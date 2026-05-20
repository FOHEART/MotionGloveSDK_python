"""Vive Tracker attach-axis helper."""

import math

import vtk

from vtk_axes import build_local_axes_actor


DEFAULT_ATTACH_AXIS_OFFSET_XYZ = (0.0, 0.05, 0.03)
DEFAULT_ATTACH_AXIS_LENGTH_MM = 20.0
DEFAULT_ATTACH_AXIS_SHAFT_RADIUS_MM = 1.5

# 左手附加点配置
DEFAULT_LEFT_ATTACH_AXIS_OFFSET_XYZ = (0.0, 0.05, 0.05)
DEFAULT_LEFT_ATTACH_AXIS_ROTATION_XYZ_DEGREES = (180.0, 0.0, 270.0)

# 右手附加点配置
DEFAULT_RIGHT_ATTACH_AXIS_OFFSET_XYZ = (0.0, 0.05, 0.05)
DEFAULT_RIGHT_ATTACH_AXIS_ROTATION_XYZ_DEGREES = (180.0, 0.0, 90.0)


def build_vive_tracker_attach_axis_actor(
    length_mm: float = DEFAULT_ATTACH_AXIS_LENGTH_MM,
    shaft_radius_mm: float = DEFAULT_ATTACH_AXIS_SHAFT_RADIUS_MM,
):
    """Build the local attach-axis actor assembly."""
    return build_local_axes_actor(length_mm=length_mm, shaft_radius_mm=shaft_radius_mm)


