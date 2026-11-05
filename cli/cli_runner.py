"""
@file  cli_runner.py
@brief 命令分发器与 REPL：两种输入协议共用同一组命令实现。
@details
协议 A（子命令，给人用）：
    cli --json project open "C:\\data\\rec.csv"
协议 B（机器调用，给 Agent/harness 用）：
    cli --json project.open '{"path":"C:\\\\data\\\\rec.csv"}'
两条路径都归一成 dispatch(action, payload)，便于单测覆盖全部映射。
REPL 内禁用任何 sys.exit / argparse 出错即退出行为，错误统一转信封。
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
from typing import Any, Callable

from .commands import (
    ACTION_NAMES,
    OPTION_SPECS,
    SUBCOMMAND_ACTIONS,
    export_cmd,
    project_cmd,
    run_cmd,
    status_cmd,
)
from .envelope import (
    ERR_INTERNAL,
    CliError,
    Envelope,
    UsageError,
)
from .parser import HELP_TEXT, parse_tokens, strip_bom, tokenize

Handler = Callable[[dict[str, Any]], tuple[dict[str, Any], str]]

# action → 命令实现（唯一权威映射，SKILL.md 与 harness 均以此为准）
HANDLERS: dict[str, Handler] = {
    "status": status_cmd.status,
    "project.open": project_cmd.project_open,
    "project.new": project_cmd.project_new,
    "project.close": project_cmd.project_close,
    "project.status": project_cmd.project_status,
    "run.frame": run_cmd.run_frame,
    "run.frames": run_cmd.run_frames,
    "run.listen": run_cmd.run_listen,
    "run.bones": run_cmd.run_bones,
    "run.port-check": run_cmd.run_port_check,
    "export": export_cmd.export,
}


def dispatch(action: str, payload: dict[str, Any]) -> Envelope:
    """@brief 执行一条命令，永远返回信封、永不抛异常、永不退出进程。

    @details 底层 SDK / CSV 解析器的 print 会被捕获并转写到 stderr，
             保证 stdout 只有一行合法信封，自动化解析不会被中文日志污染。
    @param action 机器调用协议中的 action 名。
    @param payload 命令参数字典。
    @return Envelope（成功或失败）。
    """
    captured = io.StringIO()
    try:
        handler = HANDLERS.get(action)
        if handler is None:
            raise UsageError(
                f"未知命令：{action}；可用命令：{', '.join(ACTION_NAMES)}",
                data={"actions": list(ACTION_NAMES)},
            )
        if not isinstance(payload, dict):
            raise UsageError("payload 必须是 JSON 对象（dict）")
        with contextlib.redirect_stdout(captured):
            data, message = handler(payload)
        return Envelope.success(data, message)
    except CliError as exc:
        return Envelope.failure(exc.code, str(exc), exc.data)
    except Exception as exc:  # 兜底：命令实现不得让 REPL / 主进程崩溃
        return Envelope.failure(
            ERR_INTERNAL,
            f"{type(exc).__name__}: {exc}",
            {"action": action},
        )
    finally:
        noise = captured.getvalue()
        if noise.strip():
            # 诊断信息走 stderr，绝不污染 stdout 的 JSON 信封
            sys.stderr.write(noise if noise.endswith("\n") else noise + "\n")


def _positional_key(key: tuple[str, str]) -> str | None:
    """@brief 返回该子命令唯一位置参数应写入的 payload 键名。"""
    if key in (("project", "open"), ("project", "new")):
        return "path"
    if key == ("export", ""):
        return "output"
    return None


def _handle(tokens: list[str], default_json: bool) -> tuple[Envelope, bool]:
    """@brief 解析并分发单条命令（内部实现，错误由 UsageError 上抛）。"""
    cleaned = [t for t in tokens if t != "--json"]
    as_json = default_json or ("--json" in tokens)
    if not cleaned:
        raise UsageError("缺少命令；输入 help 查看命令列表")

    first = cleaned[0]
    if first in ("help", "--help", "-h", "?"):
        return (
            Envelope.success(
                {"actions": list(ACTION_NAMES), "help": HELP_TEXT}, "命令列表"
            ),
            as_json,
        )

    # ── 协议 B：--json <action> '<payload-json>' ────────────────────────
    # 带点号的 action（project.open 等）一定是机器协议；单词 action
    # （status / export）仅在无参数或参数看起来是 JSON 对象时走机器协议，
    # 否则按子命令语法解析（例如 `export out.json --format csv`）。
    rest = cleaned[1:]
    machine_call = ("." in first) or (
        first in HANDLERS and (not rest or rest[0].lstrip().startswith("{"))
    )
    if machine_call:
        if len(rest) > 1:
            raise UsageError(
                f"机器调用协议只接受一个 payload 参数，当前多余：{rest[1:]}"
            )
        try:
            payload = json.loads(rest[0]) if rest else {}
        except (ValueError, TypeError) as exc:
            raise UsageError(f"payload 不是合法 JSON：{exc}") from None
        return dispatch(first, payload), as_json

    # 形如 project.xxx 但不在 HANDLERS 里：给出明确的未知命令信封
    if "." in first and first.split(".")[0] in ("project", "run", "export", "status"):
        return dispatch(first, {}), as_json

    # ── 协议 A：子命令式 ───────────────────────────────────────────────
    group = first
    second = ""
    rest_tokens = cleaned[1:]
    if group in ("project", "run") and rest_tokens and not rest_tokens[0].startswith("--"):
        second = rest_tokens[0]
        rest_tokens = rest_tokens[1:]

    key = (group, second)
    action = SUBCOMMAND_ACTIONS.get(key)
    if action is None:
        hint = (
            f"未知子命令：{group} {second}".strip()
            if group in ("project", "run")
            else f"未知命令：{group}"
        )
        raise UsageError(
            f"{hint}；可用命令：{', '.join(ACTION_NAMES)}",
            data={"actions": list(ACTION_NAMES)},
        )

    args = parse_tokens(rest_tokens, OPTION_SPECS.get(key, {}))
    payload = args.to_payload()
    pos_key = _positional_key(key)
    if args.positional:
        if pos_key is None:
            raise UsageError(
                f"命令 {' '.join(k for k in key if k)} 不接受位置参数：{args.positional}"
            )
        if len(args.positional) > 1:
            raise UsageError(f"位置参数过多：{args.positional}")
        if pos_key in payload:
            raise UsageError(f"目标路径重复指定（位置参数与 {pos_key} 选项）")
        payload[pos_key] = args.positional[0]

    # 子命令别名归一到机器协议使用的键名
    if "file" in payload and "input" not in payload and key == ("export", ""):
        payload["input"] = payload.pop("file")
    return dispatch(action, payload), as_json


def handle_argv(tokens: list[str], *, default_json: bool = False) -> tuple[Envelope, bool]:
    """@brief 单条命令入口：解析错误也转成信封，绝不退出进程。

    @param tokens 已 token 化的参数（可含 BOM）。
    @param default_json REPL 的 json 开关；未显式给 --json 时自动补上。
    @return (Envelope, as_json)。
    """
    as_json = default_json or ("--json" in tokens)
    try:
        return _handle([strip_bom(t) for t in tokens], default_json)
    except CliError as exc:
        return Envelope.failure(exc.code, str(exc), exc.data), as_json


def _default_reader(prompt: str) -> str:
    """@brief 交互式显示提示符；管道/重定向输入时静默逐行读取。"""
    stdin = getattr(sys, "stdin", None)
    if stdin is not None and bool(getattr(stdin, "isatty", lambda: False)()):
        return input(prompt)
    line = sys.stdin.readline() if stdin is not None else ""
    if line == "":
        raise EOFError
    return line.rstrip("\r\n")


def run_repl(
    *,
    json_mode: bool = False,
    reader: Callable[[str], str] | None = None,
    printer: Callable[[str], None] | None = None,
) -> int:
    """@brief 启动 REPL；支持 exit/quit/help/json on|off，EOF 正常收尾。

    @details REPL 级 json 开关会真正传给 handle_argv(default_json=...)，
             而不是只打印 on/off。行内 token 支持成对单/双引号与 BOM。
    @param json_mode 初始 JSON 输出开关。
    @param reader 可注入的行读取函数（测试用）。
    @param printer 可注入的输出函数（测试用）。
    @return 进程退出码（REPL 内命令失败不影响整体退出，恒为 0）。
    """
    read = reader or _default_reader
    out = printer or print
    out("MotionGlove3DViewer CLI REPL — help 查看命令，exit/quit 退出")
    while True:
        try:
            line = read("mg> ")
        except (EOFError, KeyboardInterrupt):
            out("")
            return 0
        if line is None:
            return 0
        text = strip_bom(line).strip()
        if not text:
            continue
        low = text.lower()
        if low in ("exit", "quit", "q"):
            return 0
        if low in ("json on", "json:on", "json=on"):
            json_mode = True
            out("json=on")
            continue
        if low in ("json off", "json:off", "json=off"):
            json_mode = False
            out("json=off")
            continue
        if low in ("help", "?", "--help"):
            out(HELP_TEXT)
            continue
        try:
            tokens = tokenize(text)
        except CliError as exc:
            out(Envelope.failure(exc.code, str(exc), exc.data).render(json_mode))
            continue
        env, as_json = handle_argv(tokens, default_json=json_mode)
        out(env.render(as_json))
