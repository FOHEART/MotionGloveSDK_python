"""
backend.py - MotionGloveSDK Python 转接层
对上层提供【稳定】的 Python 语义接口，屏蔽 C++ 导出函数与结构体的细节。

上层（src/motionGloveSDK.py、示例程序、3D 视图）只依赖本文件的方法名与
src/definitions.py 中的数据容器；MotionGloveSDK_cpp 改动时，
通常只需要更新 abi.py（内存布局）与本文件（调用顺序/语义差异）。
"""

from __future__ import annotations

import ctypes
import threading

from ..definitions import GloveFrame
from . import abi, mapper
from .loader import NativeLibrary, load_library

# C++ 侧 ACTOR_NAME_LEN_MAX 含结尾 NUL，故有效名称最多 63 字节
_MAX_ACTOR_NAME_BYTES = abi.ACTOR_NAME_LEN_MAX - 1


class NativeBackend:
    """基于 C++ MotionGloveSDK 的数据流后端。"""

    name = "native"

    def __init__(self, library: NativeLibrary, *, verbose: bool = True) -> None:
        self._lib = library
        self._verbose = verbose
        self._actors: dict[str, None] = {}
        self._actors_lock = threading.Lock()
        self._last_remote_addr: tuple[str, int] | None = None
        self._layout_warned = False

    def _remember_actor(self, actor_name: str) -> None:
        """记录数据流名称（轮询线程写、GUI 线程读，需要加锁）。"""
        with self._actors_lock:
            self._actors.setdefault(actor_name, None)

    # -- 元信息 -------------------------------------------------------------

    @property
    def library_path(self) -> str:
        return self._lib.path

    def version(self) -> int:
        """对应 C++ MotionGloveSDK_getVersion()。"""
        return int(self._lib.get_version())

    # -- 生命周期 -----------------------------------------------------------

    def listen(self, port: int) -> int:
        """对应 C++ MotionGloveSDK_ListenUDPPort()：0 成功 / -1 失败。"""
        return int(self._lib.listen_udp_port(int(port)))

    def close(self) -> int:
        """对应 C++ MotionGloveSDK_CloseUDPPort()：0 成功 / -1 失败。"""
        return int(self._lib.close_udp_port())

    # -- 轮询 ---------------------------------------------------------------

    def is_pending(self, actor_name: str) -> bool:
        """对应 C++ MotionGloveSDK_isGloveNewFramePending()。"""
        key = self._encode_name(actor_name)
        if key is None:
            return False
        pending = bool(self._lib.is_new_frame_pending(key))
        if pending:
            self._remember_actor(actor_name)
        return pending

    def reset_pending(self, actor_name: str) -> bool:
        """对应 C++ MotionGloveSDK_resetGloveNewFramePending()。"""
        key = self._encode_name(actor_name)
        if key is None:
            return False
        reset = bool(self._lib.reset_new_frame_pending(key))
        if reset:
            self._remember_actor(actor_name)
        return reset

    def get_frame(self, actor_name: str) -> GloveFrame | None:
        """
        按帧头记录的骨骼格式取回缓存帧并转换成 GloveFrame。
        对应 C++ MotionGloveSDK_GetSkeletonsFrameType() +
        GetSkeletons42Frame() / GetSkeletons32Frame()。
        """
        key = self._encode_name(actor_name)
        if key is None:
            return None

        fmt = self._frame_format(key)
        if fmt is None:
            return None

        frame = self._fetch(actor_name, key, fmt)
        if frame is None:
            return None

        self._remember_actor(actor_name)
        if frame.header.avatar_name:
            self._remember_actor(frame.header.avatar_name)
        self._last_remote_addr = (frame.remote_ip, frame.remote_port)
        return frame

    def get_frame_format(self, actor_name: str) -> int | None:
        """
        (SkeletonFormat.SKELETON_32 / SKELETON_42 / OPENXR)。
        未知数据流或该版本库不支持时返回 None。
        """
        key = self._encode_name(actor_name)
        if key is None or self._lib.get_frame_type is None:
            return None
        fmt = self._frame_format(key)
        return None if fmt is None or fmt < 0 else fmt

    # -- Python SDK 额外能力（C++ 侧没有对应接口） --------------------------

    def get_actor_names(self) -> list[str]:
        """
        C++ SDK 没有枚举数据流的接口，因此这里返回"已经确认存在"的数据流名称：
        取帧成功的数据流，以及查询到有新帧的数据流（按首次发现顺序）。
        """
        with self._actors_lock:
            return list(self._actors.keys())

    def get_last_remote_addr(self) -> tuple[str, int] | None:
        """
        最近一次成功取回的帧的发送方地址。
        （C++ 侧把发送方地址写在帧结构内部，因此只有取到帧之后才可用。）
        """
        return self._last_remote_addr

    # -- 内部 ---------------------------------------------------------------

    @staticmethod
    def _encode_name(actor_name: str) -> bytes | None:
        if not actor_name:
            return None
        key = actor_name.encode("utf-8", errors="replace")
        if len(key) > _MAX_ACTOR_NAME_BYTES:
            return None
        return key

    def _frame_format(self, key: bytes) -> int | None:
        if self._lib.get_frame_type is None:
            # 旧版原生库没有 Format 接口：交给 _fetch 依次试探
            return -1
        fmt = ctypes.c_uint8(0xFF)
        if self._lib.get_frame_type(key, ctypes.byref(fmt)) != 0:
            return None
        return int(fmt.value)

    def _fetch(self, actor_name: str, key: bytes, fmt: int) -> GloveFrame | None:
        if fmt in (-1, abi.SkeletonFormat.SKELETON_42):
            frame = self._fetch_as(actor_name, key, abi.SkeletonFormat.SKELETON_42)
            if frame is not None:
                return frame
        if fmt in (-1, abi.SkeletonFormat.SKELETON_32):
            frame = self._fetch_as(actor_name, key, abi.SkeletonFormat.SKELETON_32)
            if frame is not None:
                return frame
        return None

    def _fetch_as(self, actor_name: str, key: bytes, fmt: int) -> GloveFrame | None:
        struct_type = abi.FRAME_STRUCT_BY_FORMAT.get(fmt)
        if struct_type is None:
            return None

        native = struct_type()
        if fmt == abi.SkeletonFormat.SKELETON_42:
            status = self._lib.get_42_frame(key, ctypes.byref(native))
        else:
            status = self._lib.get_32_frame(key, ctypes.byref(native))
        if status != 0:
            return None

        if not mapper.header_is_plausible(native.hdr) and not self._layout_warned:
            self._layout_warned = True
            if self._verbose:
                print(
                    "[MotionGloveSDK] 警告：原生帧头字段异常，"
                    "MotionGloveSDK_cpp 的结构体布局可能已变更，"
                    "请重新运行 scripts/verify_native_abi.py 并更新 src/native/abi.py"
                )

        return mapper.to_glove_frame(actor_name, native, fmt)


def create_backend(library_path: str | None = None, *, verbose: bool = True) -> NativeBackend:
    """加载原生库并创建后端。"""
    return NativeBackend(load_library(library_path), verbose=verbose)
