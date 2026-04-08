"""
bone_link_actor.py
父子骨骼关节之间的连线可视化单元。

接口
----
BoneLinkActor(renderer, color, line_width)
    构造后自动将 Actor 加入 renderer，初始隐藏。

    .update(p1, p2)
        更新连线两端点位置并显示。

    .hide()
        隐藏连线。

    .set_color(r, g, b)
        修改连线颜色。

    .set_line_width(width)
        修改连线粗细。
"""

import vtk


class BoneLinkActor:
    """单条父子骨骼连线的可视化单元。"""

    def __init__(self, renderer,
                 color=(0.7, 0.7, 0.7),
                 line_width: float = 2.0):
        self._pts = vtk.vtkPoints()
        self._pts.InsertNextPoint(0.0, 0.0, 0.0)
        self._pts.InsertNextPoint(0.0, 0.0, 0.0)

        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, 0)
        line.GetPointIds().SetId(1, 1)

        cells = vtk.vtkCellArray()
        cells.InsertNextCell(line)

        self._poly = vtk.vtkPolyData()
        self._poly.SetPoints(self._pts)
        self._poly.SetLines(cells)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(self._poly)

        self._actor = vtk.vtkActor()
        self._actor.SetMapper(mapper)
        self._actor.GetProperty().SetColor(*color)
        self._actor.GetProperty().SetLineWidth(line_width)
        self._actor.VisibilityOff()

        renderer.AddActor(self._actor)

    # ── 公开接口 ──────────────────────────────────

    def update(self, p1, p2):
        """更新连线端点并显示。p1/p2 为 (x, y, z) 序列。"""
        self._pts.SetPoint(0, p1[0], p1[1], p1[2])
        self._pts.SetPoint(1, p2[0], p2[1], p2[2])
        self._pts.Modified()
        self._poly.Modified()
        self._actor.VisibilityOn()

    def hide(self):
        """隐藏连线。"""
        self._actor.VisibilityOff()

    def set_color(self, r, g, b):
        """修改连线颜色。"""
        self._actor.GetProperty().SetColor(r, g, b)

    def set_line_width(self, width: float):
        """修改连线粗细。"""
        self._actor.GetProperty().SetLineWidth(width)
