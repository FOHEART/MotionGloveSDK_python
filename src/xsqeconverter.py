"""
@file   xsqeconverter.py
@brief  欧拉角（度）与四元数互转工具（xsQEConverter 的 Python 移植）。
@details
直接翻译自 Movella Technologies B.V. 的 xsqeconverter.cpp，与 C++ 实现
逐式对应，供 decode_glove_csv.py（EULER 帧转四元数）使用。

公共函数：
  - euler_degree_to_quat_xyzw(x, y, z, rot_order) -> [x, y, z, w]
  - euler_degree_to_quat_wxyz(x, y, z, rot_order) -> [w, x, y, z]
  - quat_to_euler_degree(quat_wxyz, order)        -> [x_deg, y_deg, z_deg]

旋转顺序 rot_order 取值（与 C++ unsigned int RotOrder 一致）：
    0 = XYZ,  1 = XZY,  2 = YXZ,  3 = YZX,  4 = ZXY,  5 = ZYX
非法 rot_order 返回单位四元数 / [0,0,0]，不抛异常。

测试：tests/unit/test_xsqeconverter.py（半角公式金标准 + 逐顺序往返不变量）。
"""

from __future__ import annotations
import math

_PI         = math.pi
_EPSILON    = 1e-7
_ASIN_CLAMP = 1.0


# ── internal helpers ────────────────────────────────────────────────────────

def _safe_asinf(v: float) -> float:
    """@brief 带钳位的 asin，避免浮点误差导致 |sin| 略大于 1 时抛 ValueError。

    @param v 待求角的正弦值，理论范围 [-1, 1]；允许因舍入略越界。
    @return  [-pi/2, pi/2] 内的弧度角；v 越界时按 ±1 钳位计算。
    """
    return math.asin(max(-_ASIN_CLAMP, min(_ASIN_CLAMP, v)))


def _rotation2quat(rotmat: list[float]) -> list[float]:
    """@brief 旋转矩阵 → 归一化四元数 [x, y, z, w]。

    按 |w|、|x|、|y|、|z| 最大分量分四支求解（数值稳定），对应
    xsQEConverter::rotation2quat()。

    @param rotmat 行优先 3x3 旋转矩阵，长度 9 的列表，元素为无量纲浮点数。
    @return 归一化四元数 [x, y, z, w]；矩阵退化时返回单位四元数 [0,0,0,1]。
    """
    q = [0.0, 0.0, 0.0, 1.0]  # x y z w

    T = 1.0 + rotmat[0] + rotmat[4] + rotmat[8]
    if T > 1e-8:
        S    = 0.5 / math.sqrt(T)
        q[3] = 0.25 / S
        q[0] = (rotmat[7] - rotmat[5]) * S
        q[1] = (rotmat[2] - rotmat[6]) * S
        q[2] = (rotmat[3] - rotmat[1]) * S
    elif rotmat[0] > rotmat[4] and rotmat[0] > rotmat[8]:
        S    = math.sqrt(1.0 + rotmat[0] - rotmat[4] - rotmat[8]) * 2.0
        q[3] = (rotmat[6] - rotmat[5]) / S
        q[0] = 0.25 * S
        q[1] = (rotmat[1] + rotmat[3]) / S
        q[2] = (rotmat[2] + rotmat[6]) / S
    elif rotmat[4] > rotmat[8]:
        S    = math.sqrt(1.0 + rotmat[4] - rotmat[0] - rotmat[8]) * 2.0
        q[3] = (rotmat[2] - rotmat[6]) / S
        q[0] = (rotmat[1] + rotmat[3]) / S
        q[1] = 0.25 * S
        q[2] = (rotmat[5] + rotmat[7]) / S
    else:
        S    = math.sqrt(1.0 + rotmat[8] - rotmat[0] - rotmat[4]) * 2.0
        q[3] = (rotmat[3] - rotmat[1]) / S
        q[0] = (rotmat[2] + rotmat[6]) / S
        q[1] = (rotmat[1] + rotmat[3]) / S
        q[2] = 0.25 * S

    T = math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
    if T <= 0.0:
        return [0.0, 0.0, 0.0, 1.0]
    return [q[i] / T for i in range(4)]


