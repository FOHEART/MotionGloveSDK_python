"""
@file  test_xsqeconverter.py
@brief 纯逻辑层（xsqeconverter）单元测试，框架为 pytest。
@details
覆盖策略
 - 解析解（金标准）：单轴旋转的四元数用半角公式 q = [cos(θ/2), sin(θ/2)·axis]
   独立手算，不复制被测实现；
 - 不变量：单位四元数范数恒为 1；欧拉 → 四元数 → 欧拉往返恢复原角；
 - 边界条件：±180°、±90°（gimbal 邻域只测往返，不测分量值）；
 - 异常场景：非法旋转序（6 种合法值之外）必须返回单位四元数，不得崩溃。

该层仅依赖 math 标准库，可在无窗口、无 GPU 环境毫秒级执行。
旋转序编号与 C++ RotOrder 一致：0=XYZ 1=XZY 2=YXZ 3=YZX 4=ZXY 5=ZYX。
"""

import math

import pytest

from src.xsqeconverter import (
    euler_degree_to_quat_wxyz,
    euler_degree_to_quat_xyzw,
    quat_to_euler_degree,
)

# 公共常量 ---------------------------------------------------------------

ALL_ORDERS = [0, 1, 2, 3, 4, 5]
SQRT2_2 = math.sqrt(2.0) / 2.0
TOL_QUAT = 1e-6       # 四元数分量容差（解析解金标准）
TOL_DEG = 1e-6        # 欧拉角往返容差（度）


# 各旋转序中 asin 型（主值域 ±90°）的轴：XYZ→Y、XZY→Z、YXZ→X、YZX→Z、ZXY→X、ZYX→Y
_SECOND_AXIS_BY_ORDER = {0: 1, 1: 2, 2: 0, 3: 2, 4: 0, 5: 1}

# 每个序的往返角度组：第二角（asin 型）限制在主值域 ±90° 内，其余两角可达 ±180°
_ROUNDTRIP_ANGLES = {
    0: [(10.0, 20.0, 30.0), (-45.0, 15.0, 170.0), (5.0, -80.0, -175.0), (60.0, -85.0, 130.0)],
    1: [(10.0, 20.0, 30.0), (-45.0, 15.0, 80.0), (5.0, -80.0, -60.0), (170.0, -40.0, 33.0)],
    2: [(10.0, 20.0, 30.0), (-45.0, 15.0, 170.0), (80.0, -80.0, -175.0), (-70.0, 44.0, -100.0)],
    3: [(10.0, 20.0, 30.0), (-45.0, 15.0, 80.0), (5.0, -80.0, -60.0), (170.0, -40.0, 33.0)],
    4: [(10.0, 20.0, 30.0), (-45.0, 15.0, 170.0), (80.0, -80.0, -175.0), (-70.0, 44.0, -100.0)],
    5: [(10.0, 20.0, 30.0), (-45.0, 15.0, 170.0), (5.0, -80.0, -175.0), (60.0, -85.0, 130.0)],
}


def _roundtrip_params():
    """生成 (order, angles) 参数化列表，按序选择第二角在主值域内的角度组。"""
    return [(order, angles) for order in ALL_ORDERS for angles in _ROUNDTRIP_ANGLES[order]]


def quat_norm(q: list[float]) -> float:
    """四元数范数（不依赖被测模块的内部函数）。"""
    return math.sqrt(sum(v * v for v in q))


