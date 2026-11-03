"""
@file  errors.py
@brief MotionGloveSDK Python 转接层专用异常类型。
@details 与 C++ 侧的返回码（0 成功 / 负值失败）解耦：转接层内部把失败
         翻译为异常抛给上层，上层只需捕获 MotionGloveNativeError。
"""

from __future__ import annotations


class MotionGloveNativeError(RuntimeError):
    """@brief 原生库不可用、ABI 不匹配或调用失败的基类异常。"""


class NativeLibraryNotFound(MotionGloveNativeError):
    """@brief 在候选路径中找不到 MotionGloveSDK 原生库。

    @details 异常消息包含全部已搜索位置与编译指引。
    """

    def __init__(self, searched: list[str]) -> None:
        """@brief 用已搜索路径列表构造异常（消息附带编译指引）。

        @param searched 已尝试的全部候选路径。
        @return 无（None）。
        """
        self.searched = searched
        lines = [
            "未找到 MotionGloveSDK 原生库（MotionGloveSDK.dll / libMotionGloveSDK.so）。",
            "本 SDK 的数据流解析完全由 C++ 库完成，必须先编译它：",
            "  Windows : scripts\\build_mgsdk_cpp.cmd",
            "  Linux   : sh scripts/build_mgsdk_cpp.cmd",
            "也可以用环境变量 MOTIONGLOVE_NATIVE_LIB 指定库文件（或所在目录）的绝对路径。",
            "已搜索的位置：",
        ]
        lines.extend(f"  - {path}" for path in searched)
        super().__init__("\n".join(lines))
