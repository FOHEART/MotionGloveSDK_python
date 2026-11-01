"""
@file  test_decode_glove_csv.py
@brief CSV 帧解析（decode_glove_csv / parse_header_tokens）单元测试。
@details
覆盖策略
 - 解析解（金标准）：零角欧拉 → 四元数 (0,0,0,1)；绕 X 90° → (wxyz √2/2,√2/2,0,0)，
   与 C++ 侧 decodeAsGloveCSV.cpp 的线上顺序（quat 4 字段 wxyz，pos+att 共 7 字段）对齐；
 - 不变量：GloveFrame.skeletons 数量 == 42/32、bone_index 映射一致性；
 - 边界条件：32 段帧、QUAT 帧直通；
 - 异常场景：数值个数不匹配、非浮点值、空 header、越界手势值、非法 fn
   都必须返回 None 或保持默认值，不得抛异常。

该层可 headless 运行；不依赖网络与原生库。
"""

import math

import pytest

from src.decode_glove_csv import decode_glove_csv, parse_header_tokens
from src.definitions import (
    BONE_INDEX_MAP_32_TO_42,
    BONE_NAMES,
    BONE_NAMES_32,
    ChannelOrder,
    HandGesture,
    SkeletonAttitude,
    SkeletonCoordinate,
    SkeletonPosition,
)

SQRT2_2 = math.sqrt(2.0) / 2.0

# 常用 header：42 段、米、欧拉 ZXY、相对坐标
HEADER_EULER_ZXY = ["Glove1", "pos", "euler", "ZXY", "relative", "fn", "100",
                    "subpackage", "1/1"]


def build_body(skeleton_count: int, euler: tuple[float, float, float],
               position: tuple[float, float, float] = (0.1, 0.2, 0.3)) -> str:
    """构造 group_item_count=7（pos3 + euler3）的 CSV 数值串。

    所有骨骼使用相同的欧拉角与位置，便于按索引抽查。
    """
    items = []
    for _ in range(skeleton_count):
        items.extend([repr(position[0]), repr(position[1]), repr(position[2]),
                      repr(euler[0]), repr(euler[1]), repr(euler[2])])
    return ",".join(items)


# ── parse_header_tokens ──────────────────────────────────────────────────────


def test_ParseHeaderTokens_FullHeaderPopulatesAllFields():
    """@test   decode_glove_csv.ParseHeaderTokens_FullHeaderPopulatesAllFields
    @brief  完整 header 一次性填充姿态/坐标/旋转序等全部字段。
    @details 目的：header token 是 C++ splitHeaderVec 的逐项解析镜像，字段
             漏读会让帧被静默丢弃。用一条真实抓包 header 做端到端检查。
    @expected position=METER、attitude=EULER、order=ZXY、coordinate=RELATIVE
    @priority P0
    """
    # Act
    hdr = parse_header_tokens(HEADER_EULER_ZXY)

    # Assert
    assert hdr.avatar_name == "Glove1"
    assert hdr.skeleton_position == SkeletonPosition.METER
    assert hdr.skeleton_attitude == SkeletonAttitude.EULER
    assert hdr.channel_order == ChannelOrder.ZXY
    assert hdr.skeleton_coordinate == SkeletonCoordinate.RELATIVE


def test_ParseHeaderTokens_EmptyTokensKeepDefaults():
    """@test   decode_glove_csv.ParseHeaderTokens_EmptyTokensKeepDefaults
    @brief  空 token 列表返回全默认的 StreamHeader，不得抛异常。
    @details 目的：UDP 截断包会产生空 header，解析必须安全降级。
    @expected avatar_name 为空串、frame_number 为 0
    @priority P1
    """
    # Act
    hdr = parse_header_tokens([])

    # Assert
    assert hdr.avatar_name == ""
    assert hdr.frame_number == 0


def test_ParseHeaderTokens_FnNotIntegerKeepsDefault():
    """@test   decode_glove_csv.ParseHeaderTokens_FnNotIntegerKeepsDefault
    @brief  fn 后跟非整数时保持默认 0，不得抛 ValueError。
    @details 目的：坏包/半包输入防御。异常输入 → 拒绝并保持原值。
    @expected frame_number == 0
    @priority P1
    """
    # Act
    hdr = parse_header_tokens(["Glove1", "fn", "abc"])

    # Assert
    assert hdr.frame_number == 0


