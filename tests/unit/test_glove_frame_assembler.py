"""
@file  test_glove_frame_assembler.py
@brief 分包拼接器（glove_frame_assembler.GloveFrameAssembler）单元测试。
@details
覆盖策略
 - 不变量：乱序/重复分包仍按 subpackage 序号拼接（顺序 == 编号序）；
 - 边界条件：单分包（1/1）立即完成、新 fn 重置旧状态、同 actor 交叉帧；
 - 异常场景：缺逗号、缺 fn、缺 subpackage 字段的包返回 False 且不崩。

对应 C++ GloveSplitFrameMgr 的 Python 参考实现；C++ 侧同样有
readWriteLock_test 独立覆盖线程场景，本文件只测拼接语义。
"""

import pytest

from src.glove_frame_assembler import GloveFrameAssembler

PREFIX = "Glove1 time 2026-04-06 22:10:04.500 pos euler ZXY relative fn {fn}"


def make_packet(fn: int, cur: int, total: int, body: str = "1.0,2.0,3.0") -> str:
    return f"{PREFIX.format(fn=fn)} subpackage {cur}/{total},{body}"


# ── 正常拼接 ────────────────────────────────────────────────────────────────


def test_Assembler_SingleSubpackageCompletesImmediately():
    """@test   glove_frame_assembler.SingleSubpackageCompletesImmediately
    @brief  1/1 单分包包到达即触发回调。
    @details 目的：发最简包（一条 UDP 数据 = 一帧）是无需拆包的常见场景。
    @expected 回调 1 次，回调参数 (actor, fn, body, 4 个 header tokens)
    @priority P0
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append((a, f, b, h)))

    # Act
    handled = asm.feed(make_packet(1, 1, 1, "0.1,0.2"))

    # Assert
    assert handled is True
    assert len(calls) == 1
    actor, fn, body, tokens = calls[0]
    assert actor == "Glove1"
    assert fn == 1
    assert body == "0.1,0.2"


def test_Assembler_TwoSubpackagesConcatenateInOrder():
    """@test   glove_frame_assembler.TwoSubpackagesConcatenateInOrder
    @brief  两分包帧按 subpackage 1、2 的编号顺序直连拼接（无分隔符）。
    @details 目的：subpackage 编号决定 body 拼接顺序（与到达顺序无关），
             颠倒会让骨骼数值错位。C++ 侧用 m_data += s 直连——分包边界
             切在数值边界上，因此无分隔符是正确语义，测试锁定该约定。
    @expected 回调 body == "part1part2"
    @priority P0
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append(b))

    # Act
    asm.feed(make_packet(5, 1, 2, "part1"))
    asm.feed(make_packet(5, 2, 2, "part2"))

    # Assert
    assert calls == ["part1part2"]
    assert asm.complete_frame_count == 1


def test_Assembler_OutOfOrderSubpackagesStillConcatenateInNumberOrder():
    """@test   glove_frame_assembler.OutOfOrderSubpackagesStillConcatenateInNumberOrder
    @brief  先收到 2/2、后收到 1/2 时，仍按编号序（先 1 后 2）拼接。
    @details 目的：UDP 无序到达是常态，拼接顺序必须由编号决定而非到达序。
    @expected 回调 body == "firstsecond"（1/2 内容在前）
    @priority P0
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append(b))

    # Act
    asm.feed(make_packet(6, 2, 2, "second"))
    assert len(calls) == 0
    asm.feed(make_packet(6, 1, 2, "first"))

    # Assert
    assert calls == ["firstsecond"]


def test_Assembler_DuplicateSubpackageDoesNotCompleteTwice():
    """@test   glove_frame_assembler.DuplicateSubpackageDoesNotCompleteTwice
    @brief  重复收到同一分包不会提前触发完成。
    @details 目的：UDP 重传会产生重复分包；received 是集合语义，
             重复包不能让 len(received)==sub_max 提前成立。
    @expected 收 1/2、再 1/2、再 2/2 后仅回调 1 次
    @priority P1
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append((f, b)))

    # Act
    asm.feed(make_packet(9, 1, 2, "A"))
    asm.feed(make_packet(9, 1, 2, "A"))       # 重复
    assert len(calls) == 0
    asm.feed(make_packet(9, 2, 2, "B"))

    # Assert
    assert len(calls) == 1
    assert calls[0] == (9, "AB")