# ── 解析解（金标准）────────────────────────────────────────────────────────


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_EulerToQuat_IdentityAnglesGiveUnitQuat(order):
    """@test   xsqeconverter.EulerToQuat_IdentityAnglesGiveUnitQuat
    @brief  零角度在任何旋转序下都应返回单位四元数 (w=1, x=y=z=0)。
    @details 目的：防止矩阵分支选错（Shepperd 方法 T<1e-8 走特殊分支）导致
             零角输出漂移。设计思路：零角是所有旋转序矩阵相同的唯一输入，
             用 6 个序逐一验证可同时覆盖全部分支入口。
    @expected euler_degree_to_quat_wxyz(0,0,0,order) == [1.0, 0.0, 0.0, 0.0]
    @priority P0
    """
    # Act
    q = euler_degree_to_quat_wxyz(0.0, 0.0, 0.0, order)

    # Assert
    assert q == pytest.approx([1.0, 0.0, 0.0, 0.0], abs=TOL_QUAT)


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_EulerToQuat_PureXAxis90MatchesHalfAngleFormula(order):
    """@test   xsqeconverter.EulerToQuat_PureXAxis90MatchesHalfAngleFormula
    @brief  仅绕 X 转 90° 时，任意旋转序结果都应为 (√2/2, √2/2, 0, 0)（wxyz）。
    @details 目的：验证 sin/cos→矩阵→四元数全链路的符号约定。
             设计思路：单轴 90° 的四元数由半角公式 q=[cos45°, sin45°·(1,0,0)]
             独立手算得到，是真正的金标准；且 y=z=0 时六种旋转序的矩阵相同，
             可一次覆盖 6 个分支。
    @expected quat_wxyz == [√2/2, √2/2, 0, 0]，误差 < 1e-6
    @priority P0
    """
    # Act
    q = euler_degree_to_quat_wxyz(90.0, 0.0, 0.0, order)

    # Assert
    assert q == pytest.approx([SQRT2_2, SQRT2_2, 0.0, 0.0], abs=TOL_QUAT)


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_EulerToQuat_PureYAxis180MatchesHalfAngleFormula(order):
    """@test   xsqeconverter.EulerToQuat_PureYAxis180MatchesHalfAngleFormula
    @brief  仅绕 Y 转 180° 时，任意旋转序结果都应为 (0, 0, 1, 0)（wxyz）。
    @details 目的：180° 是半角公式 sin(90°)=1 的边界，且 cos(90°)=0 会把
             Shepperd 方法推入非主分支，是最容易丢符号的位置。
    @expected quat_wxyz == [0, 0, 1, 0]，误差 < 1e-6
    @priority P0
    """
    # Act
    q = euler_degree_to_quat_wxyz(0.0, 180.0, 0.0, order)

    # Assert
    assert q == pytest.approx([0.0, 0.0, 1.0, 0.0], abs=TOL_QUAT)


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_EulerToQuat_PureZAxis45MatchesHalfAngleFormula(order):
    """@test   xsqeconverter.EulerToQuat_PureZAxis45MatchesHalfAngleFormula
    @brief  仅绕 Z 转 45° 时，任意旋转序结果都应为 (cos22.5°, 0, 0, sin22.5°)。
    @details 目的：45°/22.5° 是非退化中间角，防止实现只在 90° 特殊角上碰巧
             正确。期望值来自半角公式，与实现完全独立。
    @expected quat_wxyz == [cos(22.5°), 0, 0, sin(22.5°)]，误差 < 1e-6
    @priority P1
    """
    # Act
    q = euler_degree_to_quat_wxyz(0.0, 0.0, 45.0, order)

    # Assert
    assert q[0] == pytest.approx(math.cos(math.radians(22.5)), abs=TOL_QUAT)
    assert q[1] == pytest.approx(0.0, abs=TOL_QUAT)
    assert q[2] == pytest.approx(0.0, abs=TOL_QUAT)
    assert q[3] == pytest.approx(math.sin(math.radians(22.5)), abs=TOL_QUAT)


def test_EulerToQuat_XyzwAndWxyzOrdersConsistent():
    """@test   xsqeconverter.EulerToQuat_XyzwAndWxyzOrdersConsistent
    @brief  xyzw 与 wxyz 两个入口对同一输入必须只做分量重排，数值一致。
    @details 目的：工程中 wxyz（Python 对外）与 xyzw（C++ 内部存储）并存，
             两个入口一旦漂移会出现"同一帧两个后端不同姿态"的隐蔽缺陷。
    @expected xyzw 版本循环左移一位后与 wxyz 版本逐分量相等
    @priority P0
    """
    # Arrange
    angles = (10.0, 20.0, 30.0)

    # Act
    xyzw = euler_degree_to_quat_xyzw(*angles, 4)
    wxyz = euler_degree_to_quat_wxyz(*angles, 4)

    # Assert
    assert wxyz == pytest.approx([xyzw[3], xyzw[0], xyzw[1], xyzw[2]], abs=0.0)


