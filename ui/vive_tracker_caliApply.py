"""vive_tracker_caliApply.py
应用定位页面。

功能：
- 提供一个独立 tab 页面，用于将 3D 视图中的整只左手骨架平移到左手 Vive Tracker 基准点
- 点击按钮后启用覆盖：计算 LeftHand 根节点到左手 Vive Tracker 的位置偏移，并应用到整只左手的绘制对象
- 支持对右手骨架执行相同的 Tracker 位置绑定操作
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from shiboken6 import isValid


def _find_cali_apply_ui_file() -> Path:
    """查找 vive_tracker_caliApply.ui 文件的路径。"""
    candidates = [
        Path(__file__).parent / "vive_tracker_caliApply.ui",
        Path(__file__).parent.parent / "ui" / "vive_tracker_caliApply.ui",
        Path.cwd() / "ui" / "vive_tracker_caliApply.ui",
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(2, Path(meipass) / "ui" / "vive_tracker_caliApply.ui")
        candidates.insert(3, Path(meipass) / "_internal" / "ui" / "vive_tracker_caliApply.ui")

    try:
        exe_dir = Path(sys.executable).parent
        candidates.insert(len(candidates) - 1, exe_dir / "ui" / "vive_tracker_caliApply.ui")
        candidates.insert(len(candidates) - 1, exe_dir / "_internal" / "ui" / "vive_tracker_caliApply.ui")
    except Exception:
        pass

    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue

    search_roots = [Path(__file__).parent, Path(__file__).parent.parent, Path.cwd()]
    if meipass:
        search_roots.insert(0, Path(meipass))

    for root in search_roots:
        try:
            for p in root.rglob("vive_tracker_caliApply.ui"):
                return p
        except Exception:
            continue

    return candidates[0]


class ViveTrackerCaliApplyWidget(QWidget):
    """应用定位页面。"""

    def __init__(self, parent=None, vive_tracker_widget=None):
        super().__init__(parent)
        self._vive_tracker_widget = vive_tracker_widget
        self._apply_button = None
        self._cancel_button = None
        self._apply_right_button = None
        self._cancel_right_button = None
        self._init_ui()

    def _init_ui(self):
        """从 UI 文件加载界面。"""
        loader = QUiLoader()
        ui_file = QFile(str(_find_cali_apply_ui_file()))

        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_find_cali_apply_ui_file()}")

        self._ui = loader.load(ui_file)
        ui_file.close()

        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_find_cali_apply_ui_file()}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ui)

        self._apply_button = self.findChild(QPushButton, "applyLocationButton")
        self._cancel_button = self.findChild(QPushButton, "cancelApplyLocationButton")
        self._apply_right_button = self.findChild(QPushButton, "applyRightLocationButton")
        self._cancel_right_button = self.findChild(QPushButton, "cancelApplyRightLocationButton")
        assert self._apply_button is not None, "UI 控件未找到：applyLocationButton"
        assert self._cancel_button is not None, "UI 控件未找到：cancelApplyLocationButton"
        assert self._apply_right_button is not None, "UI 控件未找到：applyRightLocationButton"
        assert self._cancel_right_button is not None, "UI 控件未找到：cancelApplyRightLocationButton"
        self._apply_button.clicked.connect(self._on_apply_clicked)
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        self._apply_right_button.clicked.connect(self._on_apply_right_clicked)
        self._cancel_right_button.clicked.connect(self._on_cancel_right_clicked)

    def _resolve_apply_button(self) -> QPushButton:
        """安全获取应用定位按钮。"""
        if self._apply_button is not None and isValid(self._apply_button):
            return self._apply_button

        self._apply_button = self.findChild(QPushButton, "applyLocationButton")
        if self._apply_button is None:
            raise RuntimeError("无法找到 applyLocationButton 控件")
        return self._apply_button

    def _resolve_cancel_button(self) -> QPushButton:
        """安全获取取消应用定位按钮。"""
        if self._cancel_button is not None and isValid(self._cancel_button):
            return self._cancel_button

        self._cancel_button = self.findChild(QPushButton, "cancelApplyLocationButton")
        if self._cancel_button is None:
            raise RuntimeError("无法找到 cancelApplyLocationButton 控件")
        return self._cancel_button

    def _on_apply_clicked(self):
        """启用左手骨架整体跟随左手 Vive Tracker。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法应用定位")
            return

        success = self._vive_tracker_widget.enable_left_hand_root_follow_tracker(True)
        if success:
            print("[CaliApply] 已启用：左手骨架将整体平移到左手 Vive Tracker 基准点")
        else:
            print("[CaliApply] 左手 Vive Tracker 当前无有效数据，未启用应用定位")

    def _on_cancel_clicked(self):
        """取消应用定位，恢复原始左手骨架位置。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法取消应用定位")
            return

        self._vive_tracker_widget.enable_left_hand_root_follow_tracker(False)
        print("[CaliApply] 已取消：左手骨架恢复使用原始位置")

    def _on_apply_right_clicked(self):
        """启用右手骨架整体跟随右手 Vive Tracker。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法应用右手定位")
            return

        success = self._vive_tracker_widget.enable_right_hand_root_follow_tracker(True)
        if success:
            print("[CaliApply] 已启用：右手骨架将整体平移到右手 Vive Tracker 基准点")
        else:
            print("[CaliApply] 右手 Vive Tracker 当前无有效数据，未启用右手应用定位")

    def _on_cancel_right_clicked(self):
        """取消右手应用定位，恢复原始右手骨架位置。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法取消右手应用定位")
            return

        self._vive_tracker_widget.enable_right_hand_root_follow_tracker(False)
        print("[CaliApply] 已取消：右手骨架恢复使用原始位置")


class CaliApplyTabManager:
    """应用定位 tab 管理器。"""

    def __init__(self, vive_tracker_widget):
        self._vive_tracker_widget = vive_tracker_widget
        self._cali_apply_widget = None
        self._cali_apply_tab_index = None

    def setup_cali_apply_tab(self, tab_widget):
        """设置应用定位 tab 并添加到 QTabWidget。"""
        self._cali_apply_widget = ViveTrackerCaliApplyWidget(
            vive_tracker_widget=self._vive_tracker_widget,
            parent=self._vive_tracker_widget,
        )
        self._cali_apply_tab_index = tab_widget.addTab(self._cali_apply_widget, "应用定位")
        tab_widget.setTabEnabled(self._cali_apply_tab_index, True)
        return self._cali_apply_widget

    def get_cali_apply_widget(self):
        return self._cali_apply_widget

    def get_cali_apply_tab_index(self):
        return self._cali_apply_tab_index