def test_ParseHeaderTokens_GestureValuesMappedToEnum():
    """@test   decode_glove_csv.ParseHeaderTokens_GestureValuesMappedToEnum
    @brief  gesture 3 5 分别映射为左手 G3、右手 G5。
    @details 目的：手势是两个连续 token（左/右），错位读取会把右手值给左手。
    @expected left_hand_gesture == HandGesture.G3、right == G5
    @priority P1
    """
    # Act
    hdr = parse_header_tokens(["Glove1", "gesture", "3", "5"])

    # Assert
    assert hdr.left_hand_gesture == HandGesture.G3
    assert hdr.right_hand_gesture == HandGesture.G5


def test_ParseHeaderTokens_GestureOutOfRangeKeepsDefault():
    """@test   decode_glove_csv.ParseHeaderTokens_GestureOutOfRangeKeepsDefault
    @brief  越界手势值（99）时整条 gesture 字段被拒绝，左右手都保持默认 NONE。
    @details 目的：C++ 枚举值越界读栈垃圾是真实缺陷面；Python 侧约定
             "非合法枚举 → 拒绝并保持原值"。手势是成对 token（左/右）在一个
             try 块内解析，任一值非法即视为该 header 的手势字段整体不可信，
             因此右手值也不采纳——避免出现"左手默认、右手新值"的半错状态。
    @expected left_hand_gesture == right_hand_gesture == HandGesture.NONE
    @priority P0
    """
    # Act
    hdr = parse_header_tokens(["Glove1", "gesture", "99", "5"])

    # Assert：整条字段拒绝，左右手均保持默认
    assert hdr.left_hand_gesture == HandGesture.NONE
    assert hdr.right_hand_gesture == HandGesture.NONE


def test_ParseHeaderTokens_UnknownEulerOrderDefaultsToZXY():
    """@test   decode_glove_csv.ParseHeaderTokens_UnknownEulerOrderDefaultsToZXY
    @brief  未知旋转序字符串（ABC）回退到 MotionGlove 默认序 ZXY。
    @details 目的：C++ MVSDK_ChannelOrder_StringDesc 只认 6 个字符串，
             未收录值按默认序处理——与 decode_glove_csv 的 .get(order, ZXY) 一致。
    @expected channel_order == ChannelOrder.ZXY
    @priority P1
    """
    # Act
    hdr = parse_header_tokens(["Glove1", "euler", "ABC"])

    # Assert
    assert hdr.channel_order == ChannelOrder.ZXY


def test_ParseHeaderTokens_EulerWithoutOrderTokenDefaultsToZXY():
    """@test   decode_glove_csv.ParseHeaderTokens_EulerWithoutOrderTokenDefaultsToZXY
    @brief  "euler" 后缺失序号 token（截断包）回退到 ZXY，不得抛 IndexError。
    @details 目的：header 以 "euler" 结尾是典型截断场景。
    @expected channel_order == ChannelOrder.ZXY
    @priority P1
    """
    # Act
    hdr = parse_header_tokens(["Glove1", "euler"])

    # Assert
    assert hdr.channel_order == ChannelOrder.ZXY


# ── decode_glove_csv：42 段欧拉帧 ───────────────────────────────────────────


def test_DecodeGloveCsv_EulerFrame42PopulatesSkeletons():
    """@test   decode_glove_csv.DecodeGloveCsv_EulerFrame42PopulatesSkeletons
    @brief  42 段欧拉帧（252 个值）解析出 42 条骨骼，位置/欧拉角逐段填充。
    @details 目的：这是 MotionGlove CSV 的主路径。数值个数按
             group_item_count(7) × 42 校验，名称按 BONE_NAMES 顺序对齐。
    @expected len(skeletons)==42；第 0 段 bone_name==BONE_NAMES[0]、
             position==(0.1,0.2,0.3)、euler==(10,20,30)、contains_* 均为 1
    @priority P0
    """
    # Arrange
    body = build_body(42, (10.0, 20.0, 30.0))

    # Act
    frame = decode_glove_csv("Glove1", 100, body, HEADER_EULER_ZXY)

    # Assert
    assert frame is not None
    assert len(frame.skeletons) == 42
    sk = frame.skeletons[0]
    assert sk.bone_index == 0
    assert sk.bone_name == BONE_NAMES[0]
    assert sk.position == pytest.approx([0.1, 0.2, 0.3])
    assert sk.euler_degree == pytest.approx([10.0, 20.0, 30.0])
    assert sk.contains_position == 1
    assert sk.contains_euler_degree == 1
    assert sk.contains_quat_wxyz == 1
    assert frame.header.frame_number == 100
    assert frame.header.avatar_name == "Glove1"