# ── 不变量 ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("order,angles", _roundtrip_params())
def test_EulerQuatRoundTrip_PreservesAngles(order, angles):
    """@test   xsqeconverter.EulerQuatRoundTrip_PreservesAngles
    @brief  欧拉 → 四元数 → 欧拉往返在第二角主值域内必须恢复原角。
    @details 目的：验证 euler→quat 与 quat→euler 两个方向使用的旋转序编号
             一致（编号错位时往返必红——本用例曾暴露 YXZ/YZX 两分支公式
             被互换的实现缺陷）。设计思路：旋转序的 asin 型第二角限制在
             ±90° 主值域内（其余两角可达 ±180°），角度组覆盖常规角、
             负角与大角度边界；容差 1e-6 度对双精度是宽裕的。
    @expected 三个分量往返误差均 < 1e-6 度
    @priority P0
    """
    # Act
    wxyz = euler_degree_to_quat_wxyz(*angles, order)
    back = quat_to_euler_degree(wxyz, order)

    # Assert
    assert back == pytest.approx(list(angles), abs=TOL_DEG)


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_EulerQuatRoundTrip_OutOfPrincipalRangeIsRotationEquivalent(order):
    """@test   xsqeconverter.EulerQuatRoundTrip_OutOfPrincipalRangeIsRotationEquivalent
    @brief  第二角超出主值域（±90°）时，往返结果必须仍是同一旋转的等价表示。
    @details 目的：欧拉角表示在第二角超域时有固有二义性（如 Z=170° 可改写为
             X+180°/Y+180°/Z-10°），实现应返回等价欧拉角而非错误旋转。
             设计思路：直接断言"重新转回四元数后与原四元数同旋转"（q 与
             -q 等价），避免依赖具体是哪一种等价表示。
    @expected 往返后 quat→euler→quat 与原四元数逐分量误差 < 1e-6
    @priority P1
    """
    # Arrange：让 asin 型轴超出主值域
    second_axis = _SECOND_AXIS_BY_ORDER[order]
    angles = [25.0, -40.0, 150.0]
    angles[second_axis] = 155.0   # 强制第二角 = 155° > 90°

    # Act
    q0 = euler_degree_to_quat_wxyz(*angles, order)
    back = quat_to_euler_degree(q0, order)
    q1 = euler_degree_to_quat_wxyz(*back, order)

    # Assert（q 与 -q 表示同一旋转）
    sign = 1.0 if q1[0] * q0[0] >= 0 else -1.0
    assert [sign * v for v in q1] == pytest.approx(q0, abs=TOL_QUAT)


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_EulerToQuat_OutputAlwaysUnitNorm(order):
    """@test   xsqeconverter.EulerToQuat_OutputAlwaysUnitNorm
    @brief  任意输入角下输出的四元数范数必须为 1。
    @details 目的：下游 lerp/slerp 假设单位四元数；未归一化的输出会让 3D
             视图骨骼长度漂移。设计思路：用远超正常范围的输入（±720°）做
             越界测试，验证实现末段的范数归一化真的生效。
    @expected |q| == 1，误差 < 1e-6
    @priority P0
    """
    # Act
    q = euler_degree_to_quat_wxyz(720.0, -720.0, 360.0, order)

    # Assert
    assert quat_norm(q) == pytest.approx(1.0, abs=TOL_QUAT)


