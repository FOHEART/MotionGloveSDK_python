"""
@file  mapper.py
@brief ctypes 原生结构体 → Python 数据容器（GloveFrame）的转换。
@details
把 abi.py 中的原生结构体转换成 src/definitions.py 中的 Python 数据容器，
使上层应用（3D 视图、示例程序）完全不用感知 C++ 侧的结构体布局。

单位约定与 C++ 一致：位置米、欧拉角度、四元数 xyzw（Python 侧对外为 wxyz，
由 to_glove_frame 重排）。32 骨流经 BONE_INDEX_MAP_32_TO_42 映射为 42 骨索引。
测试：tests/unit/test_mapper.py。
"""

from __future__ import annotations

import socket

from ..definitions import (
    BONE_INDEX_MAP_32_TO_42,
    BONE_NAMES,
    BONE_NAMES_32,
    ChannelOrder,
    GloveFrame,
    HandGesture,
    SingleSkeleton,
    SkeletonAttitude,
    SkeletonCoordinate,
    SkeletonPosition,
    StreamHeader,
)
from . import abi


def _to_enum(enum_type, value: int, default):
    """@brief int → 枚举的安全转换，越界值回退默认枚举。

    @param enum_type 目标枚举类（IntEnum）。
    @param value     原始整数值（来自 C 结构体字段）。
    @param default   value 不在枚举取值范围内时返回的默认枚举成员。
    @return 枚举成员。
    """
    try:
        return enum_type(value)
    except ValueError:
        return default


def decode_name(raw: bytes | bytearray, length: int | None = None) -> str:
    """@brief 把 C++ 固定长度字符缓冲区解码为 str。

    @details 解码顺序：显式 length 截断（若给出且合法）→ 首个 NUL 截断 →
             UTF-8 解码（非法字节以 U+FFFD 替换，不抛异常）。
    @param raw    原始字节缓冲区（如 SingleSkeleton.skeleton_name）。
    @param length 显式长度（如 avatar_name_length）；None 表示不按长度截断。
    @return 解码后的名称字符串；空缓冲区返回空字符串。
    """
    data = bytes(raw)
    if length is not None and 0 <= length <= len(data):
        data = data[:length]
    data = data.split(b"\x00", 1)[0]
    return data.decode("utf-8", errors="replace")


def decode_remote_port(raw_port: int) -> int:
    """@brief 网络字节序端口号 → 主机字节序。

    @details C++ 侧把 sockaddr_in.sin_port 直接存进 remotePort（网络字节序），
             这里用 ntohs 转换。若上游改成 htons 转换，只需修改此函数。
    @param raw_port 网络字节序端口号（uint32）；≤ 0 视为无效返回 0。
    @return 主机字节序端口号（0~65535）。
    """
    if raw_port <= 0:
        return 0
    return socket.ntohs(raw_port & 0xFFFF)


def to_stream_header(hdr: abi.StreamHeader) -> StreamHeader:
    """@brief 原生 StreamHeader → Python StreamHeader。

    @details 逐字段复制；avatar_name 经 decode_name（按 avatar_name_length
             截断）；各枚举字段经 _to_enum 转换，越界值回退默认成员。
    @param hdr ctypes 侧 StreamHeader 结构体（已由原生库填充）。
    @return src.definitions.StreamHeader 数据容器。
    """
    return StreamHeader(
        protocol_version=hdr.protocol_version,
        avatar_name=decode_name(hdr.avatar_name, hdr.avatar_name_length),
        suit_number=hdr.suit_number,
        frame_number=hdr.frame_number,
        body_skeleton_count=hdr.body_skeleton_count,
        left_figure_skeleton_count=hdr.left_figure_skeleton_count,
        right_figure_skeleton_count=hdr.right_figure_skeleton_count,
        skeleton_position=_to_enum(
            SkeletonPosition, hdr.skeleton_position, SkeletonPosition.NONE
        ),
        skeleton_attitude=_to_enum(
            SkeletonAttitude, hdr.skeleton_attitude, SkeletonAttitude.EULER
        ),
        skeleton_coordinate=_to_enum(
            SkeletonCoordinate, hdr.skeleton_coordinate, SkeletonCoordinate.RELATIVE
        ),
        channel_order=_to_enum(ChannelOrder, hdr.channel_order, ChannelOrder.ZXY),
        left_hand_gesture=_to_enum(HandGesture, hdr.left_hand_gesture, HandGesture.NONE),
        right_hand_gesture=_to_enum(HandGesture, hdr.right_hand_gesture, HandGesture.NONE),
    )


