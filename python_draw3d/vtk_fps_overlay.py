"""
vtk_fps_overlay.py
VTK 渲染帧率叠加显示

统计 VTK 渲染循环的实际刷新帧率，并将结果显示为左下角的 2D 文字叠加层。

用法
----
    overlay = VtkFpsOverlay(renderer, font_file=None)

    # 每次调用 GetRenderWindow().Render() 之前调用：
    overlay.tick()

    # 由外部 1s 定时器调用（与其他 FpsCounter.snapshot() 同步即可）：
    overlay.snapshot()

    # 显示 / 隐藏
    overlay.set_visible(True)
    overlay.set_visible(False)
"""

import time
import vtk


class VtkFpsOverlay:
    """VTK 渲染帧率统计 + 左下角叠加文字。

    内置独立的整秒桶计数器，不依赖外部 FpsCounter，统计的是
    实际调用 GetRenderWindow().Render() 的频率。

    参数
    ----
    renderer  : vtkRenderer，文字 Actor 将添加到该渲染器
    font_file : TTF 字体文件绝对路径；为 None 时使用 VTK 内置字体
    visible   : 初始是否可见（默认 False）
    """

    def __init__(self, renderer: vtk.vtkRenderer,
                 font_file: str | None = None,
                 visible: bool = False) -> None:
        self._count = 0
        self._last_fps = 0
        self._bucket_start = time.monotonic()

        self._actor = vtk.vtkTextActor()
        self._actor.SetInput("-- fps")

        prop = self._actor.GetTextProperty()
        prop.SetFontSize(16)
        prop.SetColor(0.85, 0.85, 0.85)
        prop.BoldOff()
        prop.ItalicOff()
        prop.ShadowOff()

        if font_file:
            prop.SetFontFamily(vtk.VTK_FONT_FILE)
            prop.SetFontFile(font_file)

        self._actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
        self._actor.SetPosition(0.01, 0.01)
        prop.SetJustificationToLeft()

        self._actor.SetVisibility(visible)
        renderer.AddActor2D(self._actor)

    # ------------------------------------------------------------------
    # 统计接口
    # ------------------------------------------------------------------

    def tick(self) -> None:
        """每次实际渲染一帧时调用一次。"""
        self._count += 1

    def snapshot(self) -> None:
        """每秒调用一次：计算帧率、刷新文字、归零桶。
        由外部 1s 定时器驱动。
        """
        now = time.monotonic()
        elapsed = now - self._bucket_start
        if elapsed > 0:
            self._last_fps = round(self._count / elapsed)
        self._count = 0
        self._bucket_start = now

        if self._actor.GetVisibility():
            self._actor.SetInput(f"{self._last_fps} fps (render)")

    def fps(self) -> int:
        """返回最近一次 snapshot() 记录的渲染帧率。"""
        return self._last_fps

    # ------------------------------------------------------------------
    # 可见性控制
    # ------------------------------------------------------------------

    def set_visible(self, visible: bool) -> None:
        """显示或隐藏帧率叠加文字。"""
        self._actor.SetVisibility(visible)
        if visible:
            self._actor.SetInput(f"{self._last_fps} fps (render)")

    def is_visible(self) -> bool:
        return bool(self._actor.GetVisibility())