def test_DecodeGloveCsv_ZeroEulerGivesIdentityQuat():
    """@test   decode_glove_csv.DecodeGloveCsv_ZeroEulerGivesIdentityQuat
    @brief  零欧拉角换算出的四元数必须是单位四元数 (1,0,0,0)。
    @details 目的：euler→quat 换算是 CSV 解析链路里唯一的非线性步骤，
             用解析解金标准（零角 → 单位四元数）独立校验，不复制实现公式。
    @expected 第 0 段 quat_wxyz == [1.0, 0.0, 0.0, 0.0]
    @priority P0
    """
    # Arrange
    body = build_body(42, (0.0, 0.0, 0.0))

    # Act
    frame = decode_glove_csv("Glove1", 1, body, HEADER_EULER_ZXY)

    # Assert
    assert frame is not None
    assert frame.skeletons[0].quat_wxyz == pytest.approx([1.0, 0.0, 0.0, 0.0], abs=1e-9)


def test_DecodeGloveCsv_EulerX90GivesHalfAngleQuat():
    """@test   decode_glove_csv.DecodeGloveCsv_EulerX90GivesHalfAngleQuat
    @brief  欧拉 (90,0,0)（ZXY 序）换算结果 == 半角公式 (√2/2,√2/2,0,0)（wxyz）。
    @details 目的：单轴 90° 的四元数由 q=[cos(θ/2), sin(θ/2)·axis] 独立手算，
             是全链路（CSV 数值 → 欧拉 → 四元数）的金标准校验点。
    @expected quat_wxyz == [√2/2, √2/2, 0, 0]，误差 < 1e-6
    @priority P0
    """
    # Arrange
    body = build_body(42, (90.0, 0.0, 0.0))

    # Act
    frame = decode_glove_csv("Glove1", 2, body, HEADER_EULER_ZXY)

    # Assert
    assert frame is not None
    assert frame.skeletons[0].quat_wxyz == pytest.approx(
        [SQRT2_2, SQRT2_2, 0.0, 0.0], abs=1e-6)


def test_DecodeGloveCsv_QuatFramePassesThroughWFirstOrder():
    """@test   decode_glove_csv.DecodeGloveCsv_QuatFramePassesThroughWFirstOrder
    @brief  QUAT 帧的 4 个数值按线上顺序 wxyz 直通，不做任何重排。
    @details 目的：C++ decodeAsGloveCSV.cpp 明确"quat 姿态线上顺序为 wxyz"
             （每段 pos3 + quat4 = 7 字段）；Python 侧必须与 C++ 一致。
             该用例同时锁定：如果上游顺序变为 xyzw，此处会红。
    @expected 第 0 段 quat_wxyz == CSV 前 4 个值 [0.5, 0.5, 0.5, 0.5]
    @priority P0
    """
    # Arrange：QUAT 帧 header（无 euler），每段 7 个值（pos3 + quat4，wxyz）
    header = ["Glove1", "pos", "quat", "relative", "fn", "50", "subpackage", "1/1"]
    values = []
    for _ in range(42):
        values += ["0.1", "0.2", "0.3", "0.5", "0.5", "0.5", "0.5"]
    body = ",".join(values)

    # Act
    frame = decode_glove_csv("Glove1", 50, body, header)

    # Assert
    assert frame is not None
    assert frame.header.skeleton_attitude == SkeletonAttitude.QUAT
    assert frame.skeletons[0].quat_wxyz == pytest.approx([0.5, 0.5, 0.5, 0.5])
    assert frame.skeletons[0].euler_degree == [0.0, 0.0, 0.0]  # 无欧拉角
    assert frame.skeletons[0].contains_euler_degree == 0