def _quat2rotation(quat_wxyz: list[float]) -> list[float]:
    """@brief 四元数 [w, x, y, z] → 旋转矩阵（行优先 9 元素）。

    对应 xsQEConverter::QuatToEuler_quat2rotation()。注意：输入为 wxyz，
    C++ 内部先重排为 xyzw 再计算，本实现行为与之一致。

    @param quat_wxyz 长度 4 的四元数列表，顺序 [w, x, y, z]（Shader 习惯序）。
    @return 长度 9 的行优先旋转矩阵列表，元素为无量纲浮点数。
    """
    # C++: _quat = [quat[1], quat[2], quat[3], quat[0]]  (wxyz → xyzw)
    qx = quat_wxyz[1]
    qy = quat_wxyz[2]
    qz = quat_wxyz[3]
    qw = quat_wxyz[0]

    p0 = qx * qx
    p1 = qy * qy
    p2 = qz * qz
    p3 = qw * qw
    p4 = p1 + p2
    denom = p0 + p3 + p4
    p5 = (2.0 / denom) if denom != 0.0 else 0.0

    rotmat = [0.0] * 9
    rotmat[0] = 1.0 - p5 * p4
    rotmat[4] = 1.0 - p5 * (p0 + p2)
    rotmat[8] = 1.0 - p5 * (p0 + p1)

    a0 = p5 * qx
    a1 = p5 * qy
    a4 = p5 * qz * qw
    a5 = a0 * qy
    rotmat[1] = a5 - a4
    rotmat[3] = a5 + a4

    a4 = a1 * qw
    a5 = a0 * qz
    rotmat[2] = a5 + a4
    rotmat[6] = a5 - a4

    a4 = a0 * qw
    a5 = a1 * qz
    rotmat[5] = a5 - a4
    rotmat[7] = a5 + a4

    return rotmat


# ── public API ───────────────────────────────────────────────────────────────

def euler_degree_to_quat_xyzw(
    x: float, y: float, z: float, rot_order: int
) -> list[float]:
    """@brief 欧拉角（度）→ 四元数 [x, y, z, w]。

    对应 xsQEConverter::EulerDegreeToQuat_xyzw()：按 rot_order 拼装旋转
    矩阵后调用 _rotation2quat() 归一化。

    @param x          绕 X 轴欧拉角，单位度，无范围限制（任意实数）。
    @param y          绕 Y 轴欧拉角，单位度，无范围限制。
    @param z          绕 Z 轴欧拉角，单位度，无范围限制。
    @param rot_order  旋转顺序编号：0=XYZ 1=XZY 2=YXZ 3=YZX 4=ZXY 5=ZYX；
                      非法值返回单位四元数。
    @return 归一化四元数列表 [x, y, z, w]（|q| == 1）。
    """
    XR = x / 180.0 * _PI
    YR = y / 180.0 * _PI
    ZR = z / 180.0 * _PI

    SX, CX = math.sin(XR), math.cos(XR)
    SY, CY = math.sin(YR), math.cos(YR)
    SZ, CZ = math.sin(ZR), math.cos(ZR)

    if rot_order == 0:    # XYZ
        m = [
            CY*CZ,              -CY*SZ,              SY,
            CZ*SX*SY + CX*SZ,   CX*CZ - SX*SY*SZ,  -CY*SX,
            SX*SZ - CX*CZ*SY,   CZ*SX + CX*SY*SZ,   CX*CY,
        ]
    elif rot_order == 1:  # XZY
        m = [
            CY*CZ,              -SZ,                  CZ*SY,
            SX*SY + CX*CY*SZ,   CX*CZ,               CX*SY*SZ - CY*SX,
            CY*SX*SZ - CX*SY,   CZ*SX,               CX*CY + SX*SY*SZ,
        ]
    elif rot_order == 2:  # YXZ
        m = [
            CY*CZ + SX*SY*SZ,   CZ*SX*SY - CY*SZ,   CX*SY,
            CX*SZ,               CX*CZ,              -SX,
            CY*SX*SZ - CZ*SY,   CY*CZ*SX + SY*SZ,   CX*CY,
        ]
    elif rot_order == 3:  # YZX
        m = [
            CY*CZ,               SX*SY - CX*CY*SZ,   CX*SY + CY*SX*SZ,
            SZ,                  CX*CZ,              -CZ*SX,
            -CZ*SY,              CY*SX + CX*SY*SZ,   CX*CY - SX*SY*SZ,
        ]
    elif rot_order == 4:  # ZXY
        m = [
            CY*CZ - SX*SY*SZ,  -CX*SZ,               CZ*SY + CY*SX*SZ,
            CZ*SX*SY + CY*SZ,   CX*CZ,               SY*SZ - CY*CZ*SX,
            -CX*SY,              SX,                  CX*CY,
        ]
    elif rot_order == 5:  # ZYX
        m = [
            CY*CZ,               CZ*SX*SY - CX*SZ,   CX*CZ*SY + SX*SZ,
            CY*SZ,               CX*CZ + SX*SY*SZ,   CX*SY*SZ - CZ*SX,
            -SY,                 CY*SX,               CX*CY,
        ]
    else:
        return [0.0, 0.0, 0.0, 1.0]

    return _rotation2quat(m)