def _bone_index_and_name(fmt: int, stream_index: int, native: abi.SingleSkeleton) -> tuple[int, str]:
    """@brief 把原生骨骼段映射为 42 段索引与骨骼名称。

    @details 42 骨流直接用 skeleton_index，32 骨流查 BONE_INDEX_MAP_32_TO_42；
             原生名称为空时回退到对应骨骼名称表条目。
    @param fmt          骨骼流格式（abi.SkeletonFormat 值）。
    @param stream_index 该骨骼在流中的序号（0-based）。
    @param native       ctypes 侧 SingleSkeleton 结构体。
    @return (bone_index, bone_name) 二元组。
    """
    native_name = decode_name(native.skeleton_name)

    if fmt == abi.SkeletonFormat.SKELETON_42:
        index = native.skeleton_index
        fallback = BONE_NAMES[index] if 0 <= index < len(BONE_NAMES) else ""
    else:
        index = (
            BONE_INDEX_MAP_32_TO_42[stream_index]
            if stream_index < len(BONE_INDEX_MAP_32_TO_42)
            else -1
        )
        fallback = BONE_NAMES_32[stream_index] if stream_index < len(BONE_NAMES_32) else ""

    return index, (native_name or fallback)


def to_glove_frame(actor: str, native_frame, fmt: int) -> GloveFrame:
    """@brief 把 KHHS32PosAttitude / KHHS42PosAttitude 转换成 GloveFrame。

    @details 原生结构体没有 contains_* 标志位，因此按帧头的
             skeletonPosition / skeletonAttitude 推导，语义与旧版 Python
             解析器保持一致。四元数从原生 xyzw 重排为对外 wxyz。
    @param actor        数据流名称（avatar_name 为空时用作回退）。
    @param native_frame ctypes 侧整帧结构体（KHHS32PosAttitude 或 KHHS42PosAttitude）。
    @param fmt          骨骼流格式（abi.SkeletonFormat 值）。
    @return 填充完成的 GloveFrame 数据容器。
    """
    header = to_stream_header(native_frame.hdr)
    header.avatar_name = header.avatar_name or actor

    has_position = native_frame.hdr.skeleton_position == abi.SkeletonPosition.METER
    attitude = native_frame.hdr.skeleton_attitude

    skeletons: list[SingleSkeleton] = []
    for stream_index, native in enumerate(native_frame.skeletons):
        index, name = _bone_index_and_name(fmt, stream_index, native)

        quat_xyzw = native.quat_xyzw
        skel = SingleSkeleton(
            bone_index=index,
            bone_name=name,
            contains_position=1 if has_position else 0,
            contains_quat_wxyz=1 if attitude in (
                abi.SkeletonAttitude.EULER, abi.SkeletonAttitude.QUAT
            ) else 0,
            contains_euler_degree=1 if attitude == abi.SkeletonAttitude.EULER else 0,
            position=list(native.position_meter),
            quat_wxyz=[quat_xyzw[3], quat_xyzw[0], quat_xyzw[1], quat_xyzw[2]],
            euler_degree=list(native.euler_degree),
        )
        skeletons.append(skel)

    return GloveFrame(
        header=header,
        skeletons=skeletons,
        remote_ip=".".join(str(b) for b in native_frame.remote_ip),
        remote_port=decode_remote_port(native_frame.remote_port),
    )


def header_is_plausible(hdr: abi.StreamHeader) -> bool:
    """@brief 帧头合理性检查（哨兵值越界即 False）。

    @details 若 C++ 侧结构体布局发生变化而 abi.py 未同步，字段会错位，
             这里能尽早发现（返回 False 时调用方应打印告警）。检查项：
             协议版本 ≤ 0x0FFF、名称长度 < 64、骨骼格式 ≤ OPENXR、
             骨骼数 ≤ 0x40。
    @param hdr ctypes 侧 StreamHeader 结构体。
    @return True 帧头字段取值合理；False 疑似布局错位。
    """
    return (
        hdr.protocol_version <= 0x0FFF
        and hdr.avatar_name_length < abi.ACTOR_NAME_LEN_MAX
        and hdr.skeleton_format <= abi.SkeletonFormat.OPENXR
        and hdr.body_skeleton_count <= 0x40
    )
