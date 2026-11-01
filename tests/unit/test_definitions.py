"""
@file  test_definitions.py
@brief 常量与骨架索引映射（definitions.py）一致性单元测试。
@details
覆盖策略
 - 不变量：BONE_NAMES_32/BONE_NAMES/BONE_NAMES_SHORT 的长度分别等于
   32/42/42，且与 C++ 骨架定义一一对应（无重复、无缺失）；
 - BONE_INDEX_MAP_32_TO_42：32→42 索引映射必须是严格递增、覆盖全部
   "非 End 节点"，且绝不指向 *End 索引（4/8/12/16/20/25/29/33/37/41）；
 - 枚举：CHANNEL_ORDER_FROM_STR 覆盖全部 6 种旋转序。

该层为纯数据定义，headless 毫秒级执行。
"""

import pytest

from src.definitions import (
    BONE_INDEX_MAP_32_TO_42,
    BONE_NAMES,
    BONE_NAMES_32,
    BONE_NAMES_SHORT,
    CHANNEL_ORDER_FROM_STR,
    KHHS32_SKELETON_COUNT,
    KHHS42_SKELETON_COUNT,
    BoneIndex,
    ChannelOrder,
    HandGesture,
)

# 42 段骨架中 10 个 *End（末端）节点的索引
END_INDICES = {4, 8, 12, 16, 20, 25, 29, 33, 37, 41}


def test_BoneNames32HasExactly32UniqueEntries():
    """@test   definitions.BoneNames32HasExactly32UniqueEntries
    @brief  BONE_NAMES_32 恰好 32 项且无重复。
    @details 目的：32 段列表发生增删会直接导致 CSV 解析时名称错位
             （decode_glove_csv 按该表顺序填充）。
    @expected len == 32 且 len(set) == 32；首项 "RightHand"
    @priority P0
    """
    # Assert
    assert len(BONE_NAMES_32) == KHHS32_SKELETON_COUNT
    assert len(set(BONE_NAMES_32)) == KHHS32_SKELETON_COUNT
    assert BONE_NAMES_32[0] == "RightHand"


def test_BoneNamesMatchesBoneIndexEnum():
    """@test   definitions.BoneNamesMatchesBoneIndexEnum
    @brief  BONE_NAMES（42 项）与 BoneIndex 枚举成员一一对应。
    @details 目的：BONE_NAMES 由枚举 name 生成，若枚举改名，名称表会同步
             变化——测试锁定"枚举 → 列表"的一致性契约。
    @expected BONE_NAMES == [m.name for m in BoneIndex] 且长度 42
    @priority P0
    """
    # Assert
    assert len(BONE_NAMES) == len(BoneIndex) == KHHS42_SKELETON_COUNT
    assert BONE_NAMES == [m.name for m in BoneIndex]


def test_BoneNamesShortHas42Entries():
    """@test   definitions.BoneNamesShortHas42Entries
    @brief  BONE_NAMES_SHORT 恰好 42 项且无重复。
    @details 目的：短名表用于 BVH 导出与日志，长度错位会静默串位。
    @expected len == 42、len(set) == 42
    @priority P1
    """
    # Assert
    assert len(BONE_NAMES_SHORT) == KHHS42_SKELETON_COUNT
    assert len(set(BONE_NAMES_SHORT)) == KHHS42_SKELETON_COUNT


def test_BoneIndexMap32To42StrictlyIncreasing():
    """@test   definitions.BoneIndexMap32To42StrictlyIncreasing
    @brief  32→42 映射必须严格单调递增（保持手指骨链顺序）。
    @details 目的：映射表乱序会让 3D 视图骨骼连线串扰（父链拉错）。
    @expected 每一项都比前一项大
    @priority P0
    """
    # Assert
    assert len(BONE_INDEX_MAP_32_TO_42) == KHHS32_SKELETON_COUNT
    for prev, cur in zip(BONE_INDEX_MAP_32_TO_42, BONE_INDEX_MAP_32_TO_42[1:]):
        assert cur > prev, f"映射非递增：{prev} -> {cur}"


def test_BoneIndexMap32To42NeverPointsToEndNode():
    """@test   definitions.BoneIndexMap32To42NeverPointsToEndNode
    @brief  32 段流不含 *End 节点，映射目标绝不能是 42 段的 End 索引。
    @details 目的：32 段流是"无 End"骨架（kinemHumanHandsSkeleton32Index_tree.md），
             若映射误指向 END 节点，`End` 节点会被当成真实骨骼读取。
    @expected 映射值集合 == 42 段非 End 索引集合（0..41 去掉 END_INDICES）
    @priority P0
    """
    # Arrange：42 段中所有非 End 索引
    expected = sorted(set(range(KHHS42_SKELETON_COUNT)) - END_INDICES)

    # Assert
    assert sorted(BONE_INDEX_MAP_32_TO_42) == expected


def test_ChannelOrderFromStrCoversAllOrders():
    """@test   definitions.ChannelOrderFromStrCoversAllOrders
    @brief  字符串 → 旋转序映射覆盖全部 6 种序且一一对应。
    @details 目的：decode_glove_csv 用该映射解析 header 中的旋转序，
             漏掉一种序会静默回退 ZXY 造成旋转错误。
    @expected len(CHANNEL_ORDER_FROM_STR) == 6；XYZ→ChannelOrder.XYZ …
    @priority P1
    """
    # Assert
    assert len(CHANNEL_ORDER_FROM_STR) == 6
    for idx, name in enumerate(["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]):
        assert CHANNEL_ORDER_FROM_STR[name] == ChannelOrder(idx)


def test_HandGestureEnumCovers0To15():
    """@test   definitions.HandGestureEnumCovers0To15
    @brief  手势枚举 NONE=0 且 G1..G15 连续递增。
    @details 目的：固件手势值（0..15）到枚举的映射必须连续，缺号会导致
             越界手势回退 NONE 后无法区分。
    @expected len(HandGesture) == 16；HandGesture.G15 == 15
    @priority P2
    """
    # Assert
    assert len(HandGesture) == 16
    assert HandGesture.NONE == 0
    assert HandGesture.G15 == 15