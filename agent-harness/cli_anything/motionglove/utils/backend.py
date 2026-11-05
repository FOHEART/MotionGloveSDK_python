"""
@file  backend.py
@brief CLI 黑盒后端：纯函数 argv 构造 + subprocess 调用 + 信封解析。

@details
底层 CLI 是黑盒，调用方式固定为：
    subprocess.run([*cli_prefix, "--json", action, json.dumps(payload)])
其中 cli_prefix 为 [python, motionGloveSDK_cli.py]（源码树）或
[MotionGlove3DViewer.exe, "--cli"]（部署目录）。
错误分层：CliProtocolError（stdout 不是合法信封 = CLI 版本不匹配）、
CliError（起不来/超时/异常退出）、业务失败信封原样返回（默认不抛）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

ENV_CLI_BIN = "MOTIONGLOVE_CLI_BIN"
ENV_CLI_PY = "MOTIONGLOVE_CLI_PYTHON"
ENV_TIMEOUT = "MOTIONGLOVE_CLI_TIMEOUT"

CLI_SCRIPT = "motionGloveSDK_cli.py"
EXE_NAMES = (
    "MotionGloveCLI.exe",
    "MotionGloveCLI",
    "MotionGlove3DViewer.exe",
    "MotionGlove3DViewer",
)
DIST_RELATIVE = (
    "dist/MotionGlove3DViewer/MotionGlove3DViewer.exe",
    "dist/MotionGlove3DViewer/MotionGlove3DViewer",
    "dist/MotionGloveCLI.exe",
    "dist/MotionGloveCLI",
)


class CliError(Exception):
    """@brief CLI 进程层错误（起不来 / 超时 / 异常退出）。"""


class CliProtocolError(CliError):
    """@brief stdout 不是合法信封（通常是 CLI 版本不匹配或未走 --cli 分流）。"""


def app_root() -> Path:
    """@brief 定位应用根目录（源码仓库根或安装目录）。

    @details 部署后 exe 与 agent-harness/ 同级，backend.py 位于
             <root>/agent-harness/cli_anything/motionglove/utils/ 下，
             因此向上查找含 CLI 入口脚本或 exe 的目录即可同时兼容两种布局。
    @return 应用根目录 Path。
    """
    here = Path(__file__).resolve()
    markers = (CLI_SCRIPT, *EXE_NAMES)
    for parent in here.parents:
        if any((parent / name).is_file() for name in markers):
            return parent
    return here.parents[4] if len(here.parents) > 4 else here.parent


def needs_cli_flag(path: str | Path) -> bool:
    """@brief 判断该二进制是否是 GUI 主程序（必须加 --cli 才进 CLI 模式）。"""
    return Path(path).stem.lower().startswith("motionglove3dviewer")


def as_prefix(cli_bin: str | Path) -> list[str]:
    """@brief 把二进制路径转成命令前缀（GUI 主程序自动追加 --cli）。

    @param cli_bin CLI/GUI 可执行文件路径。
    @return 命令前缀列表。
    """
    path = Path(cli_bin)
    return [str(path), *(["--cli"] if needs_cli_flag(path) else [])]


def candidate_prefixes(root: Path | None = None) -> list[list[str]]:
    """@brief 按优先级列出全部候选命令前缀（纯查询，不启动进程）。

    优先级：环境变量 > 部署目录（exe 与 harness 同级）> 仓库构建产物
    > PATH > 源码树 python 入口。
    @param root 应用根目录，缺省自动定位。
    @return 命令前缀列表的列表。
    """
    root = root or app_root()
    candidates: list[list[str]] = []

    env_bin = os.environ.get(ENV_CLI_BIN)
    if env_bin:
        candidates.append(as_prefix(Path(env_bin)))

    for name in EXE_NAMES:
        path = root / name
        if path.is_file():
            candidates.append(as_prefix(path))

    for rel in DIST_RELATIVE:
        path = root / rel
        if path.is_file():
            candidates.append(as_prefix(path))

    on_path = shutil.which("MotionGloveCLI") or shutil.which("MotionGlove3DViewer")
    if on_path:
        candidates.append(as_prefix(Path(on_path)))

    entry = root / CLI_SCRIPT
    if entry.is_file():
        candidates.append([os.environ.get(ENV_CLI_PY) or sys.executable, str(entry)])
    return candidates


def build_argv(
    action: str,
    payload: dict[str, Any] | None,
    cli_prefix: Sequence[str],
) -> list[str]:
    """@brief 【纯函数】action + payload → 完整 argv（无 I/O，便于全量单测）。

    @param action 机器协议 action，例如 "project.open"。
    @param payload 命令参数字典；None 视为空对象。
    @param cli_prefix 命令前缀（[python, cli.py] 或 [exe, --cli]）。
    @return 可直接交给 subprocess.run 的 argv 列表。
    @exception ValueError action 为空或前缀为空。
    """
    if not action:
        raise ValueError("action 不能为空")
    if not cli_prefix:
        raise ValueError("cli_prefix 不能为空")
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("payload 必须是 dict 或 None")
    body = json.dumps(
        payload or {}, ensure_ascii=False, separators=(",", ":")
    )
    return [*[str(x) for x in cli_prefix], "--json", str(action), body]


def parse_envelope(stdout: str) -> dict[str, Any]:
    """@brief 从 stdout 解析统一 JSON 信封（容忍前置诊断行，取最后一条信封）。

    @param stdout CLI 的 stdout 文本。
    @return 信封字典（ok/code/message/data）。
    @exception CliProtocolError stdout 为空或不含合法信封。
    """
    text = (stdout or "").strip().lstrip("\ufeff")
    if not text:
        raise CliProtocolError(
            "CLI 没有输出任何内容：可能是 WIN32 子系统 exe 未进入 --cli 分流，"
            "或 stdout 未接管父控制台"
        )
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        return validate_envelope(obj)
    raise CliProtocolError(f"stdout 不含合法 JSON 信封：{text[:200]!r}")
    # 注：validate_envelope 会对结构不合法抛 CliProtocolError


def validate_envelope(obj: Any) -> dict[str, Any]:
    """@brief 校验信封结构（CLI 版本不匹配时给出明确错误）。

    @param obj 已反序列化的对象。
    @return 原信封字典。
    @exception CliProtocolError 结构/类型不合法。
    """
    if not isinstance(obj, dict):
        raise CliProtocolError("信封必须是 JSON 对象")
    missing = {"ok", "code", "message", "data"} - set(obj)
    if missing:
        raise CliProtocolError(f"信封缺少字段：{sorted(missing)}")
    if not isinstance(obj["ok"], bool) or not isinstance(obj["code"], int):
        raise CliProtocolError("信封字段类型错误：ok 必须为 bool，code 必须为 int")
    if not isinstance(obj["message"], str) or not isinstance(obj["data"], dict):
        raise CliProtocolError("信封字段类型错误：message 必须为 str，data 必须为 object")
    return obj


def default_timeout() -> float:
    """@brief 取默认超时（环境变量 MOTIONGLOVE_CLI_TIMEOUT，默认 30s）。"""
    try:
        return float(os.environ.get(ENV_TIMEOUT, "30"))
    except ValueError:
        return 30.0


def _probe(prefix: Sequence[str]) -> bool:
    """@brief 探测某个 exe 候选是否真的实现了 CLI 协议（避免打到旧版 GUI exe）。"""
    try:
        proc = subprocess.run(
            [*prefix, "--json", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5.0,
        )
        return bool(parse_envelope(proc.stdout)["ok"])
    except (CliError, OSError, subprocess.SubprocessError, ValueError):
        return False


def resolve_cli_prefix(
    *, probe: bool = True, root: Path | None = None
) -> list[str]:
    """@brief 定位可用的 CLI 命令前缀。

    @details exe 候选会先跑一次 --json status 探测，旧版 GUI exe（无 --cli
             分流）会被自动跳过，最终回退到源码树 python 入口；因此 CI 里
             即使存在过期构建产物也不会误用。
    @param probe 是否探测 exe 候选（单测里可关掉）。
    @param root 应用根目录。
    @return 命令前缀列表。
    @exception CliError 没有任何候选可用。
    """
    candidates = candidate_prefixes(root)
    if not candidates:
        raise CliError(
            f"未找到 CLI：请设置 {ENV_CLI_BIN} 指向可执行文件或确认 "
            f"{CLI_SCRIPT} 存在于应用根目录"
        )
    if not probe:
        return candidates[0]
    for prefix in candidates:
        # python 源码入口永远可用（与仓库代码同步），无需探测
        if len(prefix) == 2 and str(prefix[1]).endswith(".py"):
            return prefix
        if _probe(prefix):
            return prefix
    # exe 候选全部探测失败且无源码入口：返回首项，让 invoke 抛出明确的
    # CliProtocolError（stdout 不是合法信封 = 底层 CLI 版本不匹配），
    # 而不是含糊的「找不到 CLI」。
    return candidates[0]


def invoke(
    action: str,
    payload: dict[str, Any] | None = None,
    *,
    cli_prefix: Sequence[str] | None = None,
    timeout: float | None = None,
    runner: Any = None,
) -> tuple[dict[str, Any], int]:
    """@brief 调用底层 CLI，返回 (信封, 进程退出码)。

    @details 业务失败（ok=false）信封原样返回，不抛异常，便于 Agent 判定；
             只有进程层问题才抛 CliError / CliProtocolError。
    @param action 机器协议 action。
    @param payload 命令参数字典。
    @param cli_prefix 命令前缀；None 时自动定位。
    @param timeout 超时秒数；None 取默认。
    @param runner 可注入的 subprocess 运行函数（单测用），签名需兼容
                  subprocess.run(argv, capture_output, text, encoding, errors, timeout)。
    @return (信封字典, returncode)。
    @exception CliError 二进制不存在、超时或异常退出码。
    @exception CliProtocolError stdout 不是合法信封。
    """
    prefix = list(cli_prefix) if cli_prefix is not None else resolve_cli_prefix()
    argv = build_argv(action, payload, prefix)
    limit = float(timeout) if timeout is not None else default_timeout()
    run = runner or subprocess.run
    try:
        proc = run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=limit,
        )
    except FileNotFoundError as exc:
        raise CliError(f"CLI 可执行文件不存在：{argv[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise CliError(f"CLI 调用超时（{limit}s）：{action}") from exc
    except OSError as exc:
        raise CliError(f"无法启动 CLI：{exc}") from exc

    returncode = int(getattr(proc, "returncode", 0) or 0)
    envelope = parse_envelope(getattr(proc, "stdout", "") or "")
    if returncode not in (0, 1):
        raise CliError(
            f"CLI 异常退出（returncode={returncode}）："
            f"{(getattr(proc, 'stderr', '') or '')[-200:]}"
        )
    return envelope, returncode


def call(
    action: str,
    payload: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """@brief invoke() 的便捷包装，只返回信封。"""
    return invoke(action, payload, **kwargs)[0]
