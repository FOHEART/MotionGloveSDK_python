"""坐标轴 Actor 工具"""

import vtk


_AXES_LABEL_FONT_SIZE = 14


def build_axes_actor(length=4):
    """坐标轴辅助显示"""
    axes = vtk.vtkAxesActor()
    axes.SetTotalLength(length, length, length)
    axes.SetShaftTypeToCylinder()

    for caption in (
        axes.GetXAxisCaptionActor2D(),
        axes.GetYAxisCaptionActor2D(),
        axes.GetZAxisCaptionActor2D(),
    ):
        caption.GetTextActor().SetTextScaleModeToNone()   # 禁用自动缩放
        prop = caption.GetCaptionTextProperty()
        prop.SetFontSize(_AXES_LABEL_FONT_SIZE)
        prop.BoldOff()
        prop.ItalicOff()
        prop.ShadowOff()

    return axes


def add_axes_to_renderer(renderer, length=4):
    """创建坐标轴并添加到 renderer"""
    renderer.AddActor(build_axes_actor(length=length))