def test_DecodeGloveCsv_Frame32MapsBoneIndexTo42():
    """@test   decode_glove_csv.DecodeGloveCsv_Frame32MapsBoneIndexTo42
    @brief  32 段帧解析出 32 条骨骼，bone_index 按 32→42 映射表对齐。
    @details 目的：32 段流是旧固件格式，bone_index 必须映射到 42 段索引空间
             （3D 视图依赖 len(skeletons)==32 + 42 索引）。
    @expected len(skeletons)==32；第 0 段 bone_index==0、名称 BONE_NAMES_32[0]；
             第 5 段 bone_index==BONE_INDEX_MAP_32_TO_42[5]
    @priority P0
    """
    # Arrange
    body = build_body(32, (0.0, 0.0, 0.0))

    # Act
    frame = decode_glove_csv("Glove1", 7, body, HEADER_EULER_ZXY)

    # Assert
    assert frame is not None
    assert len(frame.skeletons) == 32
    assert frame.skeletons[0].bone_index == 0
    assert frame.skeletons[0].bone_name == BONE_NAMES_32[0]
    assert frame.skeletons[5].bone_index == BONE_INDEX_MAP_32_TO_42[5]


# ── 异常 / 非法输入 ─────────────────────────────────────────────────────────


def test_DecodeGloveCsv_ValueCountMismatchReturnsNone():
    """@test   decode_glove_csv.DecodeGloveCsv_ValueCountMismatchReturnsNone
    @brief  数值个数既不等于 42×7 也不等于 32×7 时返回 None。
    @details 目的：半包/粘包的帧不能被静默解析成错位的骨骼数据。
    @expected 返回 None，且不抛异常
    @priority P0
    """
    # Arrange：41 段（287 个值），两个合法长度都不是
    body = build_body(41, (10.0, 20.0, 30.0))

    # Act / Assert
    assert decode_glove_csv("Glove1", 3, body, HEADER_EULER_ZXY) is None


def test_DecodeGloveCsv_NonFloatValueReturnsNone():
    """@test   decode_glove_csv.DecodeGloveCsv_NonFloatValueReturnsNone
    @brief  数值流混入非浮点 token 时整帧丢弃，返回 None。
    @details 目的：坏字符（如时间戳混入数值区）必须让整帧安全降级，
             不能部分填充后返回。
    @expected 返回 None
    @priority P0
    """
    # Arrange
    body = build_body(42, (10.0, 20.0, 30.0)) + ",abc"

    # Act / Assert
    assert decode_glove_csv("Glove1", 4, body, HEADER_EULER_ZXY) is None


def test_DecodeGloveCsv_HeaderWithoutPosOrAttitudeReturnsNone():
    """@test   decode_glove_csv.DecodeGloveCsv_HeaderWithoutPosOrAttitudeReturnsNone
    @brief  header 既无 pos 也无 euler/quat 时 group_item_count=0，返回 None。
    @details 目的：group_item_count==0 分支是防除零/错位读的守卫。
    @expected 返回 None
    @priority P1
    """
    # Arrange：只有 actor 名，没有任何数据描述 token
    body = build_body(42, (0.0, 0.0, 0.0))

    # Act / Assert
    assert decode_glove_csv("Glove1", 5, body, ["Glove1", "relative"]) is None


def test_DecodeGloveCsv_RemoteAddrStoredInFrame():
    """@test   decode_glove_csv.DecodeGloveCsv_RemoteAddrStoredInFrame
    @brief  remote_ip / remote_port 原样写入 GloveFrame。
    @details 目的：CSV 回放路径由调用方提供来源地址（文件名或伪造地址），
             丢失会让 UI 的"数据来源"显示为空。
    @expected frame.remote_ip=="192.168.1.10"、frame.remote_port==5001
    @priority P2
    """
    # Arrange
    body = build_body(42, (0.0, 0.0, 0.0))

    # Act
    frame = decode_glove_csv("Glove1", 6, body, HEADER_EULER_ZXY,
                             remote_ip="192.168.1.10", remote_port=5001)

    # Assert
    assert frame is not None
    assert frame.remote_ip == "192.168.1.10"
    assert frame.remote_port == 5001
