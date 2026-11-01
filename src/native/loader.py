"""
loader.py - MotionGloveSDK Python 转接层
定位并加载 C++ 编译产物（MotionGloveSDK.dll / libMotionGloveSDK.so），
并把 C 导出函数绑定成带明确原型的 ctypes 函数。

导出函数原型来自 MotionGloveSDK/include/motionGloveSDK.h。
函数签名若发生变化，只需修改本文件的 _bind_* 部分与 abi.py。
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import sys
from pathlib import Path

from . import abi
from .errors import MotionGloveNativeError, NativeLibraryNotFound

_REPO_ROOT = Path(__file__).resolve().parents[2]

_LIBRARY_FILE_NAMES = {
    "win32": "MotionGloveSDK.dll",
    "linux": "libMotionGloveSDK.so",
    "darwin": "libMotionGloveSDK.dylib",
}

_ENV_LIB_PATH = "MOTIONGLOVE_NATIVE_LIB"

# 构建产物可能落地的配置目录名（CMake 多配置生成器 / 单配置生成器）
_BUILD_CONFIGS = ("Release", "Debug", "RelWithDebInfo", "")


def library_file_name() -> str:
    return _LIBRARY_FILE_NAMES.get(sys.platform, "libMotionGloveSDK.so")


def candidate_paths() -> list[Path]:
    """
    按优先级返回候选库文件路径（不含环境变量指定的路径）。

    优先级：
      1. 打包后（PyInstaller）的应用目录 / `sys._MEIPASS`
      2. <repo>/native/                                开发自放置目录
      3. <repo>/libs/                                  与 Python 依赖同级的约定目录
      4. <repo>/build/mgsdk_cpp/install/{bin,lib}      scripts/build_mgsdk_cpp 的安装结果
      5. <repo>/build/mgsdk_cpp/**                     CMake 构建树
      6. <repo>/third_party/MotionGloveSDK_cpp/out/**  C++ 工程自带构建脚本的输出
    """
    name = library_file_name()
    paths: list[Path] = []

    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            paths.append(Path(meipass) / name)
        paths.append(Path(sys.executable).parent / name)

    for directory in (_REPO_ROOT / "native", _REPO_ROOT / "libs"):
        paths.append(directory / name)

    install_root = _REPO_ROOT / "build" / "mgsdk_cpp" / "install"
    paths.append(install_root / "bin" / name)
    paths.append(install_root / "lib" / name)

    build_root = _REPO_ROOT / "build" / "mgsdk_cpp"
    for config in _BUILD_CONFIGS:
        paths.append(build_root / config / name if config else build_root / name)
        paths.append(build_root / "MotionGloveSDK" / config / name if config else build_root / name)

    cpp_out = _REPO_ROOT / "third_party" / "MotionGloveSDK_cpp" / "out"
    for config in ("x64-Release", "x64-Debug"):
        paths.append(cpp_out / "install" / config / "bin" / name)
        paths.append(cpp_out / "install" / config / "lib" / name)
        for sub in ("Release", "Debug"):
            paths.append(cpp_out / "build" / config / sub / name)

    return paths


def find_library() -> str:
    """
    返回可用的库路径。
    环境变量 MOTIONGLOVE_NATIVE_LIB 一旦设置即为权威路径（不存在时直接报错），
    否则按 candidate_paths() 依次查找，最后回退到系统库搜索。
    """
    name = library_file_name()

    env_value = os.getenv(_ENV_LIB_PATH, "").strip()
    if env_value:
        env_path = Path(env_value)
        candidate = env_path / name if env_path.is_dir() else env_path
        if candidate.is_file():
            return str(candidate)
        raise NativeLibraryNotFound([f"{candidate}（由环境变量 {_ENV_LIB_PATH} 指定，文件不存在）"])

    searched = candidate_paths()
    for path in searched:
        if path.is_file():
            return str(path)

    system_name = ctypes.util.find_library("MotionGloveSDK")
    if system_name:
        return system_name

    raise NativeLibraryNotFound([str(path) for path in searched])


class NativeLibrary:
    """已加载的原生库；属性即已绑定原型的导出函数。"""

    def __init__(self, handle: ctypes.CDLL, path: str) -> None:
        self._handle = handle
        self.path = path
        self._bind()

    # -- 绑定 ---------------------------------------------------------------

    @staticmethod
    def _required(handle: ctypes.CDLL, name: str):
        try:
            return getattr(handle, name)
        except AttributeError as exc:
            raise MotionGloveNativeError(
                f"原生库缺少导出函数 {name}，ABI 可能与 src/native/abi.py 不匹配："
                f"请重新编译 MotionGloveSDK_cpp 并更新转接层。"
            ) from exc

    @staticmethod
    def _optional(handle: ctypes.CDLL, name: str):
        return getattr(handle, name, None)

    def _bind(self) -> None:
        handle = self._handle

        self.get_version = self._required(handle, "MotionGloveSDK_getVersion")
        self.get_version.restype = ctypes.c_uint
        self.get_version.argtypes = []

        self.listen_udp_port = self._required(handle, "MotionGloveSDK_ListenUDPPort")
        self.listen_udp_port.restype = ctypes.c_int
        self.listen_udp_port.argtypes = [ctypes.c_int]

        self.close_udp_port = self._required(handle, "MotionGloveSDK_CloseUDPPort")
        self.close_udp_port.restype = ctypes.c_int
        self.close_udp_port.argtypes = []

        self.is_new_frame_pending = self._required(handle, "MotionGloveSDK_isGloveNewFramePending")
        self.is_new_frame_pending.restype = ctypes.c_bool
        self.is_new_frame_pending.argtypes = [ctypes.c_char_p]

        self.reset_new_frame_pending = self._required(handle, "MotionGloveSDK_resetGloveNewFramePending")
        self.reset_new_frame_pending.restype = ctypes.c_bool
        self.reset_new_frame_pending.argtypes = [ctypes.c_char_p]

        # 以下三个接口按骨骼格式分派；GetSkeletonsFrameType 在旧版库中可能不存在，
        # 此时 backend 会退化为"先试 42 段再试 32 段"。
        frame_format = self._optional(handle, "MotionGloveSDK_GetSkeletonsFrameType")
        if frame_format is not None:
            frame_format.restype = ctypes.c_int
            frame_format.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint8)]
        self.get_frame_type = frame_format

        get_42 = self._required(handle, "MotionGloveSDK_GetSkeletons42Frame")
        get_42.restype = ctypes.c_int
        get_42.argtypes = [ctypes.c_char_p, ctypes.POINTER(abi.KHHS42PosAttitude)]
        self.get_42_frame = get_42

        get_32 = self._required(handle, "MotionGloveSDK_GetSkeletons32Frame")
        get_32.restype = ctypes.c_int
        get_32.argtypes = [ctypes.c_char_p, ctypes.POINTER(abi.KHHS32PosAttitude)]
        self.get_32_frame = get_32


def load_library(path: str | None = None) -> NativeLibrary:
    """加载原生库。path 为 None 时按 candidate_paths() 自动定位。"""
    resolved = path or find_library()
    try:
        handle = ctypes.CDLL(resolved)
    except OSError as exc:
        raise MotionGloveNativeError(f"无法加载原生库 {resolved}: {exc}") from exc

    problems = abi.verify_layout()
    if problems:
        raise MotionGloveNativeError(
            "src/native/abi.py 的 ctypes 布局自检失败：\n  " + "\n  ".join(problems)
        )

    return NativeLibrary(handle, resolved)