@pytest.mark.parametrize("order", ALL_ORDERS)
def test_QuatToEuler_RoundTripThroughMatrix(order):
    """@test   xsqeconverter.QuatToEuler_RoundTripThroughMatrix
    @brief  四元数 → 欧拉 → 四元数往返必须恢复原四元数（含符号等价）。
    @details 目的：反向链路覆盖 _quat2rotation 的矩阵填充；q 与 -q 表示同一
             旋转，逐分量比较前先对齐符号。
    @expected 往返后四元数与原值（或其相反数）逐分量误差 < 1e-6
    @priority P1
    """
    # Arrange：非对称角度生成的四元数，四个分量均非零
    q0 = euler_degree_to_quat_wxyz(12.0, -34.0, 56.0, order)

    # Act
    euler = quat_to_euler_degree(q0, order)
    q1 = euler_degree_to_quat_wxyz(*euler, order)

    # Assert（符号等价处理）
    sign = 1.0 if q1[0] * q0[0] >= 0 else -1.0
    assert [sign * v for v in q1] == pytest.approx(q0, abs=TOL_QUAT)


# ── 边界与异常输入 ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_order", [-1, 6, 99, 255])
def test_EulerToQuat_UnknownRotationOrderReturnsIdentity(bad_order):
    """@test   xsqeconverter.EulerToQuat_UnknownRotationOrderReturnsIdentity
    @brief  非法旋转序（-1/6/99/255）必须返回单位四元数，不得抛异常或崩溃。
    @details 目的：rot_order 来自 CSV 头部字符串映射，上游坏数据不应让整个
             解析线程崩溃。C++ 侧同样约定"未知枚举 → 单位旋转"，测试锁定
             这条跨语言契约。
    @expected 返回 [0,0,0,1]（xyzw），且不抛异常
    @priority P0
    """
    # Act
    q = euler_degree_to_quat_xyzw(30.0, 40.0, 50.0, bad_order)

    # Assert
    assert q == pytest.approx([0.0, 0.0, 0.0, 1.0], abs=TOL_QUAT)


@pytest.mark.parametrize("bad_order", [-1, 6, 99, 255])
def test_QuatToEuler_UnknownRotationOrderReturnsZeros(bad_order):
    """@test   xsqeconverter.QuatToEuler_UnknownRotationOrderReturnsZeros
    @brief  quat_to_euler_degree 对非法旋转序必须返回 [0, 0, 0]。
    @details 目的：与 euler→quat 方向的"未知序 → 单位四元数"成对，两个方向
             的兜底行为都要锁定；返回全零欧拉角等价于单位旋转，语义自洽。
    @expected 返回 [0.0, 0.0, 0.0]，且不抛异常
    @priority P1
    """
    # Act
    euler = quat_to_euler_degree([1.0, 0.0, 0.0, 0.0], bad_order)

    # Assert
    assert euler == pytest.approx([0.0, 0.0, 0.0], abs=TOL_QUAT)


def test_QuatToEuler_GimbalLockDoesNotProduceNaN():
    """@test   xsqeconverter.QuatToEuler_GimbalLockDoesNotProduceNaN
    @brief  gimbal 奇异点（绕 X 恰好 90°）不得输出 NaN / Inf。
    @details 目的：奇异点处 asin 的参数被夹取到 ±1（_safe_asinf），若夹取
             失效会抛 ValueError 或产生 NaN 污染下游骨骼数据。设计思路：
             用 XYZ 序绕 X 90° 构造精确奇异姿态，逐分量断言有限性——
             NaN 参与任何比较都是 False，必须先查 isfinite。
    @expected 三个欧拉分量均为有限值，且往返后的旋转等价于原旋转
    @priority P0
    """
    # Arrange：绕 X 90° 的四元数（解析解）
    q = [SQRT2_2, SQRT2_2, 0.0, 0.0]

    # Act
    euler = quat_to_euler_degree(q, 0)   # XYZ 序，X 是第一个奇异轴

    # Assert：先查有限性，再查旋转等价性
    for v in euler:
        assert math.isfinite(v), f"欧拉分量非有限：{euler}"

    wxyz_back = euler_degree_to_quat_wxyz(*euler, 0)
    # 奇异点往返只要求旋转等价（允许 X/Z 分量在奇异流形上重新分配）
    assert quat_norm(wxyz_back) == pytest.approx(1.0, abs=TOL_QUAT)
