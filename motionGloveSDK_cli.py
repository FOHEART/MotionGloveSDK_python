#!/usr/bin/env python3
"""
@file  motionGloveSDK_cli.py
@brief CLI-Anything 独立命令行入口（无 VTK / PySide6 / bpy 依赖）。
@details
两种等价调用方式：
    python motionGloveSDK_cli.py --json status
    python motionGloveSDK_example3_3dView.py --cli --json status   # 主程序内置分流
    python -m cli --json status
打包成 WIN32 子系统 exe 时，请用主程序的内置 --cli 分流（cli/console_win.py
会 AttachConsole 接管父控制台），或让 harness 直接调用本脚本。
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cli import main  # noqa: E402  (路径注入后才能安全导入)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
