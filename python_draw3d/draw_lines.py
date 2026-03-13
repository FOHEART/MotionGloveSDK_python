"""连线绘制工具：球体/连线 Actor 创建及随机添加连线回调"""

import random
import vtk


_SPHERE_RADIUS = 0.08
_LINE_WIDTH = 3.0

LINE_COLORS = [
    (0.3, 0.8, 1.0),   # 青蓝
    (0.3, 1.0, 0.5),   # 绿
    (1.0, 0.8, 0.2),   # 黄
    (0.8, 0.3, 1.0),   # 紫
    (1.0, 0.5, 0.2),   # 橙
    (0.2, 0.9, 0.9),   # 青
    (1.0, 0.4, 0.6),   # 粉
]


def make_sphere_actor(center, radius, color=(1.0, 0.0, 0.0)):
    """创建一个球体Actor"""
    sphere = vtk.vtkSphereSource()
    sphere.SetCenter(*center)
    sphere.SetRadius(radius)
    sphere.SetPhiResolution(24)
    sphere.SetThetaResolution(24)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(sphere.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    return actor


def make_line_actor(p1, p2, color=(0.2, 0.6, 1.0)):
    """创建一条连线Actor"""
    points = vtk.vtkPoints()
    points.InsertNextPoint(*p1)
    points.InsertNextPoint(*p2)

    line = vtk.vtkLine()
    line.GetPointIds().SetId(0, 0)
    line.GetPointIds().SetId(1, 1)

    cells = vtk.vtkCellArray()
    cells.InsertNextCell(line)

    polydata = vtk.vtkPolyData()
    polydata.SetPoints(points)
    polydata.SetLines(cells)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetLineWidth(_LINE_WIDTH)
    return actor


def rand_coord(random_range=(-3.0, 3.0)):
    lo, hi = random_range
    return round(random.uniform(lo, hi), 2)


class AddLineCallback:
    """鼠标左键点击"添加连线"按钮时的回调"""

    def __init__(self, renderer, render_window, info_actor, btn_bounds,
                 point_groups, random_range):
        """
        btn_bounds: (x_min, x_max, y_min, y_max) 归一化显示坐标
        """
        self.renderer      = renderer
        self.render_window = render_window
        self.info_actor    = info_actor
        self.btn_bounds    = btn_bounds
        self.point_groups  = point_groups
        self.random_range  = random_range
        self.count         = len(point_groups)

    def __call__(self, obj, event):
        if event != "LeftButtonPressEvent":
            return

        x, y = obj.GetEventPosition()
        w, h = self.render_window.GetSize()
        nx = x / w
        ny = y / h

        x0, x1, y0, y1 = self.btn_bounds
        if x0 <= nx <= x1 and y0 <= ny <= y1:
            p_start = (rand_coord(self.random_range),
                       rand_coord(self.random_range),
                       rand_coord(self.random_range))
            p_end   = (rand_coord(self.random_range),
                       rand_coord(self.random_range),
                       rand_coord(self.random_range))
            self.point_groups.append((p_start, p_end))
            self.count = len(self.point_groups)

            color = LINE_COLORS[(self.count - 1) % len(LINE_COLORS)]

            self.renderer.AddActor(make_line_actor(p_start, p_end, color=color))
            self.renderer.AddActor(make_sphere_actor(p_start, _SPHERE_RADIUS))
            self.renderer.AddActor(make_sphere_actor(p_end,   _SPHERE_RADIUS))

            self.info_actor.SetInput("连线条数: {}".format(self.count))
            print("  [+] 新增连线 #{}: {} → {}".format(self.count, p_start, p_end))
            self.render_window.Render()
        else:
            self.renderer.GetRenderWindow().GetInteractor().GetInteractorStyle().OnLeftButtonDown()


def add_lines_to_renderer(renderer, point_groups):
    """将所有点组的连线和端点球体添加到 renderer"""
    for i, (p_start, p_end) in enumerate(point_groups):
        color = LINE_COLORS[i % len(LINE_COLORS)]
        renderer.AddActor(make_line_actor(p_start, p_end, color=color))
        renderer.AddActor(make_sphere_actor(p_start, _SPHERE_RADIUS))
        renderer.AddActor(make_sphere_actor(p_end,   _SPHERE_RADIUS))
