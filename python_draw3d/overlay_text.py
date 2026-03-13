"""
overlay_text.py
VTK 界面文字叠加工具

接口
----
add_overlay_text(renderer, text, font_file=None,
                 font_size=16, color=(0.9, 0.9, 0.9),
                 position=(0.01, 0.96), justification="left")
    在 renderer 中添加一个 2D 文本 Actor，返回该 Actor。
    position: 归一化坐标 (x, y)，(0,0) 为左下，(1,1) 为右上。
    font_file: TTF 字体文件绝对路径，为 None 时使用 VTK 内置字体。
"""

import vtk


def add_overlay_text(renderer, text,
                     font_file=None,
                     font_size=16,
                     color=(0.9, 0.9, 0.9),
                     position=(0.01, 0.96),
                     justification="left"):
    """
    在 renderer 中添加 2D 文字叠加层，返回 vtkTextActor。
    """
    actor = vtk.vtkTextActor()
    actor.SetInput(text)

    prop = actor.GetTextProperty()
    prop.SetFontSize(font_size)
    prop.SetColor(*color)
    prop.BoldOff()
    prop.ItalicOff()
    prop.ShadowOff()

    if font_file:
        prop.SetFontFamily(vtk.VTK_FONT_FILE)
        prop.SetFontFile(font_file)

    # 坐标系设置为归一化视口坐标
    actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    actor.SetPosition(*position)

    if justification == "center":
        prop.SetJustificationToCentered()
    elif justification == "right":
        prop.SetJustificationToRight()
    else:
        prop.SetJustificationToLeft()

    renderer.AddActor2D(actor)
    return actor
