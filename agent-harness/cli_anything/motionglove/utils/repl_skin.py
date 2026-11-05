"""
@file  repl_skin.py
@brief 可注入 reader/printer 的薄 REPL（CLI-Anything harness 展示层）。

@details
底层 CLI 始终以 --json 调用（协议要求，保证机器可读），REPL 的
`json on/off` 开关控制输出呈现：on 打印原始信封，off 打印人类可读摘要。
CLI 自身的 REPL 另见 cli/cli_runner.run_repl()，那里的 json 开关会真正
传给命令分发器（default_json）。
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable

from . import backend

HELP = """MotionGlove CLI REPL — 命令一览
  status | project open <path> | project open --udp [--port N]
  project new <path> [--frames N] | project close | project status
  run frame [--index N] | run frames [--count N] | run listen [--seconds S]
  run bones | run port-check [--port N]
  export <output> [--format F] [--input P] [--index N] [--count N]
  json on | json off | help | exit | quit
"""


def _default_reader(prompt: str) -> str:
    """@brief 交互式显示提示符，管道输入时静默读取（EOF 抛 EOFError）。"""
    stdin = getattr(sys, "stdin", None)
    if stdin is not None and bool(getattr(stdin, "isatty", lambda: False)()):
        return input(prompt)
    line = sys.stdin.readline() if stdin is not None else ""
    if line == "":
        raise EOFError
    return line.rstrip("\r\n")


def _tokenize(text: str) -> list[str]:
    """@brief 引号感知的行内切分（支持含空格路径，Windows 反斜杠不转义）。"""
    out: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    for ch in text:
        if quote is not None:
            if ch == quote:
                quote = None
            else:
                buf.append(ch)
        elif ch in ("'", '"'):
            quote = ch
        elif ch.isspace():
            if buf:
                out.append("".join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def _split_opts(tokens: list[str]) -> tuple[dict[str, Any], list[str]]:
    """@brief 切分 --key value / --key=value / 布尔开关与位置参数。"""
    opts: dict[str, Any] = {}
    positional: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--") and len(tok) > 2:
            name, sep, inline = tok[2:].partition("=")
            key = name.replace("-", "_")
            if sep:
                opts[key] = inline
            elif i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                opts[key] = tokens[i + 1]
                i += 1
            else:
                opts[key] = True
        else:
            positional.append(tok)
        i += 1
    return opts, positional


def _compact(payload: dict[str, Any]) -> dict[str, Any]:
    """@brief 去掉 None / 空字符串值。"""
    return {k: v for k, v in payload.items() if v is not None and v != ""}


def translate(line: str) -> tuple[str, Any]:
    """@brief 把一行 REPL 输入翻译成 (kind, value)。

    @details kind ∈ command / exit / json / help / empty / unknown；
             command 的 value 为 (action, payload) 二元组。
    @param line 一行文本（允许 BOM）。
    @return (kind, value) 二元组。
    """
    text = (line or "").lstrip("\ufeff").strip()
    if not text:
        return "empty", None
    if text.lower() == "--help":
        return "help", None

    opts, pos = _split_opts(_tokenize(text))
    head = pos[0].lower() if pos else ""
    sub = pos[1].lower() if len(pos) > 1 else ""

    if head in ("exit", "quit", "q"):
        return "exit", None
    if head in ("help", "?", "--help"):
        return "help", None
    if head == "json" and sub in ("on", "off"):
        return "json", sub == "on"

    if head == "status" and not sub:
        return "command", ("status", {})

    if head == "project":
        if sub == "open":
            payload = _compact({
                "path": pos[2] if len(pos) > 2 else opts.get("file"),
                "udp": opts.get("udp"),
                "port": opts.get("port"),
                "actor": opts.get("actor"),
                "source": opts.get("source"),
            })
            return "command", ("project.open", payload)
        if sub == "new":
            payload = _compact({
                "path": pos[2] if len(pos) > 2 else opts.get("file"),
                "frames": opts.get("frames"),
                "actor": opts.get("actor"),
                "force": opts.get("force"),
            })
            return "command", ("project.new", payload)
        if sub == "close":
            return "command", ("project.close", {})
        if sub == "status":
            return "command", ("project.status", {})

    if head == "run":
        action_map = {
            "frame": "run.frame",
            "frames": "run.frames",
            "listen": "run.listen",
            "bones": "run.bones",
            "port-check": "run.port-check",
            "port_check": "run.port-check",
        }
        if sub in action_map:
            return "command", (action_map[sub], _compact(dict(opts)))

    if head == "export":
        payload = _compact({
            "output": pos[1] if len(pos) > 1 else opts.pop("output", None),
            **opts,
        })
        return "command", ("export", payload)

    return "unknown", text


class ReplSkin:
    """@brief 薄 REPL：只做行解析、调用 backend、格式化输出。"""

    def __init__(
        self,
        call: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
        reader: Callable[[str], str] | None = None,
        printer: Callable[[str], None] | None = None,
        json_mode: bool = False,
        prompt: str = "mg> ",
    ) -> None:
        """@brief 构造 REPL。

        @param call 可注入的命令调用函数（默认 backend.call）。
        @param reader 可注入的行读取函数。
        @param printer 可注入的输出函数。
        @param json_mode 初始 JSON 输出开关。
        @param prompt 交互式提示符。
        """
        self._call = call or (lambda action, payload: backend.call(action, payload))
        self._reader = reader or _default_reader
        self._printer = printer or print
        self.json_mode = bool(json_mode)
        self.prompt = prompt

    def format_envelope(self, envelope: dict[str, Any]) -> str:
        """@brief 按 json 开关格式化信封（json on 输出原始信封 JSON）。"""
        if self.json_mode:
            return json.dumps(envelope, ensure_ascii=False)
        head = "[OK] " if envelope.get("ok") else "[FAIL] "
        lines = [
            f"{head}{envelope.get('message', '')}",
            f"code: {envelope.get('code')}",
        ]
        data = envelope.get("data") or {}
        if data:
            lines.append("data:")
            lines.append(json.dumps(data, ensure_ascii=False, indent=2))
        return "\n".join(lines)

    def handle_line(self, line: str) -> str | None:
        """@brief 处理单行输入，返回待打印文本；None 表示无需输出。"""
        kind, value = translate(line)
        if kind == "empty":
            return None
        if kind == "exit":
            return "__EXIT__"
        if kind == "help":
            return HELP
        if kind == "json":
            self.json_mode = bool(value)
            return f"json={'on' if self.json_mode else 'off'}"
        if kind == "unknown":
            return f"[FAIL] 未知命令：{value}；输入 help 查看命令列表"
        action, payload = value
        try:
            envelope = self._call(action, payload)
        except backend.CliError as exc:
            return f"[FAIL] {exc}"
        return self.format_envelope(envelope)

    def run(self) -> int:
        """@brief 运行 REPL 直到 exit/quit/EOF。

        @return 进程退出码（REPL 内命令失败不影响整体退出，恒为 0）。
        """
        self._printer("MotionGlove CLI REPL — help 查看命令，exit/quit 退出")
        while True:
            try:
                line = self._reader(self.prompt)
            except (EOFError, KeyboardInterrupt):
                self._printer("")
                return 0
            output = self.handle_line(line)
            if output == "__EXIT__":
                return 0
            if output is not None:
                self._printer(output)