def normalize_quaternion_wxyz(
    quat_wxyz: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Return a normalized quaternion in wxyz order."""
    w, x, y, z = quat_wxyz
    norm = (w * w + x * x + y * y + z * z) ** 0.5
    if norm <= 1e-8:
        return (1.0, 0.0, 0.0, 0.0)
    return (w / norm, x / norm, y / norm, z / norm)


def multiply_quaternion_wxyz(
    lhs_wxyz: tuple[float, float, float, float],
    rhs_wxyz: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Multiply two quaternions in wxyz order."""
    lw, lx, ly, lz = lhs_wxyz
    rw, rx, ry, rz = rhs_wxyz
    return (
        lw * rw - lx * rx - ly * ry - lz * rz,
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
    )


def quaternion_from_axis_angle_wxyz(
    axis_xyz: tuple[float, float, float],
    angle_degrees: float,
) -> tuple[float, float, float, float]:
    """Build a quaternion from an axis-angle pair in wxyz order."""
    ax, ay, az = axis_xyz
    axis_norm = (ax * ax + ay * ay + az * az) ** 0.5
    if axis_norm <= 1e-8:
        return (1.0, 0.0, 0.0, 0.0)

    half_angle_radians = math.radians(angle_degrees) * 0.5
    sin_half_angle = math.sin(half_angle_radians)
    return normalize_quaternion_wxyz(
        (
            math.cos(half_angle_radians),
            ax / axis_norm * sin_half_angle,
            ay / axis_norm * sin_half_angle,
            az / axis_norm * sin_half_angle,
        )
    )


def quaternion_from_euler_xyz_degrees_wxyz(
    x_degrees: float,
    y_degrees: float,
    z_degrees: float,
) -> tuple[float, float, float, float]:
    """Build a quaternion from fixed XYZ Euler degrees in wxyz order."""
    quat_x = quaternion_from_axis_angle_wxyz((1.0, 0.0, 0.0), x_degrees)
    quat_y = quaternion_from_axis_angle_wxyz((0.0, 1.0, 0.0), y_degrees)
    quat_z = quaternion_from_axis_angle_wxyz((0.0, 0.0, 1.0), z_degrees)
    return normalize_quaternion_wxyz(
        multiply_quaternion_wxyz(
            multiply_quaternion_wxyz(quat_z, quat_y),
            quat_x,
        )
    )


def invert_quaternion_wxyz(
    quat_wxyz: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    """Return the inverse of a unit quaternion in wxyz order."""
    qw, qx, qy, qz = normalize_quaternion_wxyz(quat_wxyz)
    return (qw, -qx, -qy, -qz)


def rotate_vector_by_quaternion_wxyz(
    vector_xyz: tuple[float, float, float],
    quat_wxyz: tuple[float, float, float, float],
) -> tuple[float, float, float]:
    """Rotate a vector by a quaternion in wxyz order."""
    normalized_quat = normalize_quaternion_wxyz(quat_wxyz)
    vector_quat = (0.0, vector_xyz[0], vector_xyz[1], vector_xyz[2])
    rotated_vector_quat = multiply_quaternion_wxyz(
        multiply_quaternion_wxyz(normalized_quat, vector_quat),
        invert_quaternion_wxyz(normalized_quat),
    )
    return (
        rotated_vector_quat[1],
        rotated_vector_quat[2],
        rotated_vector_quat[3],
    )


def compose_vive_tracker_attach_axis_pose(
    tracker_position_xyz: tuple[float, float, float],
    tracker_quat_wxyz: tuple[float, float, float, float],
    local_offset_xyz: tuple[float, float, float] = DEFAULT_ATTACH_AXIS_OFFSET_XYZ,
    local_rotation_quat_wxyz: tuple[float, float, float, float] | None = None,
) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
    """Compose the attach-axis world pose from tracker world pose and local offset."""
    tracker_orientation_wxyz = normalize_quaternion_wxyz(tracker_quat_wxyz)
    final_orientation_wxyz = tracker_orientation_wxyz
    if local_rotation_quat_wxyz is not None:
        final_orientation_wxyz = normalize_quaternion_wxyz(
            multiply_quaternion_wxyz(tracker_orientation_wxyz, local_rotation_quat_wxyz)
        )

    # The attach point stays on the tracker-defined offset location; the optional
    # local rotation changes only the attach-axis' own orientation.
    rotated_offset_xyz = rotate_vector_by_quaternion_wxyz(local_offset_xyz, tracker_orientation_wxyz)
    attach_position_xyz = (
        tracker_position_xyz[0] + rotated_offset_xyz[0],
        tracker_position_xyz[1] + rotated_offset_xyz[1],
        tracker_position_xyz[2] + rotated_offset_xyz[2],
    )
    return attach_position_xyz, final_orientation_wxyz


def apply_pose_to_prop_assembly(
    actor_assembly,
    position_xyz: tuple[float, float, float],
    quat_wxyz: tuple[float, float, float, float],
    matrix: vtk.vtkMatrix4x4 | None = None,
    transform: vtk.vtkTransform | None = None,
) -> tuple[vtk.vtkMatrix4x4, vtk.vtkTransform]:
    """Apply a pose to every part in a vtkPropAssembly."""
    qx, qy, qz, qw = quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]
    quat_norm = (qx * qx + qy * qy + qz * qz + qw * qw) ** 0.5
    if quat_norm > 1e-6:
        qx /= quat_norm
        qy /= quat_norm
        qz /= quat_norm
        qw /= quat_norm
    else:
        qx, qy, qz, qw = 0.0, 0.0, 0.0, 1.0

    r11 = 1 - 2 * (qy * qy + qz * qz)
    r12 = 2 * (qx * qy - qz * qw)
    r13 = 2 * (qx * qz + qy * qw)

    r21 = 2 * (qx * qy + qz * qw)
    r22 = 1 - 2 * (qx * qx + qz * qz)
    r23 = 2 * (qy * qz - qx * qw)

    r31 = 2 * (qx * qz - qy * qw)
    r32 = 2 * (qy * qz + qx * qw)
    r33 = 1 - 2 * (qx * qx + qy * qy)

    matrix = matrix or vtk.vtkMatrix4x4()
    transform = transform or vtk.vtkTransform()

    matrix.SetElement(0, 0, r11)
    matrix.SetElement(0, 1, r12)
    matrix.SetElement(0, 2, r13)
    matrix.SetElement(0, 3, position_xyz[0])

    matrix.SetElement(1, 0, r21)
    matrix.SetElement(1, 1, r22)
    matrix.SetElement(1, 2, r23)
    matrix.SetElement(1, 3, position_xyz[1])

    matrix.SetElement(2, 0, r31)
    matrix.SetElement(2, 1, r32)
    matrix.SetElement(2, 2, r33)
    matrix.SetElement(2, 3, position_xyz[2])

    matrix.SetElement(3, 0, 0.0)
    matrix.SetElement(3, 1, 0.0)
    matrix.SetElement(3, 2, 0.0)
    matrix.SetElement(3, 3, 1.0)

    transform.SetMatrix(matrix)

    parts = actor_assembly.GetParts()
    for index in range(parts.GetNumberOfItems()):
        part = parts.GetItemAsObject(index)
        if part is not None:
            part.SetUserTransform(transform)
            part.Modified()

    actor_assembly.Modified()
    return matrix, transform