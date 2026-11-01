"""
@file  backend.py
@brief 对上层提供稳定的 Python 语义接口（NativeBackend）。
@details
屏蔽 C++ 导出函数与结构体的细节：上层（src/motionGloveSDK.py、示例程序、
3D 视图）只依赖本文件的方法名与 src/definitions.py 中的数据容器；
MotionGloveSDK_cpp 改动时，通常只需要更新 abi.py（内存布局）与本文件
（调用顺序/语义差异）。

线程安全约定：_actors 由轮询线程写入、GUI 线程读取，操作均在
_actors_lock 保护下进行。
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
    """@brief 基于 C++ MotionGloveSDK 的数据流后端。

    @details 持有一个释放后的原生库句柄 NativeLibrary，并把 C++ 的
             返回码（0 成功 / 负值失败）翻译为 Python 语义返回值。
    """

    name = "native"

    def __init__(self, library: NativeLibrary, *, verbose: bool = True) -> None:
        """@brief 创建后端实例（一般通过 create_backend() 间接创建）。

        @param library 已加载的原生库句柄。
        @param verbose 帧头布局异常时是否打印告警（默认 True）。
        @return 无（None）。
        """
        self._lib = library
        self._verbose = verbose
        self._actors: dict[str, None] = {}
        self._actors_lock = threading.Lock()
        self._last_remote_addr: tuple[str, int] | None = None
        self._layout_warned = False

    def _remember_actor(self, actor_name: str) -> None:
        """@brief 记录数据流名称（按首次发现顺序去重）。

        @details 轮询线程写、GUI 线程读，需要加锁。
        @param actor_name 数据流名称，非空字符串。
        @return 无（None）。
        """
        with self._actors_lock:
            self._actors.setdefault(actor_name, None)

    # -- 元信息 -------------------------------------------------------------

    @property
    def library_path(self) -> str:
        """@brief 已加载原生库的文件路径。@return 绝对路径字符串。"""
        return self._lib.path

    def version(self) -> int:
        """@brief 原生 SDK 版本号。@details 对应 C++ MotionGloveSDK_getVersion()。

        @return 32 位版本整数：(main<<16)|(sub<<8)|patch。
        """
        return int(self._lib.get_version())

    # -- 生命周期 -----------------------------------------------------------

    def listen(self, port: int) -> int:
        """@brief 绑定 UDP 端口并启动 C++ 接收线程。
        @details 对应 C++ MotionGloveSDK_ListenUDPPort()。
        @param port 端口号 1024~65535。
        @return 0 成功 / -1 失败。
        """
        return int(self._lib.listen_udp_port(int(port)))

    def close(self) -> int:
        """@brief 关闭 UDP 连接并等待接收线程退出。
        @details 对应 C++ MotionGloveSDK_CloseUDPPort()。
        @return 0 成功 / -1 失败。
        """
        return int(self._lib.close_udp_port())

    # -- 轮询 ---------------------------------------------------------------

    def is_pending(self, actor_name: str) -> bool:
        """@brief 查询指定数据流是否有新帧。
        @details 对应 C++ MotionGloveSDK_isGloveNewFramePending()；发现新帧
                 时顺便登记 actor 名称。
        @param actor_name 数据流名称。
        @return True 有新帧；False 无新帧或名称无效。
        """
        key = self._encode_name(actor_name)
        if key is None:
            return False
        pending = bool(self._lib.is_new_frame_pending(key))
        if pending:
            self._remember_actor(actor_name)
        return pending

    def reset_pending(self, actor_name: str) -> bool:
        """@brief 清除指定数据流的新帧标志。
        @details 对应 C++ MotionGloveSDK_resetGloveNewFramePending()。
        @param actor_name 数据流名称。
        @return True 清除成功；False 名称无效或未找到。
        """
        key = self._encode_name(actor_name)
        if key is None:
            return False
        reset = bool(self._lib.reset_new_frame_pending(key))
        if reset:
            self._remember_actor(actor_name)
        return reset

    def get_frame(self, actor_name: str) -> GloveFrame | None:
        """@brief 按帧头记录的骨骼格式取回缓存帧并转换成 GloveFrame。

        @details 对应 C++ MotionGloveSDK_GetSkeletonsFrameType() +
                 GetSkeletons42Frame() / GetSkeletons32Frame()。取帧成功后
                 登记 actor 名称（含帧头 avatar_name）并缓存发送方地址。
        @param actor_name 数据流名称。
        @return GloveFrame（成功）；None 名称无效、数据流未知或数据未到达。
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
        """@brief 查询指定数据流的骨骼流格式。

        @param actor_name 数据流名称。
        @return SkeletonFormat.SKELETON_32 / SKELETON_42 / OPENXR；
                未知数据流或该版本库不支持时返回 None。
        """
        key = self._encode_name(actor_name)
        if key is None or self._lib.get_frame_type is None:
            return None
        fmt = self._frame_format(key)
        return None if fmt is None or fmt < 0 else fmt

    # -- Python SDK 额外能力（C++ 侧没有对应接口） --------------------------

    def get_actor_names(self) -> list[str]:
        """@brief 返回已确认存在的数据流名称列表。

        @details C++ SDK 没有枚举数据流的接口，因此这里返回「已经确认
                 存在」的数据流名称：取帧成功的数据流，以及查询到有新帧
                 的数据流（按首次发现顺序）。
        @return list[str]，尚无数据流时为空列表。
        """
        with self._actors_lock:
            return list(self._actors.keys())

    def get_last_remote_addr(self) -> tuple[str, int] | None:
        """@brief 最近一次成功取回的帧的发送方地址。

        @details C++ 侧把发送方地址写在帧结构内部，因此只有取到帧之后才可用。
        @return (ip_str, port_int)；尚未取到任何帧时返回 None。
        """
        return self._last_remote_addr

    # -- 内部 ---------------------------------------------------------------

    @staticmethod
    def _encode_name(actor_name: str) -> bytes | None:
        """@brief 数据流名称 → UTF-8 字节键。

        @param actor_name 数据流名称（str）。
        @return UTF-8 字节串；空名或超过 63 字节返回 None。
        """
        if not actor_name:
            return None
        key = actor_name.encode("utf-8", errors="replace")
        if len(key) > _MAX_ACTOR_NAME_BYTES:
            return None
        return key

    def _frame_format(self, key: bytes) -> int | None:
        """@brief 查询原生侧骨骼格式（内部字节键版本）。

        @param key UTF-8 编码的数据流名称字节串。
        @return 格式编号；旧版原生库无此接口返回 -1（交由 _fetch 试探）；
                调用失败返回 None。
        """
        if self._lib.get_frame_type is None:
            # 旧版原生库没有 Format 接口：交给 _fetch 依次试探
            return -1
        fmt = ctypes.c_uint8(0xFF)
        if self._lib.get_frame_type(key, ctypes.byref(fmt)) != 0:
            return None
        return int(fmt.value)

    def _fetch(self, actor_name: str, key: bytes, fmt: int) -> GloveFrame | None:
        """@brief 按格式取帧，必要时 42/32 依次试探。

        @param actor_name 数据流名称（用于 GloveFrame 回退名）。
        @param key        UTF-8 编码的数据流名称字节串。
        @param fmt        骨骼格式（-1 表示未知，需试探）。
        @return GloveFrame（成功）；两种格式都取不到时返回 None。
        """
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
        """@brief 以指定格式调用原生取帧接口并转换为 GloveFrame。

        @details 帧头不合理（header_is_plausible 为 False）时打印一次
                 布局告警（每进程最多一次），提示重新校验 abi.py。
        @param actor_name 数据流名称。
        @param key        UTF-8 编码的数据流名称字节串。
        @param fmt        骨骼格式（SKELETON_32 / SKELETON_42）。
        @return GloveFrame（成功）；调用失败或格式未知返回 None。
        """
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
    """@brief 加载原生库并创建后端。

    @param library_path 原生库文件或所在目录路径；None 时按 loader 的
                        候选路径搜索（含 MOTIONGLOVE_NATIVE_LIB 环境变量）。
    @param verbose      是否打印布局告警等诊断信息。
    @return NativeBackend 实例。
    @exception MotionGloveNativeError 库缺失或 ABI 不匹配时抛出。
    """
    return NativeBackend(load_library(library_path), verbose=verbose)
