"""
bone_joint_actor.py
每个骨骼关节的可视化单元：球体 + 三轴坐标线段

接口
----
BoneJointActor(renderer, radius, sphere_color)
    构造后自动将所有 Actor 加入 renderer，初始隐藏。

    .set_pose(position, quat_wxyz)
        设置位置和旋转四元数 (w,x,y,z)，显示球体和三轴。

    .set_position_only(position)
        仅设置位置，显示球体，隐藏三轴。

    .hide()
        隐藏球体和三轴。

    .set_axis_length(length)
        修改三轴线段长度（默认 = radius * 2）。

    .set_axis_line_width(width)
        修改三轴线宽（默认 1.5）。
"""

import vtk


# 三轴默认颜色：X=红，Y=绿，Z=蓝
_AXIS_COLORS = (
    (1.0, 0.2, 0.2),
    (0.2, 1.0, 0.2),
    (0.2, 0.4, 1.0),
)


def _make_sphere_actor(radius, color):
    sphere = vtk.vtkSphereSource()
    sphere.SetCenter(0.0, 0.0, 0.0)
    sphere.SetRadius(radius)
    sphere.SetPhiResolution(16)
    sphere.SetThetaResolution(16)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    return actor, sphere


def _make_line_actor(color, line_width):
    pts = vtk.vtkPoints()
    pts.InsertNextPoint(0.0, 0.0, 0.0)
    pts.InsertNextPoint(1.0, 0.0, 0.0)

    line = vtk.vtkLine()
    line.GetPointIds().SetId(0, 0)
    line.GetPointIds().SetId(1, 1)

    cells = vtk.vtkCellArray()
    cells.InsertNextCell(line)

    poly = vtk.vtkPolyData()
    poly.SetPoints(pts)
    poly.SetLines(cells)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetLineWidth(line_width)
    return actor, pts, poly


def _quat_rotate(v, qw, qx, qy, qz):
    """用单位四元数 (w,x,y,z) 旋转向量 v，返回旋转后的向量。"""
    vx, vy, vz = v
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx),
    )


def _set_line_pts(pts, poly, origin, direction, length):
    ox, oy, oz = origin
    dx, dy, dz = direction
    pts.SetPoint(0, ox, oy, oz)
    pts.SetPoint(1, ox + dx * length, oy + dy * length, oz + dz * length)
    pts.Modified()
    poly.Modified()


class BoneJointActor:
    """单个骨骼关节的球体 + 三轴坐标轴可视化单元。"""

    def __init__(self, renderer, radius=0.005, sphere_color=(1.0, 1.0, 1.0),
                 axis_line_width=1.5):
        self._radius     = radius
        self._axis_len   = radius * 2.0

        # 球体
        self._s_actor, self._sphere_src = _make_sphere_actor(radius, sphere_color)
        self._s_actor.VisibilityOff()
        renderer.AddActor(self._s_actor)

        # 三轴线段：[(actor, pts, poly), ...]
        self._axes = []
        for color in _AXIS_COLORS:
            a, pts, poly = _make_line_actor(color, axis_line_width)
            a.VisibilityOff()
            renderer.AddActor(a)
            self._axes.append((a, pts, poly))

    # ── 公开接口 ──────────────────────────────────

    def set_pose(self, position, quat_wxyz):
        """设置位置 + 四元数旋转，显示球体和三轴。"""
        ox, oy, oz = position
        qw, qx, qy, qz = quat_wxyz

        self._sphere_src.SetCenter(ox, oy, oz)
        self._sphere_src.Update()
        self._s_actor.VisibilityOn()

        dirs = (
            _quat_rotate((1.0, 0.0, 0.0), qw, qx, qy, qz),
            _quat_rotate((0.0, 1.0, 0.0), qw, qx, qy, qz),
            _quat_rotate((0.0, 0.0, 1.0), qw, qx, qy, qz),
        )
        for (a, pts, poly), d in zip(self._axes, dirs):
            _set_line_pts(pts, poly, (ox, oy, oz), d, self._axis_len)
            a.VisibilityOn()

    def set_position_only(self, position):
        """仅设置位置，显示球体，隐藏三轴。"""
        self._sphere_src.SetCenter(*position)
        self._sphere_src.Update()
        self._s_actor.VisibilityOn()
        for a, _, __ in self._axes:
            a.VisibilityOff()

    def hide(self):
        """隐藏球体和三轴。"""
        self._s_actor.VisibilityOff()
        for a, _, __ in self._axes:
            a.VisibilityOff()

    def set_axis_length(self, length):
        """设置三轴线段长度。"""
        self._axis_len = length

    def set_axis_line_width(self, width):
        """设置三轴线宽。"""
        for a, _, __ in self._axes:
            a.GetProperty().SetLineWidth(width)
