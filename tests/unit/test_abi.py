"""
@file  test_abi.py
@brief ctypes 结构体布局基准（abi.py）单元测试。
@details
覆盖策略
 - 不变量：sizeof 与字段 offset 必须与布局基准一致（VS2022 x64 / GCC x86_64
   实测值，由 scripts/abi_probe.cpp 打印）。这是 Python 转接层与 C++ 库之间
   的二进制契约，一旦漂移，帧数据会整体错位；
 - verify_layout() 返回空列表表示全部一致；
 - FRAME_STRUCT_BY_FORMAT 必须覆盖 32/42 两种格式，缺格式会让 get_frame
   静默返回 None。

无网络、无原生库依赖，headless 毫秒级执行。
"""

import ctypes

import pytest

from src.native import abi


def test_StreamHeaderSizeMatchesBaseline():
    """@test   abi.StreamHeaderSizeMatchesBaseline
    @brief  sizeof(StreamHeader) 必须等于布局基准 131 字节。
    @details 目的：C++ 头文件加字段后 Python 侧若未同步，sizeof 会漂移；
             该用例在 ctypes 层就能抓住，无需编译原生库。
    @expected ctypes.sizeof(StreamHeader) == 131 == EXPECTED_SIZES 基准
    @priority P0
    """
    # Act
    actual = ctypes.sizeof(abi.StreamHeader)

    # Assert
    assert actual == 131
    assert actual == abi.EXPECTED_SIZES["StreamHeader"]


def test_SingleSkeletonSizeMatchesBaseline():
    """@test   abi.SingleSkeletonSizeMatchesBaseline
    @brief  sizeof(SingleSkeleton) 必须等于布局基准 196 字节。
    @details 目的：单段骨骼结构体是 32/42 整帧的重复单元，尺寸错 1 字节
             会让整帧 8375 字节的偏移全部漂移。
    @expected sizeof == 196 == 基准
    @priority P0
    """
    # Act / Assert
    assert ctypes.sizeof(abi.SingleSkeleton) == 196
    assert ctypes.sizeof(abi.SingleSkeleton) == abi.EXPECTED_SIZES["SingleSkeleton"]


def test_FrameStructSizesMatchBaseline():
    """@test   abi.FrameStructSizesMatchBaseline
    @brief  42 段/32 段/OpenXR 整帧尺寸必须等于布局基准。
    @details 目的：整帧是 ctypes 与 C++ 之间按值传递的缓冲区，尺寸不一致
             时 GetSkeletons42Frame 会写越界或读不满。
    @expected 8375 / 6415 / 10335，逐一等于 EXPECTED_SIZES
    @priority P0
    """
    # Assert
    assert ctypes.sizeof(abi.KHHS42PosAttitude) == 8375
    assert ctypes.sizeof(abi.KHHS32PosAttitude) == 6415
    assert ctypes.sizeof(abi.KHHSOpenXRPosAttitude) == 10335
    for name in ("KHHS42PosAttitude", "KHHS32PosAttitude", "KHHSOpenXRPosAttitude"):
        struct = abi.STRUCTS[name]
        assert ctypes.sizeof(struct) == abi.EXPECTED_SIZES[name]


@pytest.mark.parametrize("struct_name,field,offset", [
    ("StreamHeader", "skeleton_format", 91),
    ("StreamHeader", "channel_order", 83),
    ("SingleSkeleton", "skeleton_name", 4),
    ("SingleSkeleton", "quat_xyzw", 80),
    ("KHHS42PosAttitude", "skeletons", 131),
    ("KHHS42PosAttitude", "remote_ip", 8363),
])
def test_KeyFieldOffsetsMatchBaseline(struct_name, field, offset):
    """@test   abi.KeyFieldOffsetsMatchBaseline
    @brief  关键字段 offset 必须与布局基准一致。
    @details 目的：sizeof 一致不代表字段顺序一致（调换两个同类型字段尺寸
             不变但语义全错）。抽查帧格式/通道序/骨骼名/四元数/远端地址
             这些"错位即事故"的字段。
    @expected getattr(struct, field).offset == 基准值
    @priority P0
    """
    # Act
    actual = getattr(abi.STRUCTS[struct_name], field).offset

    # Assert
    assert actual == offset
    assert actual == abi.EXPECTED_OFFSETS[struct_name][field]


def test_VerifyLayoutReturnsNoProblems():
    """@test   abi.VerifyLayoutReturnsNoProblems
    @brief  verify_layout() 必须返回空列表（全部基准一致）。
    @details 目的：scripts/verify_native_abi.py 与测试共用该校验入口，
             返回非空即代表 ctypes 定义与基准漂移。
    @expected verify_layout() == []
    @priority P0
    """
    # Act / Assert
    assert abi.verify_layout() == []


def test_PackIsOneNoImplicitPadding():
    """@test   abi.PackIsOneNoImplicitPadding
    @brief  所有结构体 _pack_=1，无隐式对齐填充。
    @details 目的：C++ 侧 #pragma pack(1)；Python 侧漏写 _pack_ 会让
             c_uint32 之后的字段偏移按 4 字节对齐，与基准不一致。
    @expected 每个结构体 _pack_ == 1
    @priority P0
    """
    # Assert
    for name, struct in abi.STRUCTS.items():
        assert struct._pack_ == 1, f"{name} 缺少 _pack_ = 1"


def test_FrameStructByFormatCovers32And42():
    """@test   abi.FrameStructByFormatCovers32And42
    @brief  帧容器映射必须覆盖 SKELETON_32 与 SKELETON_42 两种格式。
    @details 目的：backend._fetch 按该映射取结构体，缺 32 段条目会让
             旧固件数据流永远取不到帧（静默返回 None）。
    @expected 映射包含 0→KHHS32PosAttitude、1→KHHS42PosAttitude
    @priority P0
    """
    # Assert
    assert abi.FRAME_STRUCT_BY_FORMAT[abi.SkeletonFormat.SKELETON_32] is abi.KHHS32PosAttitude
    assert abi.FRAME_STRUCT_BY_FORMAT[abi.SkeletonFormat.SKELETON_42] is abi.KHHS42PosAttitude


def test_DescribeLayoutCoversAllStructs():
    """@test   abi.DescribeLayoutCoversAllStructs
    @brief  describe_layout() 覆盖全部 5 个结构体并带 sizeof 键。
    @details 目的：该函数是 ABI 探针的 Python 侧数据源，漏结构体会让
             verify_native_abi.py 的 diff 漏报。
    @expected 返回字典包含 5 个键，每项含 'sizeof'
    @priority P2
    """
    # Act
    layout = abi.describe_layout()

    # Assert
    assert set(layout.keys()) == set(abi.STRUCTS.keys())
    for entry in layout.values():
        assert "sizeof" in entry