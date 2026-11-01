"""
mapper.py - MotionGloveSDK Python 转接层
把 ctypes 原生结构体转换成 src/definitions.py 中的 Python 数据容器，
使上层应用（3D 视图、示例程序）完全不用感知 C++ 侧的结构体布局。

单位约定与 C++ 一致：位置米、欧拉角度、四元数 xyzw（Python 侧对外为 wxyz）。
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
    try:
        return enum_type(value)
    except ValueError:
        return default


def decode_name(raw: bytes | bytearray, length: int | None = None) -> str:
    """把 C++ 固定长度字符缓冲区解码为 str（按 NUL 或显式长度截断）。"""
    data = bytes(raw)
    if length is not None and 0 <= length <= len(data):
        data = data[:length]
    data = data.split(b"\x00", 1)[0]
    return data.decode("utf-8", errors="replace")


def decode_remote_port(raw_port: int) -> int:
    """
    C++ 侧把 sockaddr_in.sin_port 直接存进 remotePort（网络字节序），
    这里转换为主机字节序。若上游改成 htons 转换，只需修改此函数。
    """
    if raw_port <= 0:
        return 0
    return socket.ntohs(raw_port & 0xFFFF)


def to_stream_header(hdr: abi.StreamHeader) -> StreamHeader:
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
    """把原生骨骼段映射为 42 段索引与骨骼名称。"""
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
    """
    把 KHHS32PosAttitude / KHHS42PosAttitude 转换成 GloveFrame。

    原生结构体没有 contains_* 标志位，因此按帧头的 skeletonPosition /
    skeletonAttitude 推导，语义与旧版 Python 解析器保持一致。
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
    """
    帧头合理性检查：若 C++ 侧结构体布局发生变化而 abi.py 未同步，
    字段会错位，这里能尽早发现（返回 False 时调用方应打印告警）。
    """
    return (
        hdr.protocol_version <= 0x0FFF
        and hdr.avatar_name_length < abi.ACTOR_NAME_LEN_MAX
        and hdr.skeleton_format <= abi.SkeletonFormat.OPENXR
        and hdr.body_skeleton_count <= 0x40
    )
