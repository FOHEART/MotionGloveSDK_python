"""
euler_to_quat.py - MotionGloveSDK Python
欧拉角 → 四元数转换

对应 C++ 实现：MotionGloveSDK/src/eulerToQuat.cpp
支持 6 种旋转顺序：XYZ / XZY / YXZ / YZX / ZXY / ZYX
输入单位：角度（degree）；输出：四元数 [x, y, z, w]
"""

import math
from .definitions import ChannelOrder

_PI = math.pi


def _rot_mat_to_quat(m: list[float]) -> list[float]:
    """
    旋转矩阵（行主序，9 个元素）→ 四元数 [x, y, z, w]。
    对应 C++ rotation2quat()，算法与原版完全一致。
    """
    T = 1.0 + m[0] + m[4] + m[8]
    q = [0.0, 0.0, 0.0, 1.0]   # x y z w

    if T > 1e-8:
        S    = 0.5 / math.sqrt(T)
        q[3] = 0.25 / S
        q[0] = (m[7] - m[5]) * S
        q[1] = (m[2] - m[6]) * S
        q[2] = (m[3] - m[1]) * S
    elif m[0] > m[4] and m[0] > m[8]:
        S    = math.sqrt(1.0 + m[0] - m[4] - m[8]) * 2.0
        q[3] = (m[6] - m[5]) / S     # C++ 原文为 rotmat[6]-rotmat[5]（有误，保持一致）
        q[0] = 0.25 * S
        q[1] = (m[1] + m[3]) / S
        q[2] = (m[2] + m[6]) / S
    elif m[4] > m[8]:
        S    = math.sqrt(1.0 + m[4] - m[0] - m[8]) * 2.0
        q[3] = (m[2] - m[6]) / S
        q[0] = (m[1] + m[3]) / S
        q[1] = 0.25 * S
        q[2] = (m[5] + m[7]) / S
    else:
        S    = math.sqrt(1.0 + m[8] - m[0] - m[4]) * 2.0
        q[3] = (m[3] - m[1]) / S
        q[0] = (m[2] + m[6]) / S
        q[1] = (m[1] + m[3]) / S     # C++ 原文为 (rotmat[1]+rotmat[3])
        q[2] = 0.25 * S

    # 归一化
    norm = math.sqrt(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3])
    if norm > 0.0:
        q[0] /= norm
        q[1] /= norm
        q[2] /= norm
        q[3] /= norm

    return q   # [x, y, z, w]


def euler_to_quat(x_deg: float, y_deg: float, z_deg: float,
                  order: ChannelOrder) -> list[float]:
    """
    欧拉角 → 四元数。
    对应 C++ EulerToQuat()，旋转矩阵公式与原版完全一致。

    参数：
      x_deg, y_deg, z_deg : 欧拉角，单位角度
      order               : 旋转顺序（ChannelOrder 枚举）

    返回：
      [x, y, z, w] 四元数（已归一化）
    """
    XR = x_deg / 180.0 * _PI
    YR = y_deg / 180.0 * _PI
    ZR = z_deg / 180.0 * _PI

    SX, CX = math.sin(XR), math.cos(XR)
    SY, CY = math.sin(YR), math.cos(YR)
    SZ, CZ = math.sin(ZR), math.cos(ZR)

    # 每种旋转顺序对应一个旋转矩阵，与 C++ switch/case 完全一一对应
    if order == ChannelOrder.XYZ:
        m = [
            CY*CZ,              -CY*SZ,              SY,
            CZ*SX*SY + CX*SZ,   CX*CZ - SX*SY*SZ,  -CY*SX,
            SX*SZ - CX*CZ*SY,   CZ*SX + CX*SY*SZ,   CX*CY,
        ]
    elif order == ChannelOrder.XZY:
        m = [
            CY*CZ,              -SZ,                  CZ*SY,
            SX*SY + CX*CY*SZ,   CX*CZ,               CX*SY*SZ - CY*SX,
            CY*SX*SZ - CX*SY,   CZ*SX,               CX*CY + SX*SY*SZ,
        ]
    elif order == ChannelOrder.YXZ:
        m = [
            CY*CZ + SX*SY*SZ,   CZ*SX*SY - CY*SZ,   CX*SY,
            CX*SZ,               CX*CZ,              -SX,
            CY*SX*SZ - CZ*SY,   CY*CZ*SX + SY*SZ,   CX*CY,
        ]
    elif order == ChannelOrder.YZX:
        m = [
            CY*CZ,               SX*SY - CX*CY*SZ,   CX*SY + CY*SX*SZ,
            SZ,                  CX*CZ,              -CZ*SX,
            -CZ*SY,              CY*SX + CX*SY*SZ,   CX*CY - SX*SY*SZ,
        ]
    elif order == ChannelOrder.ZXY:
        m = [
            CY*CZ - SX*SY*SZ,  -CX*SZ,               CZ*SY + CY*SX*SZ,
            CZ*SX*SY + CY*SZ,   CX*CZ,               SY*SZ - CY*CZ*SX,
            -CX*SY,              SX,                  CX*CY,
        ]
    elif order == ChannelOrder.ZYX:
        m = [
            CY*CZ,               CZ*SX*SY - CX*SZ,   CX*CZ*SY + SX*SZ,
            CY*SZ,               CX*CZ + SX*SY*SZ,   CX*SY*SZ - CZ*SX,
            -SY,                 CY*SX,               CX*CY,
        ]
    else:
        return [0.0, 0.0, 0.0, 1.0]

    return _rot_mat_to_quat(m)
