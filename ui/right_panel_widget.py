"""right_panel_widget.py
右侧多功能面板：QTabWidget 容器，包含绘图配置、骨骼查看、ViveTracker 配置三个 Tab 页。

布局由 right_panel.ui 定义，可用 Qt Designer 添加/修改 Tab 页。
Python 代码只负责向 Tab 页中嵌入子控件以及信号连接。

公开接口
--------
RightPanelWidget(parent)
    .draw_config    -> DrawConfigWidget      — 绘图配置子控件（转发 current_config / load_from_config）
    .bone_viewer    -> BoneViewerWidget      — 骨骼查看子控件（显示骨骼树和欧拉角）
    .vive_tracker   -> ViveTrackerWidget     — Vive Tracker 配置显示子控件
    .tab_widget     -> QTabWidget            — 直接访问底层 QTabWidget（用于动态增减 Tab）
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice

from draw_config_widget import DrawConfigWidget
from bone_viewer_widget import BoneViewerWidget
from vive_tracker_widget import ViveTrackerWidget


def _ui_path() -> Path:
    """返回 right_panel.ui 的绝对路径，兼容源码运行和 PyInstaller 打包。"""
    candidates: list[Path] = []

    candidates.append(Path(__file__).parent / "right_panel.ui")
    candidates.append(Path(__file__).parent.parent / "ui" / "right_panel.ui")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "ui" / "right_panel.ui")
        candidates.append(Path(meipass) / "_internal" / "ui" / "right_panel.ui")

    try:
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "ui" / "right_panel.ui")
        candidates.append(exe_dir / "_internal" / "ui" / "right_panel.ui")
    except Exception:
        exe_dir = None

    candidates.append(Path.cwd() / "ui" / "right_panel.ui")
    candidates.append(Path.cwd() / "_internal" / "ui" / "right_panel.ui")

    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue

    search_roots = [Path(__file__).parent, Path(__file__).parent.parent]
    if exe_dir is not None:
        search_roots.append(exe_dir)
    search_roots.append(Path.cwd())
    for root in search_roots:
        try:
            for p in root.rglob("right_panel.ui"):
                return p
        except Exception:
            continue

    return Path(__file__).parent / "right_panel.ui"


class RightPanelWidget(QWidget):
    """右侧多功能面板，包含 QTabWidget，第一个 Tab 为绘图配置。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        ui_file = QFile(str(_ui_path()))
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_ui_path()}")
        self._ui = loader.load(ui_file)
        ui_file.close()
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_ui_path()}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._ui)

        # 获取 QTabWidget
        self._tab_widget: QTabWidget = self._ui.findChild(QTabWidget, "tab_widget")
        assert self._tab_widget is not None, "UI 控件未找到：tab_widget"

        # 获取第一个 Tab 页及其布局，嵌入 DrawConfigWidget
        tab0: QWidget = self._tab_widget.widget(0)
        assert tab0 is not None, "right_panel.ui 中第一个 Tab 页缺失"
        tab0_layout: QVBoxLayout = tab0.layout()
        assert tab0_layout is not None, "right_panel.ui 中第一个 Tab 页布局缺失"

        self._draw_config = DrawConfigWidget()
        tab0_layout.addWidget(self._draw_config)

        # 获取第二个 Tab 页及其布局，嵌入 BoneViewerWidget
        tab1: QWidget = self._tab_widget.widget(1)
        assert tab1 is not None, "right_panel.ui 中第二个 Tab 页缺失"
        tab1_layout: QVBoxLayout = tab1.layout()
        assert tab1_layout is not None, "right_panel.ui 中第二个 Tab 页布局缺失"

        self._bone_viewer = BoneViewerWidget()
        tab1_layout.addWidget(self._bone_viewer)

        # 获取第三个 Tab 页及其布局，嵌入 ViveTrackerWidget
        tab2: QWidget = self._tab_widget.widget(2)
        assert tab2 is not None, "right_panel.ui 中第三个 Tab 页缺失"
        tab2_layout: QVBoxLayout = tab2.layout()
        assert tab2_layout is not None, "right_panel.ui 中第三个 Tab 页布局缺失"

        self._vive_tracker = ViveTrackerWidget()
        tab2_layout.addWidget(self._vive_tracker)

        # 设置最小宽度，允许用户拖动调整
        self.setMinimumWidth(300)
        self.setMaximumWidth(400)

    # ── 公开属性 ──────────────────────────────────────

    @property
    def draw_config(self) -> DrawConfigWidget:
        """绘图配置子控件（转发 current_config / load_from_config）。"""
        return self._draw_config

    @property
    def bone_viewer(self) -> BoneViewerWidget:
        """骨骼查看子控件（显示骨骼树和欧拉角）。"""
        return self._bone_viewer

    @property
    def vive_tracker(self) -> ViveTrackerWidget:
        """Vive Tracker 配置显示子控件。"""
        return self._vive_tracker

    @property
    def tab_widget(self) -> QTabWidget:
        """底层 QTabWidget，可用于动态增减 Tab 页。"""
        return self._tab_widget
