"""
@file  console_win.py
@brief Windows 控制台接管与 UTF-8 编码（内置 --cli 分流必踩的坑）。
@details
PyInstaller 默认以 WIN32（无控制台）子系统打包主程序，从控制台启动时
stdout 不可见、sys.stdout 甚至可能为 None。CLI 模式开头执行：
  1. 若标准句柄已被重定向（>file / 管道）→ 直接沿用，不动；
  2. 否则 AttachConsole(ATTACH_PARENT_PROCESS) +
     open("CONOUT$") / open("CONIN$") 接管父控制台（Python 层等价于
     C++ 的 freopen(CONOUT$) / freopen(CONIN$)）；
  3. 控制台代码页切 CP_UTF8，输出流显式 reconfigure 为 UTF-8。
非 Windows 平台或普通 python 解释器（已有控制台）时本模块为空操作。
"""

from __future__ import annotations

import sys

CP_UTF8 = 65001
FILE_TYPE_CHAR = 0x0002
FILE_TYPE_DISK = 0x0001
FILE_TYPE_PIPE = 0x0003
ATTACH_PARENT_PROCESS = -1


def force_utf8_stdio() -> None:
    """@brief 把 stdout/stderr 统一 reconfigure 为 UTF-8（幂等）。

    @details 内部数据全 UTF-8；中文消息与 JSON 都必须以 UTF-8 输出，
             否则 GBK 控制台会抛 UnicodeEncodeError。
    """
    for stream_name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _is_redirected(stream: object) -> bool:
    """@brief 判断标准流是否已重定向到文件/管道（此时不应接管控制台）。"""
    if stream is None:
        return False
    if sys.platform != "win32":
        return not bool(getattr(stream, "isatty", lambda: False)())
    try:
        import msvcrt
        import ctypes

        fd = stream.fileno()  # type: ignore[attr-defined]
        handle = msvcrt.get_osfhandle(fd)
        file_type = ctypes.windll.kernel32.GetFileType(handle)  # type: ignore[attr-defined]
        return file_type in (FILE_TYPE_DISK, FILE_TYPE_PIPE)
    except Exception:
        return False


def _rebuild_redirected_streams() -> bool:
    """@brief WIN32 子系统 exe 的 sys.std* 可能为 None，但 OS 标准句柄已被
            subprocess 管道/文件重定向；此时依据句柄重建 Python 流。

    @details 这是文档第 5 节「若标准句柄已被重定向 → 直接用，不动」在
             Python 层的等价实现：windowed exe 里不能靠 sys.stdout.isatty()
             判断重定向（流对象根本不存在），必须查 GetStdHandle + GetFileType。
    @return True 表示至少重建了一个流（调用方不应再 AttachConsole）。
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        import msvcrt
        import os

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.GetStdHandle.restype = ctypes.c_void_p
        kernel32.GetStdHandle.argtypes = [ctypes.c_uint32]
        kernel32.GetFileType.argtypes = [ctypes.c_void_p]

        rebuilt = False
        # STD_INPUT_HANDLE=-10, STD_OUTPUT_HANDLE=-11, STD_ERROR_HANDLE=-12
        for name, std_id, mode in (
            ("stdout", -11, "w"),
            ("stderr", -12, "w"),
            ("stdin", -10, "r"),
        ):
            if getattr(sys, name, None) is not None:
                continue
            handle = kernel32.GetStdHandle(std_id & 0xFFFFFFFF)
            if not handle or handle == -1:
                continue
            if kernel32.GetFileType(handle) not in (FILE_TYPE_DISK, FILE_TYPE_PIPE):
                continue
            fd = msvcrt.open_osfhandle(handle, 0)
            setattr(
                sys,
                name,
                os.fdopen(fd, mode, encoding="utf-8", errors="replace"),
            )
            rebuilt = True
        return rebuilt
    except Exception:
        return False


def _set_console_codepage() -> None:
    """@brief 控制台输入/输出代码页切到 UTF-8。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleOutputCP(CP_UTF8)
        kernel32.SetConsoleCP(CP_UTF8)
    except Exception:
        pass


def ensure_console() -> bool:
    """@brief 确保 CLI 输出能到达父控制台（可安全重复调用）。

    @return True 表示已接管/刷新了控制台；False 表示无需或无法接管。
    """
    if sys.platform != "win32":
        return False

    _set_console_codepage()

    # 情况 0：windowed exe 的 sys.std* 为 None，但 OS 句柄已被管道/文件重定向
    if _rebuild_redirected_streams():
        force_utf8_stdio()
        return True

    stdout = getattr(sys, "stdout", None)

    # 情况 1：已被重定向（>file / 管道），保持调用方的句柄不变
    if _is_redirected(stdout):
        force_utf8_stdio()
        return False

    # 情况 2：已有可交互控制台（python.exe / console=True 的 exe）
    if stdout is not None and bool(getattr(stdout, "isatty", lambda: False)()):
        force_utf8_stdio()
        return True

    # 情况 3：windowed exe，需要 AttachConsole 接管父进程控制台
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        if not kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            return False
        out = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        err = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        try:
            inp = open("CONIN$", "r", encoding="utf-8", errors="replace")
        except OSError:
            inp = None
    except (OSError, AttributeError):
        return False

    sys.stdout, sys.stderr = out, err
    if inp is not None:
        sys.stdin = inp
    _set_console_codepage()
    force_utf8_stdio()
    return True
