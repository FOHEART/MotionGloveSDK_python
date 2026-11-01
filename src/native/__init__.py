"""
native - MotionGloveSDK Python 转接层（Python 转接层 / adapter layer）

目的：让上层代码稳定地使用 MotionGloveSDK_cpp 编译出来的库，而 C++ 工程
经常改动时只需要改动本包，不需要动 src/motionGloveSDK.py、示例程序或 3D 视图。

数据流：
    UDP 5001 ──► MotionGloveSDK.dll/.so（C++：分包重组 + CSV 解析 + 帧缓存）
                        │
                        ▼  ctypes 调用（本包）
                 GloveFrame（src/definitions.py）

分层：
    errors.py    转接层异常（库缺失 / ABI 不匹配 / 调用失败）
    abi.py       ctypes 结构体与枚举 —— 唯一与 C++ 内存布局耦合的文件
    loader.py    库定位、加载与导出函数原型绑定
    mapper.py    原生结构体 → GloveFrame 的转换
    backend.py   稳定的 Python 语义接口（NativeBackend）

C++ 侧发生以下变化时的维护动作：
    结构体字段/顺序/对齐 → 改 abi.py，并用 scripts/verify_native_abi.py 校验
    导出函数签名/返回码    → 改 loader.py 的 _bind_*（以及必要时的 backend.py）
    新增骨骼格式           → 改 abi.py（FRAME_STRUCT_BY_FORMAT）+ mapper.py

环境变量：
    MOTIONGLOVE_NATIVE_LIB  指定原生库文件或所在目录的绝对路径
"""

from __future__ import annotations

from . import abi
from .backend import NativeBackend, create_backend
from .errors import MotionGloveNativeError, NativeLibraryNotFound
from .loader import candidate_paths

__all__ = [
    "MotionGloveNativeError",
    "NativeBackend",
    "NativeLibraryNotFound",
    "SkeletonFormat",
    "abi",
    "backend_name",
    "candidate_paths",
    "get_backend",
    "is_available",
    "library_path",
    "reset_backend",
]

SkeletonFormat = abi.SkeletonFormat

_backend: NativeBackend | None = None


def get_backend() -> NativeBackend:
    """返回进程级原生后端单例；原生库不可用时抛 MotionGloveNativeError。"""
    global _backend
    if _backend is None:
        _backend = create_backend()
    return _backend


def is_available() -> bool:
    """原生库是否可用（不可用时不会抛异常，仅返回 False）。"""
    try:
        get_backend()
    except MotionGloveNativeError:
        return False
    return True


def backend_name() -> str:
    return "native"


def library_path() -> str | None:
    """已加载原生库的绝对路径（首次调用会触发加载）；不可用时抛 MotionGloveNativeError。"""
    return get_backend().library_path


def reset_backend() -> None:
    """丢弃单例（主要用于测试）。"""
    global _backend
    _backend = None
