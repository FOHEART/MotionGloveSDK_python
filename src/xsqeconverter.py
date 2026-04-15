"""
xsqeconverter.py
Python port of xsQEConverter (Movella Technologies B.V.)

Direct translation of xsqeconverter.cpp.

Public functions
----------------
euler_degree_to_quat_xyzw(x, y, z, rot_order) -> list[float]  # [x, y, z, w]
euler_degree_to_quat_wxyz(x, y, z, rot_order) -> list[float]  # [w, x, y, z]
quat_to_euler_degree(quat_wxyz, order)         -> list[float]  # [x_deg, y_deg, z_deg]

rot_order values (match C++ unsigned int RotOrder):
    0 = XYZ,  1 = XZY,  2 = YXZ,  3 = YZX,  4 = ZXY,  5 = ZYX
"""

from __future__ import annotations
import math

_PI         = math.pi
_EPSILON    = 1e-7
_ASIN_CLAMP = 1.0


# ── internal helpers ────────────────────────────────────────────────────────

def _safe_asinf(v: float) -> float:
    return math.asin(max(-_ASIN_CLAMP, min(_ASIN_CLAMP, v)))


def _rotation2quat(rotmat: list[float]) -> list[float]:
    """Rotation matrix (row-major, 9 elements) → quaternion [x, y, z, w].
    Corresponds to xsQEConverter::rotation2quat().
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
    """Quaternion [w,x,y,z] → rotation matrix (row-major, 9 elements).
    Corresponds to xsQEConverter::QuatToEuler_quat2rotation().
    Note: input is wxyz; C++ reorders to xyzw internally.
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
    """Euler angles (degrees) → quaternion [x, y, z, w].

    Parameters
    ----------
    x, y, z   : Euler angles in degrees
    rot_order : 0=XYZ  1=XZY  2=YXZ  3=YZX  4=ZXY  5=ZYX

    Returns
    -------
    [x, y, z, w] normalised quaternion
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
    """Euler angles (degrees) → quaternion [w, x, y, z].

    Corresponds to xsQEConverter::EulerDegreeToQuat_wxyz():
    calls EulerDegreeToQuat_xyzw then reorders [x,y,z,w] → [w,x,y,z].
    """
    xyzw = euler_degree_to_quat_xyzw(x, y, z, rot_order)
    return [xyzw[3], xyzw[0], xyzw[1], xyzw[2]]


def quat_to_euler_degree(
    quat_wxyz: list[float], order: int
) -> list[float]:
    """Quaternion [w, x, y, z] → Euler angles in degrees.

    Corresponds to xsQEConverter::QuatToEulerDegree().

    Parameters
    ----------
    quat_wxyz : [w, x, y, z]
    order     : 0=XYZ … 5=ZYX  (same numbering as EulerDegreeToQuat)

    Returns
    -------
    [x_deg, y_deg, z_deg]
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
    elif order == 2:
        ex = math.atan2(-mat_R(2, 1), mat_R(1, 1))
        ey = math.atan2(-mat_R(0, 2), mat_R(0, 0))
        ez = _safe_asinf(mat_R(0, 1))
    elif order == 3:
        ex = _safe_asinf(-mat_R(2, 1))
        ey = math.atan2(mat_R(2, 0), mat_R(2, 2))
        ez = math.atan2(mat_R(0, 1), mat_R(1, 1))
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
