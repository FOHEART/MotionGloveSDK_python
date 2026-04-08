"""地平面网格 Actor"""

import vtk


def build_ground_plane_actor(extent: float = 0.30, spacing: float = 0.05) -> vtk.vtkActor:
    """
    构建 X–Z 平面（Y=0）上的网格线 Actor。

    参数：
      extent  : 网格从原点向两侧延伸的距离（米），默认 0.30 m（±30 cm）
      spacing : 网格间距（米），默认 0.05 m（5 cm）

    返回：
      vtkActor，颜色灰色 (0.4, 0.4, 0.4)，默认可见。
    """
    points = vtk.vtkPoints()
    lines = vtk.vtkCellArray()

    # 在 -extent 到 +extent 之间，每隔 spacing 生成一条线
    # 先生成平行于 X 轴的线（沿 Z 方向扫描）
    # 再生成平行于 Z 轴的线（沿 X 方向扫描）

    import math
    n = int(round(extent / spacing))   # 原点到边界的格数

    def _add_line(p0, p1):
        id0 = points.InsertNextPoint(*p0)
        id1 = points.InsertNextPoint(*p1)
        lines.InsertNextCell(2)
        lines.InsertCellPoint(id0)
        lines.InsertCellPoint(id1)

    for i in range(-n, n + 1):
        z = i * spacing
        _add_line((-extent, 0.0, z), (extent, 0.0, z))   # 平行于 X 轴

    for i in range(-n, n + 1):
        x = i * spacing
        _add_line((x, 0.0, -extent), (x, 0.0, extent))   # 平行于 Z 轴

    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetLines(lines)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(poly)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(0.4, 0.4, 0.4)
    actor.GetProperty().SetLineWidth(1.0)

    return actor
