"""
errors.py - MotionGloveSDK Python 转接层
转接层专用的异常类型，与 C++ 侧的返回码（0 成功 / 负值失败）解耦。
"""

from __future__ import annotations


class MotionGloveNativeError(RuntimeError):
    """原生库不可用、ABI 不匹配或调用失败。"""


class NativeLibraryNotFound(MotionGloveNativeError):
    """在候选路径中找不到 MotionGloveSDK 原生库。"""

    def __init__(self, searched: list[str]) -> None:
        self.searched = searched
        lines = [
            "未找到 MotionGloveSDK 原生库（MotionGloveSDK.dll / libMotionGloveSDK.so）。",
            "本 SDK 的数据流解析完全由 C++ 库完成，必须先编译它：",
            "  Windows : scripts\\[Windows]build_mgsdk_cpp.cmd",
            "  Linux   : bash \"scripts/[Linux]build_mgsdk_cpp.sh\"",
            "也可以用环境变量 MOTIONGLOVE_NATIVE_LIB 指定库文件（或所在目录）的绝对路径。",
            "已搜索的位置：",
        ]
        lines.extend(f"  - {path}" for path in searched)
        super().__init__("\n".join(lines))