def test_Assembler_NewFrameNumberResetsPartialState():
    """@test   glove_frame_assembler.NewFrameNumberResetsPartialState
    @brief  同一 actor 的新 fn 到来时，上一帧未收齐的分包状态被丢弃。
    @details 目的：丢包后旧帧残留状态若不重置，会与下一帧数值拼接（串帧）。
    @expected 旧 fn 的 1/2 残留不混入新 fn 帧；新帧 fn=8 收齐后 body 只含新帧内容
    @priority P0
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append((f, b)))

    # Act：fn=7 只收到 1/2，然后 fn=8 的两分包到达
    asm.feed(make_packet(7, 1, 2, "OLD"))
    asm.feed(make_packet(8, 1, 2, "new1"))
    asm.feed(make_packet(8, 2, 2, "new2"))

    # Assert
    assert calls == [(8, "new1new2")]


def test_Assembler_MultipleActorsIsolated():
    """@test   glove_frame_assembler.MultipleActorsIsolated
    @brief  不同 actor 的分包状态互不干扰。
    @details 目的：多手套同时在线时（Glove1/Glove2），状态按 actor 分桶；
             混桶会让两帧数值交错。
    @expected 两 actor 各回调 1 次完整帧
    @priority P0
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append((a, f, b)))

    # Act：交错喂包
    p2 = "Glove2 time 2026-04-06 22:10:04.500 pos euler ZXY relative fn 30 subpackage {c}/{t},{b}"
    asm.feed(make_packet(3, 1, 2, "g1-a"))
    asm.feed(p2.format(c=1, t=2, b="g2-a"))
    asm.feed(make_packet(3, 2, 2, "g1-b"))
    asm.feed(p2.format(c=2, t=2, b="g2-b"))

    # Assert
    assert len(calls) == 2
    assert ("Glove1", 3, "g1-ag1-b") in calls
    assert ("Glove2", 30, "g2-ag2-b") in calls


# ── 异常输入 ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_packet", [
    "no comma here",                                   # 缺逗号分界
    f"{PREFIX.format(fn=1)}",                          # 缺 subpackage
    "Glove1 pos euler subpackage 1/1,1.0",             # 缺 fn
    f"{PREFIX.format(fn=2)} subpackage x/2,1.0",       # 分包号非整数
])
def test_Assembler_MalformedPacketReturnsFalse(bad_packet):
    """@test   glove_frame_assembler.MalformedPacketReturnsFalse
    @brief  格式不符的包返回 False 且不触发回调、不抛异常。
    @details 目的：非手套 CSV 包（如心跳、其他协议的文本）会被流经同一个
             feed()；静默跳过是协议无关性的前提。
    @expected handled == False、回调数 == 0
    @priority P0
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append(True))

    # Act
    handled = asm.feed(bad_packet)

    # Assert
    assert handled is False
    assert len(calls) == 0


def test_Assembler_ZeroTotalSubpackagesIsAcceptedButNeverCompletes():
    """@test   glove_frame_assembler.ZeroTotalSubpackagesIsAcceptedButNeverCompletes
    @brief  subpackage 1/0 格式合法（可解析）但永远不会完成帧。
    @details 目的：总分包数 0 意味着需要 0 个分包才算收齐，而 1/0 已多收，
             属于自相矛盾的包。当前实现选择“能解析就返回 True、
             永不触发回调”，测试锁定该语义防止无意变更。
    @expected handled == True、回调数 == 0、complete_frame_count == 0
    @priority P2
    """
    # Arrange
    calls = []
    asm = GloveFrameAssembler(lambda a, f, b, h: calls.append(True))

    # Act
    handled = asm.feed(f"{PREFIX.format(fn=2)} subpackage 1/0,1.0")

    # Assert
    assert handled is True
    assert len(calls) == 0
    assert asm.complete_frame_count == 0