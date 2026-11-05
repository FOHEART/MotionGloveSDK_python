"""
@file  __init__.py
@brief CLI-Anything 内置 CLI 包入口。
@details
主程序（motionGloveSDK_example3_3dView.py）在导入任何 VTK/PySide6 之前，
检测到 --cli/--repl 就分流到本模块的 main()；独立入口
motionGloveSDK_cli.py 与 `python -m cli` 也复用同一实现，不重复业务逻辑。
CLI 路径只依赖标准库 + src/，绝不创建任何 GUI 框架对象。
"""

from __future__ import annotations

import sys
from typing import Sequence

from .cli_runner import dispatch, handle_argv, run_repl
from .console_win import ensure_console, force_utf8_stdio
from .parser import HELP_TEXT, strip_bom

__all__ = ["main", "dispatch", "handle_argv", "run_repl", "HELP_TEXT"]


def main(argv: Sequence[str] | None = None) -> int:
    """@brief CLI 主入口（返回进程退出码 0/1，不自行调用 sys.exit）。

    @details 启动顺序：UTF-8 标准流 → Windows 控制台接管 → 参数分流。
             --cli 前缀容错剥离；无参数/--repl 进入 REPL。
    @param argv 参数列表（不含程序名）；None 表示取 sys.argv[1:]。
    @return 0 成功（含 REPL 正常结束），1 命令失败。
    """
    force_utf8_stdio()
    ensure_console()

    raw = list(sys.argv[1:]) if argv is None else list(argv)
    args = [strip_bom(str(a)) for a in raw]
    if args and args[0] == "--cli":  # 容错：直接复用内置入口时也允许带前缀
        args = args[1:]

    repl_requested = bool(args) and args[0] in ("--repl", "repl")
    if repl_requested:
        args = args[1:]
    json_flags_only = bool(args) and all(a == "--json" for a in args)

    if args and args[0] in ("--help", "-h") and "--json" not in args:
        print(HELP_TEXT)
        return 0
    if args and args[0] in ("help", "?") and "--json" not in args:
        print(HELP_TEXT)
        return 0
    if not args and not repl_requested:
        return run_repl()
    if repl_requested or json_flags_only:
        return run_repl(json_mode=json_flags_only)

    envelope, as_json = handle_argv(args)
    print(envelope.render(as_json))
    return envelope.exit_code
