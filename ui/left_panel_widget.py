"""左侧信息面板控制器

从 left_panel.ui 加载 Qt Designer 布局，暴露 lbl_ip / lbl_port 供外部更新。
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice


def _ui_path() -> Path:
    """返回 left_panel.ui 的绝对路径，兼容源码运行和 PyInstaller 打包。"""
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller 打包：.ui 文件在 _MEIPASS/ui/left_panel.ui
        return Path(sys._MEIPASS) / "ui" / "left_panel.ui"
    # 源码运行：与本文件同目录
    return Path(__file__).parent / "left_panel.ui"


class LeftPanelWidget(QWidget):
    """加载 left_panel.ui 并提供 lbl_ip / lbl_port 属性。"""

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

        # 将加载的 widget 嵌入 self
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ui)

        # 固定宽度与 .ui 中保持一致
        self.setFixedWidth(220)

        # 暴露动态标签引用
        self.lbl_ip: QLabel = self._ui.findChild(QLabel, "lbl_ip")
        self.lbl_port: QLabel = self._ui.findChild(QLabel, "lbl_port")
        self.lbl_actor_name: QLabel = self._ui.findChild(QLabel, "lbl_actor_name")
        self.lbl_frame_id: QLabel = self._ui.findChild(QLabel, "lbl_frame_id")
        self.lbl_total_frames: QLabel = self._ui.findChild(QLabel, "lbl_total_frames")
        self.lbl_fps: QLabel = self._ui.findChild(QLabel, "lbl_fps")
        self.lbl_error: QLabel = self._ui.findChild(QLabel, "lbl_error")
        self.btn_start: QPushButton = self._ui.findChild(QPushButton, "btn_start")
        self.btn_stop: QPushButton = self._ui.findChild(QPushButton, "btn_stop")

    def show_port_error(self, lines: list[str]) -> None:
        """显示端口占用错误信息（红色文字）。"""
        self.lbl_error.setText("\n".join(lines))
        self.lbl_error.setVisible(True)

    def clear_error(self) -> None:
        """隐藏错误标签。"""
        self.lbl_error.setText("")
        self.lbl_error.setVisible(False)

    def set_receiving(self, active: bool) -> None:
        """根据接收状态切换按钮使能。active=True：开始禁用、停止可用。"""
        self.btn_start.setEnabled(not active)
        self.btn_stop.setEnabled(active)