def euler_degree_to_quat_wxyz(
    x: float, y: float, z: float, rot_order: int
) -> list[float]:
    """@brief 欧拉角（度）→ 四元数 [w, x, y, z]（Shader/引擎习惯序）。

    对应 xsQEConverter::EulerDegreeToQuat_wxyz()：调用
    euler_degree_to_quat_xyzw() 后把 [x,y,z,w] 重排为 [w,x,y,z]。

    @param x          绕 X 轴欧拉角，单位度，无范围限制。
    @param y          绕 Y 轴欧拉角，单位度，无范围限制。
    @param z          绕 Z 轴欧拉角，单位度，无范围限制。
    @param rot_order  旋转顺序编号：0=XYZ 1=XZY 2=YXZ 3=YZX 4=ZXY 5=ZYX；
                      非法值返回单位四元数。
    @return 归一化四元数列表 [w, x, y, z]。
    """
    xyzw = euler_degree_to_quat_xyzw(x, y, z, rot_order)
    return [xyzw[3], xyzw[0], xyzw[1], xyzw[2]]


def quat_to_euler_degree(
    quat_wxyz: list[float], order: int
) -> list[float]:
    """@brief 四元数 [w, x, y, z] → 欧拉角（度）。

    对应 xsQEConverter::QuatToEulerDegree()：先经 _quat2rotation() 转旋转
    矩阵，再按 order 用 atan2/asin 提取三个角。第二角为 asin 分量（主值
    范围 ±90°），其余两角为 atan2 分量（±180°）。注意本函数与
    euler_degree_to_quat_* 的往返仅在 asin 主值范围内可逆；万向锁附近
    可能出现 NaN（与 C++ 行为一致）。

    @param quat_wxyz 长度 4 的四元数列表，顺序 [w, x, y, z]。
    @param order     旋转顺序编号：0=XYZ 1=XZY 2=YXZ 3=YZX 4=ZXY 5=ZYX；
                     非法值返回 [0, 0, 0]。
    @return 欧拉角列表 [x_deg, y_deg, z_deg]，单位度。
    """
    rotmat = _quat2rotation(quat_wxyz)

    # C++ fills: mat_R[j][i] = rotmat[index++]  (i outer, j inner)
    # → mat_R[row][col] = rotmat[col*3 + row]
    def mat_R(row: int, col: int) -> float:
        v = rotmat[col * 3 + row]
        return 0.0 if abs(v) < _EPSILON else v

    if order == 0:
        ex = math.atan2(-mat_R(2, 1), mat_R(2, 2))
        ey = _safe_asinf(mat_R(2, 0))
        ez = math.atan2(-mat_R(1, 0), mat_R(0, 0))
    elif order == 1:
        ex = math.atan2(mat_R(1, 2), mat_R(1, 1))
        ey = math.atan2(mat_R(2, 0), mat_R(0, 0))
        ez = _safe_asinf(-mat_R(1, 0))
    elif order == 2:  # YXZ：第二角 X 由 asin(-m12) 给出，Y/Z 用 atan2
        ex = _safe_asinf(-mat_R(2, 1))
        ey = math.atan2(mat_R(2, 0), mat_R(2, 2))
        ez = math.atan2(mat_R(0, 1), mat_R(1, 1))
    elif order == 3:  # YZX：第二角 Z 由 asin(m10) 给出，X/Y 用 atan2
        ex = math.atan2(-mat_R(2, 1), mat_R(1, 1))
        ey = math.atan2(-mat_R(0, 2), mat_R(0, 0))
        ez = _safe_asinf(mat_R(0, 1))
    elif order == 4:
        ex = _safe_asinf(mat_R(1, 2))
        ey = math.atan2(-mat_R(0, 2), mat_R(2, 2))
        ez = math.atan2(-mat_R(1, 0), mat_R(1, 1))
    elif order == 5:
        ex = math.atan2(mat_R(1, 2), mat_R(2, 2))
        ey = _safe_asinf(-mat_R(0, 2))
        ez = math.atan2(mat_R(0, 1), mat_R(0, 0))
    else:
        return [0.0, 0.0, 0.0]

    return [180.0 * ex / _PI, 180.0 * ey / _PI, 180.0 * ez / _PI]


# ── quick smoke test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("ZXY (order=4) — MotionGlove default:")
    for euler_in in [(0, 0, 0), (4.847, 0, 0), (10, 20, 30), (-45, 0, 90)]:
        wxyz = euler_degree_to_quat_wxyz(*euler_in, 4)
        back = quat_to_euler_degree(wxyz, 4)
        err  = max(abs(back[i] - euler_in[i]) for i in range(3))
        print(
            f"  in={euler_in}  wxyz={[round(v,5) for v in wxyz]}"
            f"  back=({back[0]:.3f},{back[1]:.3f},{back[2]:.3f})  err={err:.2e}"
        )
