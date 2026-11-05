"""
@file  _cli.py
@brief Click 入口：把人类友好的子命令映射到 CLI 机器协议的 action+payload。

@details
    cli-anything-motionglove --cli-bin <path> --timeout 30 status
    cli-anything-motionglove project open "C:\\rec.csv"
    cli-anything-motionglove run frame --index 0
    cli-anything-motionglove export out.json
    cli-anything-motionglove repl
所有子命令最终都经 backend.call(action, payload) 调用底层 CLI 黑盒。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click


def _force_utf8_stdio() -> None:
    """@brief 输出流统一 UTF-8（--help 回调早于 Click group 回调，需在导入时执行）。"""
    for name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


_force_utf8_stdio()

try:  # 作为包导入（pip install -e 后）
    from .utils import backend, repl_skin
except ImportError:  # 直接 `python _cli.py`
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from utils import backend, repl_skin  # type: ignore[no-redef]


def _compact(values: dict[str, Any]) -> dict[str, Any]:
    """@brief 去掉 None / False / 空字符串，保持 payload 干净。"""
    return {
        k: v for k, v in values.items()
        if v is not None and v is not False and v != ""
    }


def _human(envelope: dict[str, Any], label: str) -> str:
    """@brief 信封 → 人类可读摘要。"""
    state = "OK" if envelope.get("ok") else "FAIL"
    lines = [
        f"{state} {label}: {envelope.get('message', '')} "
        f"(code={envelope.get('code')})"
    ]
    for key, value in (envelope.get("data") or {}).items():
        text = (
            json.dumps(value, ensure_ascii=False)
            if isinstance(value, (dict, list)) else str(value)
        )
        lines.append(f"  {key}: {text}")
    return "\n".join(lines)


def _emit(ctx: click.Context, action: str, payload: dict[str, Any]) -> None:
    """@brief 调用后端、打印结果、失败时以退出码 1 结束。"""
    try:
        envelope = backend.call(
            action,
            payload,
            cli_prefix=ctx.obj["prefix"],
            timeout=ctx.obj["timeout"],
        )
    except backend.CliError as exc:
        click.echo(f"[FAIL] {exc}", err=True)
        ctx.exit(1)
    if ctx.obj["raw"]:
        click.echo(json.dumps(envelope, ensure_ascii=False))
    else:
        click.echo(_human(envelope, action))
    if not envelope.get("ok"):
        ctx.exit(1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--cli-bin", envvar=backend.ENV_CLI_BIN, default=None,
    help="底层 CLI 二进制/入口路径（默认自动定位）",
)
@click.option("--timeout", default=30.0, show_default=True, help="单次调用超时秒数")
@click.option("--raw", is_flag=True, help="所有命令直接输出原始 JSON 信封")
@click.pass_context
def main(ctx: click.Context, cli_bin: str | None, timeout: float, raw: bool) -> None:
    """MotionGlove3DViewer CLI-Anything harness。"""
    ctx.ensure_object(dict)
    try:
        prefix = (
            backend.as_prefix(Path(cli_bin))
            if cli_bin else backend.resolve_cli_prefix()
        )
    except backend.CliError as exc:
        click.echo(f"[FAIL] {exc}", err=True)
        ctx.exit(1)
    ctx.obj["prefix"] = prefix
    ctx.obj["timeout"] = float(timeout)
    ctx.obj["raw"] = bool(raw)


@main.command("status")
@click.pass_context
def _status(ctx: click.Context) -> None:
    """查询后端/原生库/会话状态。"""
    _emit(ctx, "status", {})


@main.group("project")
def _project() -> None:
    """工程（数据源）管理：open / new / close / status。"""


@_project.command("open")
@click.argument("path", required=False)
@click.option("--file", "file_", default=None, help="CSV 路径（等价于位置参数）")
@click.option("--udp", is_flag=True, help="切换到 UDP 数据源")
@click.option("--port", type=int, default=None, help="UDP 端口")
@click.option("--actor", default=None, help="数据流名称")
@click.pass_context
def _project_open(
    ctx: click.Context, path: str | None, file_: str | None,
    udp: bool, port: int | None, actor: str | None,
) -> None:
    """打开 CSV 工程或切换 UDP 数据源。"""
    _emit(ctx, "project.open", _compact({
        "path": path or file_, "udp": udp or None,
        "port": port, "actor": actor,
    }))


@_project.command("new")
@click.argument("path")
@click.option("--frames", type=int, default=None, help="生成示例 T-pose 帧数")
@click.option("--actor", default=None, help="数据流名称")
@click.option("--force", is_flag=True, help="覆盖已有文件")
@click.pass_context
def _project_new(
    ctx: click.Context, path: str, frames: int | None,
    actor: str | None, force: bool,
) -> None:
    """新建 CSV 工程。"""
    _emit(ctx, "project.new", _compact({
        "path": path, "frames": frames, "actor": actor, "force": force or None,
    }))


@_project.command("close")
@click.pass_context
def _project_close(ctx: click.Context) -> None:
    """关闭当前工程。"""
    _emit(ctx, "project.close", {})


@_project.command("status")
@click.pass_context
def _project_status(ctx: click.Context) -> None:
    """查看当前会话。"""
    _emit(ctx, "project.status", {})


@main.group("run")
def _run() -> None:
    """取帧 / 采集 / 诊断：frame / frames / listen / bones / port-check。"""


@_run.command("frame")
@click.option("--file", "file_", default=None, help="显式指定源 CSV（不依赖会话）")
@click.option("--source", default=None, help="csv 或 udp")
@click.option("--actor", default=None)
@click.option("--index", type=int, default=None, help="CSV 帧索引（0-based）")
@click.option("--port", type=int, default=None)
@click.option("--timeout", "wait", type=float, default=None, help="UDP 等待秒数")
@click.option("--summary", is_flag=True, help="只输出帧摘要")
@click.pass_context
def _run_frame(
    ctx: click.Context, file_: str | None, source: str | None,
    actor: str | None, index: int | None, port: int | None,
    wait: float | None, summary: bool,
) -> None:
    """取一帧。"""
    _emit(ctx, "run.frame", _compact({
        "file": file_, "source": source, "actor": actor, "index": index,
        "port": port, "timeout": wait, "summary": summary or None,
    }))


@_run.command("frames")
@click.option("--file", "file_", default=None)
@click.option("--source", default=None)
@click.option("--actor", default=None)
@click.option("--start", type=int, default=None)
@click.option("--count", type=int, default=None)
@click.option("--port", type=int, default=None)
@click.option("--timeout", "wait", type=float, default=None)
@click.option("--full", is_flag=True, help="输出完整骨骼数组")
@click.pass_context
def _run_frames(
    ctx: click.Context, file_: str | None, source: str | None,
    actor: str | None, start: int | None, count: int | None,
    port: int | None, wait: float | None, full: bool,
) -> None:
    """连续取多帧。"""
    _emit(ctx, "run.frames", _compact({
        "file": file_, "source": source, "actor": actor, "start": start,
        "count": count, "port": port, "timeout": wait, "full": full or None,
    }))


@_run.command("listen")
@click.option("--port", type=int, default=None)
@click.option("--actor", default=None)
@click.option("--seconds", type=float, default=None, help="采集秒数")
@click.pass_context
def _run_listen(
    ctx: click.Context, port: int | None, actor: str | None, seconds: float | None
) -> None:
    """UDP 采集若干秒。"""
    _emit(ctx, "run.listen", _compact({
        "port": port, "actor": actor, "seconds": seconds,
    }))


@_run.command("bones")
@click.pass_context
def _run_bones(ctx: click.Context) -> None:
    """查询 42/32 骨骼索引映射。"""
    _emit(ctx, "run.bones", {})


@_run.command("port-check")
@click.option("--port", type=int, default=None)
@click.pass_context
def _run_port_check(ctx: click.Context, port: int | None) -> None:
    """诊断 UDP 端口占用。"""
    _emit(ctx, "run.port-check", _compact({"port": port}))


@main.command("export")
@click.argument("output")
@click.option("--format", "fmt", default=None, help="json / csv / bvh（省略按扩展名）")
@click.option("--input", "input_", default=None, help="显式源 CSV")
@click.option("--source", default=None)
@click.option("--actor", default=None)
@click.option("--index", type=int, default=None)
@click.option("--count", type=int, default=None)
@click.option("--frame-rate", type=float, default=None, help="BVH 帧率 Hz")
@click.option("--all", "all_", is_flag=True, help="导出全部帧")
@click.pass_context
def _export(
    ctx: click.Context, output: str, fmt: str | None, input_: str | None,
    source: str | None, actor: str | None, index: int | None,
    count: int | None, frame_rate: float | None, all_: bool,
) -> None:
    """导出 json / csv / bvh。"""
    _emit(ctx, "export", _compact({
        "output": output, "format": fmt, "input": input_, "source": source,
        "actor": actor, "index": index, "count": count,
        "frame_rate": frame_rate, "all": all_ or None,
    }))


@main.command("repl")
@click.pass_context
def _repl(ctx: click.Context) -> None:
    """进入交互式 REPL。"""
    def _call(action: str, payload: dict[str, Any]) -> dict[str, Any]:
        return backend.call(
            action, payload,
            cli_prefix=ctx.obj["prefix"], timeout=ctx.obj["timeout"],
        )

    def _reader(prompt: str) -> str:
        return input(prompt)

    skin = repl_skin.ReplSkin(call=_call, reader=_reader, json_mode=ctx.obj["raw"])
    ctx.exit(skin.run())


if __name__ == "__main__":
    main()
