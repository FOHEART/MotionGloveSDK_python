"""
@file  test_mapper.py
@brief 原生结构体 → GloveFrame 转换（native/mapper.py）单元测试。
@details
覆盖策略
 - 解析解（金标准）：远端端口网络字节序 ntohs（5001 ↔ 0x8913）；
 - 不变量：四元数 xyzw→wxyz 只做分量重排；32 段流 bone_index 走映射表；
 - 边界条件：帧头空名回退 actor 参数；
 - 异常场景：越界枚举值（如 skeleton_position=200）回退默认枚举；
   帧头不合理（skeleton_format=255 等）被 header_is_plausible 拒绝。

全部用 ctypes 现场构造原生结构体，无网络、无原生库依赖。
"""

import ctypes
import socket

import pytest

from src.definitions import (
    BONE_INDEX_MAP_32_TO_42,
    ChannelOrder,
    SkeletonAttitude,
    SkeletonCoordinate,
    SkeletonPosition,
)
from src.native import abi, mapper


def make_header(**overrides) -> abi.StreamHeader:
    """构造一个合法的 42 段、米、欧拉 ZXY 帧头，字段可覆盖。"""
    hdr = abi.StreamHeader()
    name = overrides.pop("avatar_name", b"Glove1")
    hdr.avatar_name_length = len(name)
    for i, byte in enumerate(name):
        hdr.avatar_name[i] = byte
    hdr.frame_number = 100
    hdr.body_skeleton_count = 1
    hdr.skeleton_position = abi.SkeletonPosition.METER
    hdr.skeleton_attitude = abi.SkeletonAttitude.EULER
    hdr.skeleton_coordinate = abi.SkeletonCoordinate.RELATIVE
    # abi 层没有 ChannelOrder 枚举，channel_order 是裸 uint8（4 == ZXY）
    hdr.channel_order = int(ChannelOrder.ZXY)
    hdr.skeleton_format = abi.SkeletonFormat.SKELETON_42
    for key, value in overrides.items():
        setattr(hdr, key, value)
    return hdr


def make_frame_42() -> abi.KHHS42PosAttitude:
    """构造一帧 42 段原生帧：第 0 段写入特征值，其余保持零。"""
    frame = abi.KHHS42PosAttitude()
    frame.hdr = make_header()
    sk = frame.skeletons[0]
    sk.skeleton_index = 0
    sk.skeleton_name = b"RightHand"
    sk.position_meter[0] = 1.0
    sk.position_meter[1] = 2.0
    sk.position_meter[2] = 3.0
    # C++ 内部 quat_xyzw 布局：写入 (1,2,3,4) 检查重排后 wxyz == (4,1,2,3)
    sk.quat_xyzw[0] = 1.0
    sk.quat_xyzw[1] = 2.0
    sk.quat_xyzw[2] = 3.0
    sk.quat_xyzw[3] = 4.0
    sk.euler_degree[0] = 10.0
    sk.euler_degree[1] = 20.0
    sk.euler_degree[2] = 30.0
    frame.remote_ip[0] = 192
    frame.remote_ip[1] = 168
    frame.remote_ip[2] = 1
    frame.remote_ip[3] = 10
    frame.remote_port = socket.htons(5001)   # 网络字节序写入，与 C++ 一致
    return frame


# ── decode_name / decode_remote_port ────────────────────────────────────────


def test_DecodeName_StopsAtFirstNul():
    """@test   mapper.DecodeName_StopsAtFirstNul
    @brief  名称缓冲区在第一个 NUL 处截断。
    @details 目的：C++ 固定 64 字节缓冲区尾部是残留垃圾，不截断会把
             乱码带进 UI 与 actor 枚举。
    @expected b"Glove1\\x00junk" → "Glove1"
    @priority P0
    """
    # Act / Assert
    assert mapper.decode_name(b"Glove1\x00junkjunk") == "Glove1"


def test_DecodeName_ExplicitLengthTruncatesBeforeNul():
    """@test   mapper.DecodeName_ExplicitLengthTruncatesBeforeNul
    @brief  显式长度优先于 NUL 截断。
    @details 目的：C++ 帧头带 avatar_name_length；两者不一致时以长度为准
             （长度是权威字段）。
    @expected b"ABCDEF"、length=3 → "ABC"
    @priority P1
    """
    # Act / Assert
    assert mapper.decode_name(b"ABCDEF", 3) == "ABC"


def test_DecodeName_InvalidUtf8ReplacedNotRaised():
    """@test   mapper.DecodeName_InvalidUtf8ReplacedNotRaised
    @brief  非法 UTF-8 字节被替换（errors=replace），不抛异常。
    @details 目的：坏包不应让轮询线程崩溃。
    @expected b"\\xff\\xfe" 解码成功且包含替换符
    @priority P1
    """
    # Act
    result = mapper.decode_name(b"\xff\xfe")

    # Assert
    assert "\ufffd" in result


