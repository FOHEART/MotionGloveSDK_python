"""长方体 Actor 工具：创建及四元数旋转接口"""

import math
import vtk


def build_box_actor(x_len=30.0/2, y_len=20.0/2, z_len=10.0/2, opacity=0.9):
    """创建彩色面长方体 Actor（居中于原点）"""
    box = vtk.vtkCubeSource()
    box.SetXLength(x_len)
    box.SetYLength(y_len)
    box.SetZLength(z_len)
    box.SetCenter(0.0, 0.0, 0.0)
    box.Update()

    box_pd = vtk.vtkPolyData()
    box_pd.DeepCopy(box.GetOutput())

    # 面颜色顺序：+X, -X, +Y, -Y, +Z, -Z
    scalars = vtk.vtkUnsignedCharArray()
    scalars.SetNumberOfComponents(3)
    scalars.SetName("FaceColor")
    face_colors = [
        (204, 30,  30),   # +X 红色（与 YOZ 面平行）
        (204, 30,  30),   # -X 红色（与 YOZ 面平行）
        (30,  180, 60),   # +Y 绿色（与 XOZ 面平行）
        (30,  180, 60),   # -Y 绿色（与 XOZ 面平行）
        (30,  80,  204),  # +Z 蓝色（与 XOY 面平行）
        (30,  80,  204),  # -Z 蓝色（与 XOY 面平行）
    ]
    for r, g, b in face_colors:
        scalars.InsertNextTuple3(r, g, b)
    box_pd.GetCellData().SetScalars(scalars)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(box_pd)
    mapper.SetColorModeToDirectScalars()
    mapper.ScalarVisibilityOn()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetOpacity(opacity)
    actor.GetProperty().SetEdgeVisibility(True)
    actor.GetProperty().SetEdgeColor(1.0, 1.0, 1.0)
    actor.GetProperty().SetLineWidth(1.5)
    return actor


def set_box_quaternion(actor, qx, qy, qz, qw):
    """
    将四元数 (qx, qy, qz, qw) 应用到 actor 的旋转。
    四元数须为单位四元数。
    """
    # 四元数 → 轴角
    # 先归一化，防止浮点误差
    n = math.sqrt(qx*qx + qy*qy + qz*qz + qw*qw)
    if n < 1e-10:
        return
    qx, qy, qz, qw = qx/n, qy/n, qz/n, qw/n

    # qw 限制在 [-1, 1] 防止 acos 越界
    qw = max(-1.0, min(1.0, qw))
    angle_rad = 2.0 * math.acos(qw)
    angle_deg = math.degrees(angle_rad)

    s = math.sqrt(1.0 - qw*qw)
    if s < 1e-6:
        ax, ay, az = 1.0, 0.0, 0.0
    else:
        ax, ay, az = qx/s, qy/s, qz/s

    actor.SetOrientation(0, 0, 0)          # 先清除旧旋转
    actor.RotateWXYZ(angle_deg, ax, ay, az)