def test_DecodeRemotePort_NetworkByteOrderToHost():
    """@test   mapper.DecodeRemotePort_NetworkByteOrderToHost
    @brief  网络字节序端口 0x8913 解码为主机序 5001。
    @details 目的：C++ 把 sockaddr_in.sin_port 原样存进 remotePort（大端），
             不 ntohs 的话端口会显示为 35091 之类的错值。
    @expected decode_remote_port(socket.htons(5001)) == 5001
    @priority P0
    """
    # Arrange
    raw = socket.htons(5001)   # 独立计算，不复制实现

    # Act / Assert
    assert mapper.decode_remote_port(raw) == 5001


def test_DecodeRemotePort_NonPositiveReturnsZero():
    """@test   mapper.DecodeRemotePort_NonPositiveReturnsZero
    @brief  非正端口（0 / 负值）返回 0，不参与 ntohs。
    @details 目的：未收到帧时 remotePort 为 0，ntohs(0) 虽无害但负值会
             产生意外大数，统一钳制为 0。
    @expected decode_remote_port(0) == 0、decode_remote_port(-1) == 0
    @priority P1
    """
    # Act / Assert
    assert mapper.decode_remote_port(0) == 0
    assert mapper.decode_remote_port(-1) == 0


# ── to_glove_frame ──────────────────────────────────────────────────────────


def test_ToGloveFrame_QuatReorderedXyzwToWxyz():
    """@test   mapper.ToGloveFrame_QuatReorderedXyzwToWxyz
    @brief  原生 quat_xyzw (1,2,3,4) 映射后 quat_wxyz == (4,1,2,3)。
    @details 目的：xyzw↔wxyz 重排是转接层最高频的语义差异，写反会让
             3D 视图整体姿态错乱（不报错、只是"转得不对"，极难排查）。
    @expected 第 0 段 quat_wxyz == [4.0, 1.0, 2.0, 3.0]
    @priority P0
    """
    # Act
    frame = mapper.to_glove_frame("Glove1", make_frame_42(), abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame.skeletons[0].quat_wxyz == pytest.approx([4.0, 1.0, 2.0, 3.0])


def test_ToGloveFrame_PositionEulerDirectPass():
    """@test   mapper.ToGloveFrame_PositionEulerDirectPass
    @brief  位置（米）与欧拉角（度）直通不换算。
    @details 目的：mapper 不做单位换算（与 C++ 约定一致），若误加 ×100
             之类的缩放，骨骼位置会整体放大。
    @expected position == [1,2,3]、euler_degree == [10,20,30]
    @priority P0
    """
    # Act
    frame = mapper.to_glove_frame("Glove1", make_frame_42(), abi.SkeletonFormat.SKELETON_42)

    # Assert
    sk = frame.skeletons[0]
    assert sk.position == pytest.approx([1.0, 2.0, 3.0])
    assert sk.euler_degree == pytest.approx([10.0, 20.0, 30.0])


def test_ToGloveFrame_RemoteAddrDecoded():
    """@test   mapper.ToGloveFrame_RemoteAddrDecoded
    @brief  IP 四元组与网络序端口都被正确解码为可读形式。
    @details 目的：IP 用 "." 连接、端口 ntohs，两处都错则 UI 显示乱值。
    @expected remote_ip=="192.168.1.10"、remote_port==5001
    @priority P0
    """
    # Act
    frame = mapper.to_glove_frame("Glove1", make_frame_42(), abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame.remote_ip == "192.168.1.10"
    assert frame.remote_port == 5001


def test_ToGloveFrame_ContainsFlagsDerivedFromHeader():
    """@test   mapper.ToGloveFrame_ContainsFlagsDerivedFromHeader
    @brief  contains_* 标志由帧头 skeletonPosition/Attitude 推导。
    @details 目的：原生结构体没有 contains_* 位，mapper 必须按帧头推导；
             推导错会让上层在"有位置"帧上读到假位置。
    @expected 米 + 欧拉帧：contains_position/quat/euler 全为 1；
             NONE 姿态帧：三个标志全为 0
    @priority P0
    """
    # Act：欧拉帧
    frame = mapper.to_glove_frame("Glove1", make_frame_42(), abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame.skeletons[0].contains_position == 1
    assert frame.skeletons[0].contains_quat_wxyz == 1
    assert frame.skeletons[0].contains_euler_degree == 1

    # Act：姿态/位置全 NONE 的帧
    native = abi.KHHS42PosAttitude()
    native.hdr = make_header(skeleton_position=abi.SkeletonPosition.NONE,
                             skeleton_attitude=abi.SkeletonAttitude.NONE)
    frame2 = mapper.to_glove_frame("Glove1", native, abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame2.skeletons[0].contains_position == 0
    assert frame2.skeletons[0].contains_quat_wxyz == 0
    assert frame2.skeletons[0].contains_euler_degree == 0


def test_ToGloveFrame_EmptyNativeNameFallsBackToBoneTable():
    """@test   mapper.ToGloveFrame_EmptyNativeNameFallsBackToBoneTable
    @brief  原生骨骼名为空时回退到 42 段骨骼名表按索引取值。
    @details 目的：旧固件不填 skeleton_name，缺失回退让 UI 始终能显示
             骨骼名称（42 段流按 BONE_NAMES[index]，32 段流按 BONE_NAMES_32）。
    @expected 第 0 段 bone_name == "RightHand"（BONE_NAMES[0]）
    @priority P1
    """
    # Arrange：清空原生名
    native = make_frame_42()
    native.skeletons[0].skeleton_name = b"\x00" * abi.SKELETON_NAME_LEN

    # Act
    frame = mapper.to_glove_frame("Glove1", native, abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame.skeletons[0].bone_name == "RightHand"


def test_ToGloveFrame_Format32UsesIndexMap():
    """@test   mapper.ToGloveFrame_Format32UsesIndexMap
    @brief  32 段帧的 bone_index 按 BONE_INDEX_MAP_32_TO_42 映射。
    @details 目的：32 段流的 stream_index 与 42 段索引不同，不映射会让
             3D 视图把小指骨骼画到中指位置。
    @expected stream_index 5 的骨骼 bone_index == 映射表[5]
    @priority P0
    """
    # Arrange
    native = abi.KHHS32PosAttitude()
    native.hdr = make_header(skeleton_format=abi.SkeletonFormat.SKELETON_32)

    # Act
    frame = mapper.to_glove_frame("Glove1", native, abi.SkeletonFormat.SKELETON_32)

    # Assert
    assert len(frame.skeletons) == 32
    assert frame.skeletons[5].bone_index == BONE_INDEX_MAP_32_TO_42[5]


def test_ToGloveFrame_OutOfRangeEnumFallsBackToDefault():
    """@test   mapper.ToGloveFrame_OutOfRangeEnumFallsBackToDefault
    @brief  越界枚举值（如 skeleton_position=200）回退到默认枚举。
    @details 目的：C++ 结构体字段是裸 uint8，坏数据/布局漂移会产生越界值；
             Python IntEnum 直接构造会抛 ValueError 让轮询线程崩溃，
             约定是拒绝该值并回退默认。
    @expected position=200 → SkeletonPosition.NONE；attitude=200 → EULER 默认
    @priority P0
    """
    # Arrange
    native = abi.KHHS42PosAttitude()
    native.hdr = make_header(skeleton_position=200, skeleton_attitude=200)

    # Act
    frame = mapper.to_glove_frame("Glove1", native, abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame.header.skeleton_position == SkeletonPosition.NONE
    assert frame.header.skeleton_attitude == SkeletonAttitude.EULER


def test_ToGloveFrame_EmptyHeaderNameUsesActorParam():
    """@test   mapper.ToGloveFrame_EmptyHeaderNameUsesActorParam
    @brief  帧头 avatar_name 为空时，header.avatar_name 回退 actor 参数。
    @details 目的：get_frame 的调用方按名称轮询，帧头空名会让 actor 枚举
             出现空字符串条目。
    @expected frame.header.avatar_name == "Glove1"
    @priority P1
    """
    # Arrange：帧头无名称
    native = make_frame_42()
    native.hdr.avatar_name_length = 0
    for i in range(abi.ACTOR_NAME_LEN_MAX):
        native.hdr.avatar_name[i] = 0

    # Act
    frame = mapper.to_glove_frame("Glove1", native, abi.SkeletonFormat.SKELETON_42)

    # Assert
    assert frame.header.avatar_name == "Glove1"


# ── header_is_plausible ─────────────────────────────────────────────────────


def test_HeaderIsPlausible_AcceptsWellFormedHeader():
    """@test   mapper.HeaderIsPlausible_AcceptsWellFormedHeader
    @brief  合法帧头通过合理性检查。
    @details 目的：该检查是 ABI 漂移的第一道防线，合法帧必须全绿。
    @expected make_header() → True
    @priority P0
    """
    # Act / Assert
    assert mapper.header_is_plausible(make_header()) is True


@pytest.mark.parametrize("field,value", [
    ("skeleton_format", 255),          # 超出 OPENXR(2)
    ("avatar_name_length", 200),       # 超出 64 字节缓冲区
    ("protocol_version", 0x8000),      # 超出 0x0FFF（uint16 域内）
    ("body_skeleton_count", 100),      # 超出 0x40
])
def test_HeaderIsPlausible_RejectsImplausibleFields(field, value):
    """@test   mapper.HeaderIsPlausible_RejectsImplausibleFields
    @brief  单字段越界即判定帧头不合理（ABI 漂移信号）。
    @details 目的：abi.py 未同步时字段会错位读出垃圾值；四个哨兵字段中
             任一越界都应拒绝，让调用方打印"请重跑 verify_native_abi"。
    @expected header_is_plausible == False
    @priority P0
    """
    # Arrange
    hdr = make_header(**{field: value})

    # Act / Assert
    assert mapper.header_is_plausible(hdr) is False