"""vive_tracker_caliApply.py
应用定位页面。

功能：
- 提供一个独立 tab 页面，用于将 3D 视图中的整只左手骨架平移到左手 Vive Tracker 基准点
- 点击按钮后启用覆盖：计算 LeftHand 根节点到左手 Vive Tracker 的位置偏移，并应用到整只左手的绘制对象
- 支持对右手骨架执行相同的 Tracker 位置绑定操作
"""

import sys
from pathlib import Path
from typing import cast

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QSlider
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
        self._left_attach_axis_button = None
        self._left_attach_axis_x_edit = None
        self._left_attach_axis_y_edit = None
        self._left_attach_axis_z_edit = None
        self._left_attach_axis_set_button = None
        self._left_attach_axis_x_rotation_slider = None
        self._left_attach_axis_y_rotation_slider = None
        self._left_attach_axis_z_rotation_slider = None
        self._left_attach_axis_x_rotation_value_label = None
        self._left_attach_axis_y_rotation_value_label = None
        self._left_attach_axis_z_rotation_value_label = None
        self._right_attach_axis_button = None
        self._right_attach_axis_x_edit = None
        self._right_attach_axis_y_edit = None
        self._right_attach_axis_z_edit = None
        self._right_attach_axis_set_button = None
        self._right_attach_axis_x_rotation_slider = None
        self._right_attach_axis_y_rotation_slider = None
        self._right_attach_axis_z_rotation_slider = None
        self._right_attach_axis_x_rotation_value_label = None
        self._right_attach_axis_y_rotation_value_label = None
        self._right_attach_axis_z_rotation_value_label = None
        self._init_ui()

    def _find_ui_child(self, widget_type, object_name: str):
        """从已加载的 UI 控件树中查找子控件。"""
        ui_root = getattr(self, "_ui", None)
        if ui_root is not None and isValid(ui_root):
            return ui_root.findChild(widget_type, object_name)
        return self.findChild(widget_type, object_name)

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

        self._apply_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "applyLocationButton"))
        self._cancel_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "cancelApplyLocationButton"))
        self._apply_right_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "applyRightLocationButton"))
        self._cancel_right_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "cancelApplyRightLocationButton"))
        self._left_attach_axis_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "leftAttachAxisButton"))
        self._left_attach_axis_x_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "leftAttachAxisXEdit"))
        self._left_attach_axis_y_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "leftAttachAxisYEdit"))
        self._left_attach_axis_z_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "leftAttachAxisZEdit"))
        self._left_attach_axis_set_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "leftAttachAxisSetButton"))
        self._left_attach_axis_x_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "leftAttachAxisXRotationSlider"))
        self._left_attach_axis_y_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "leftAttachAxisYRotationSlider"))
        self._left_attach_axis_z_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "leftAttachAxisZRotationSlider"))
        self._left_attach_axis_x_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "leftAttachAxisXRotationValueLabel"))
        self._left_attach_axis_y_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "leftAttachAxisYRotationValueLabel"))
        self._left_attach_axis_z_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "leftAttachAxisZRotationValueLabel"))
        self._right_attach_axis_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "rightAttachAxisButton"))
        self._right_attach_axis_x_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "rightAttachAxisXEdit"))
        self._right_attach_axis_y_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "rightAttachAxisYEdit"))
        self._right_attach_axis_z_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "rightAttachAxisZEdit"))
        self._right_attach_axis_set_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "rightAttachAxisSetButton"))
        self._right_attach_axis_x_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "rightAttachAxisXRotationSlider"))
        self._right_attach_axis_y_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "rightAttachAxisYRotationSlider"))
        self._right_attach_axis_z_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "rightAttachAxisZRotationSlider"))
        self._right_attach_axis_x_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "rightAttachAxisXRotationValueLabel"))
        self._right_attach_axis_y_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "rightAttachAxisYRotationValueLabel"))
        self._right_attach_axis_z_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "rightAttachAxisZRotationValueLabel"))
        assert self._apply_button is not None, "UI 控件未找到：applyLocationButton"
        assert self._cancel_button is not None, "UI 控件未找到：cancelApplyLocationButton"
        assert self._apply_right_button is not None, "UI 控件未找到：applyRightLocationButton"
        assert self._cancel_right_button is not None, "UI 控件未找到：cancelApplyRightLocationButton"
        assert self._left_attach_axis_button is not None, "UI 控件未找到：leftAttachAxisButton"
        assert self._left_attach_axis_x_edit is not None, "UI 控件未找到：leftAttachAxisXEdit"
        assert self._left_attach_axis_y_edit is not None, "UI 控件未找到：leftAttachAxisYEdit"
        assert self._left_attach_axis_z_edit is not None, "UI 控件未找到：leftAttachAxisZEdit"
        assert self._left_attach_axis_set_button is not None, "UI 控件未找到：leftAttachAxisSetButton"
        assert self._left_attach_axis_x_rotation_slider is not None, "UI 控件未找到：leftAttachAxisXRotationSlider"
        assert self._left_attach_axis_y_rotation_slider is not None, "UI 控件未找到：leftAttachAxisYRotationSlider"
        assert self._left_attach_axis_z_rotation_slider is not None, "UI 控件未找到：leftAttachAxisZRotationSlider"
        assert self._left_attach_axis_x_rotation_value_label is not None, "UI 控件未找到：leftAttachAxisXRotationValueLabel"
        assert self._left_attach_axis_y_rotation_value_label is not None, "UI 控件未找到：leftAttachAxisYRotationValueLabel"
        assert self._left_attach_axis_z_rotation_value_label is not None, "UI 控件未找到：leftAttachAxisZRotationValueLabel"
        assert self._right_attach_axis_button is not None, "UI 控件未找到：rightAttachAxisButton"
        assert self._right_attach_axis_x_edit is not None, "UI 控件未找到：rightAttachAxisXEdit"
        assert self._right_attach_axis_y_edit is not None, "UI 控件未找到：rightAttachAxisYEdit"
        assert self._right_attach_axis_z_edit is not None, "UI 控件未找到：rightAttachAxisZEdit"
        assert self._right_attach_axis_set_button is not None, "UI 控件未找到：rightAttachAxisSetButton"
        assert self._right_attach_axis_x_rotation_slider is not None, "UI 控件未找到：rightAttachAxisXRotationSlider"
        assert self._right_attach_axis_y_rotation_slider is not None, "UI 控件未找到：rightAttachAxisYRotationSlider"
        assert self._right_attach_axis_z_rotation_slider is not None, "UI 控件未找到：rightAttachAxisZRotationSlider"
        assert self._right_attach_axis_x_rotation_value_label is not None, "UI 控件未找到：rightAttachAxisXRotationValueLabel"
        assert self._right_attach_axis_y_rotation_value_label is not None, "UI 控件未找到：rightAttachAxisYRotationValueLabel"
        assert self._right_attach_axis_z_rotation_value_label is not None, "UI 控件未找到：rightAttachAxisZRotationValueLabel"
        self._apply_button.clicked.connect(self._on_apply_clicked)
        self._cancel_button.clicked.connect(self._on_cancel_clicked)
        self._apply_right_button.clicked.connect(self._on_apply_right_clicked)
        self._cancel_right_button.clicked.connect(self._on_cancel_right_clicked)
        self._left_attach_axis_button.clicked.connect(self._on_left_attach_axis_clicked)
        self._left_attach_axis_set_button.clicked.connect(self._on_set_left_attach_axis_offset_clicked)
        self._left_attach_axis_x_rotation_slider.valueChanged.connect(self._on_left_attach_axis_rotation_value_changed)
        self._left_attach_axis_x_rotation_slider.sliderReleased.connect(self._on_left_attach_axis_rotation_slider_released)
        self._left_attach_axis_y_rotation_slider.valueChanged.connect(self._on_left_attach_axis_rotation_value_changed)
        self._left_attach_axis_y_rotation_slider.sliderReleased.connect(self._on_left_attach_axis_rotation_slider_released)
        self._left_attach_axis_z_rotation_slider.valueChanged.connect(self._on_left_attach_axis_rotation_value_changed)
        self._left_attach_axis_z_rotation_slider.sliderReleased.connect(self._on_left_attach_axis_rotation_slider_released)
        self._right_attach_axis_button.clicked.connect(self._on_right_attach_axis_clicked)
        self._right_attach_axis_set_button.clicked.connect(self._on_set_right_attach_axis_offset_clicked)
        self._right_attach_axis_x_rotation_slider.valueChanged.connect(self._on_right_attach_axis_rotation_value_changed)
        self._right_attach_axis_x_rotation_slider.sliderReleased.connect(self._on_right_attach_axis_rotation_slider_released)
        self._right_attach_axis_y_rotation_slider.valueChanged.connect(self._on_right_attach_axis_rotation_value_changed)
        self._right_attach_axis_y_rotation_slider.sliderReleased.connect(self._on_right_attach_axis_rotation_slider_released)
        self._right_attach_axis_z_rotation_slider.valueChanged.connect(self._on_right_attach_axis_rotation_value_changed)
        self._right_attach_axis_z_rotation_slider.sliderReleased.connect(self._on_right_attach_axis_rotation_slider_released)
        self.sync_left_attach_axis_offset_values()
        self.sync_left_attach_axis_rotation_values()
        self.sync_right_attach_axis_offset_values()
        self.sync_right_attach_axis_rotation_values()
        self.sync_left_attach_axis_button_text()
        self.sync_right_attach_axis_button_text()

    def _resolve_apply_button(self) -> QPushButton:
        """安全获取应用定位按钮。"""
        if self._apply_button is not None and isValid(self._apply_button):
            return self._apply_button

        self._apply_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "applyLocationButton"))
        if self._apply_button is None:
            raise RuntimeError("无法找到 applyLocationButton 控件")
        return self._apply_button

    def _resolve_cancel_button(self) -> QPushButton:
        """安全获取取消应用定位按钮。"""
        if self._cancel_button is not None and isValid(self._cancel_button):
            return self._cancel_button

        self._cancel_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "cancelApplyLocationButton"))
        if self._cancel_button is None:
            raise RuntimeError("无法找到 cancelApplyLocationButton 控件")
        return self._cancel_button

    def _resolve_left_attach_axis_button(self) -> QPushButton:
        """安全获取左手附加点切换按钮。"""
        if self._left_attach_axis_button is not None and isValid(self._left_attach_axis_button):
            return self._left_attach_axis_button

        self._left_attach_axis_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "leftAttachAxisButton"))
        if self._left_attach_axis_button is None:
            raise RuntimeError("无法找到 leftAttachAxisButton 控件")
        return self._left_attach_axis_button

    def _resolve_left_attach_axis_edits(self) -> tuple[QLineEdit, QLineEdit, QLineEdit]:
        """安全获取左手附加点 XYZ 输入框。"""
        if (
            self._left_attach_axis_x_edit is not None and isValid(self._left_attach_axis_x_edit)
            and self._left_attach_axis_y_edit is not None and isValid(self._left_attach_axis_y_edit)
            and self._left_attach_axis_z_edit is not None and isValid(self._left_attach_axis_z_edit)
        ):
            return (
                self._left_attach_axis_x_edit,
                self._left_attach_axis_y_edit,
                self._left_attach_axis_z_edit,
            )

        self._left_attach_axis_x_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "leftAttachAxisXEdit"))
        self._left_attach_axis_y_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "leftAttachAxisYEdit"))
        self._left_attach_axis_z_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "leftAttachAxisZEdit"))
        if self._left_attach_axis_x_edit is None:
            raise RuntimeError("无法找到 leftAttachAxisXEdit 控件")
        if self._left_attach_axis_y_edit is None:
            raise RuntimeError("无法找到 leftAttachAxisYEdit 控件")
        if self._left_attach_axis_z_edit is None:
            raise RuntimeError("无法找到 leftAttachAxisZEdit 控件")
        return (
            self._left_attach_axis_x_edit,
            self._left_attach_axis_y_edit,
            self._left_attach_axis_z_edit,
        )

    def _resolve_left_attach_axis_set_button(self) -> QPushButton:
        """安全获取左手附加点偏移量设置按钮。"""
        if self._left_attach_axis_set_button is not None and isValid(self._left_attach_axis_set_button):
            return self._left_attach_axis_set_button

        self._left_attach_axis_set_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "leftAttachAxisSetButton"))
        if self._left_attach_axis_set_button is None:
            raise RuntimeError("无法找到 leftAttachAxisSetButton 控件")
        return self._left_attach_axis_set_button

    def _resolve_left_attach_axis_rotation_sliders(self) -> tuple[QSlider, QSlider, QSlider]:
        """安全获取左手附加点 XYZ 旋转滑条。"""
        if (
            self._left_attach_axis_x_rotation_slider is not None and isValid(self._left_attach_axis_x_rotation_slider)
            and self._left_attach_axis_y_rotation_slider is not None and isValid(self._left_attach_axis_y_rotation_slider)
            and self._left_attach_axis_z_rotation_slider is not None and isValid(self._left_attach_axis_z_rotation_slider)
        ):
            return (
                self._left_attach_axis_x_rotation_slider,
                self._left_attach_axis_y_rotation_slider,
                self._left_attach_axis_z_rotation_slider,
            )

        self._left_attach_axis_x_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "leftAttachAxisXRotationSlider"))
        self._left_attach_axis_y_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "leftAttachAxisYRotationSlider"))
        self._left_attach_axis_z_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "leftAttachAxisZRotationSlider"))
        if self._left_attach_axis_x_rotation_slider is None:
            raise RuntimeError("无法找到 leftAttachAxisXRotationSlider 控件")
        if self._left_attach_axis_y_rotation_slider is None:
            raise RuntimeError("无法找到 leftAttachAxisYRotationSlider 控件")
        if self._left_attach_axis_z_rotation_slider is None:
            raise RuntimeError("无法找到 leftAttachAxisZRotationSlider 控件")
        return (
            self._left_attach_axis_x_rotation_slider,
            self._left_attach_axis_y_rotation_slider,
            self._left_attach_axis_z_rotation_slider,
        )

    def _resolve_left_attach_axis_rotation_value_labels(self) -> tuple[QLabel, QLabel, QLabel]:
        """安全获取左手附加点 XYZ 旋转数值标签。"""
        if (
            self._left_attach_axis_x_rotation_value_label is not None and isValid(self._left_attach_axis_x_rotation_value_label)
            and self._left_attach_axis_y_rotation_value_label is not None and isValid(self._left_attach_axis_y_rotation_value_label)
            and self._left_attach_axis_z_rotation_value_label is not None and isValid(self._left_attach_axis_z_rotation_value_label)
        ):
            return (
                self._left_attach_axis_x_rotation_value_label,
                self._left_attach_axis_y_rotation_value_label,
                self._left_attach_axis_z_rotation_value_label,
            )

        self._left_attach_axis_x_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "leftAttachAxisXRotationValueLabel"))
        self._left_attach_axis_y_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "leftAttachAxisYRotationValueLabel"))
        self._left_attach_axis_z_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "leftAttachAxisZRotationValueLabel"))
        if self._left_attach_axis_x_rotation_value_label is None:
            raise RuntimeError("无法找到 leftAttachAxisXRotationValueLabel 控件")
        if self._left_attach_axis_y_rotation_value_label is None:
            raise RuntimeError("无法找到 leftAttachAxisYRotationValueLabel 控件")
        if self._left_attach_axis_z_rotation_value_label is None:
            raise RuntimeError("无法找到 leftAttachAxisZRotationValueLabel 控件")
        return (
            self._left_attach_axis_x_rotation_value_label,
            self._left_attach_axis_y_rotation_value_label,
            self._left_attach_axis_z_rotation_value_label,
        )

    def _resolve_right_attach_axis_button(self) -> QPushButton:
        """安全获取右手附加点切换按钮。"""
        if self._right_attach_axis_button is not None and isValid(self._right_attach_axis_button):
            return self._right_attach_axis_button

        self._right_attach_axis_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "rightAttachAxisButton"))
        if self._right_attach_axis_button is None:
            raise RuntimeError("无法找到 rightAttachAxisButton 控件")
        return self._right_attach_axis_button

    def _resolve_right_attach_axis_edits(self) -> tuple[QLineEdit, QLineEdit, QLineEdit]:
        """安全获取右手附加点 XYZ 输入框。"""
        if (
            self._right_attach_axis_x_edit is not None and isValid(self._right_attach_axis_x_edit)
            and self._right_attach_axis_y_edit is not None and isValid(self._right_attach_axis_y_edit)
            and self._right_attach_axis_z_edit is not None and isValid(self._right_attach_axis_z_edit)
        ):
            return (
                self._right_attach_axis_x_edit,
                self._right_attach_axis_y_edit,
                self._right_attach_axis_z_edit,
            )

        self._right_attach_axis_x_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "rightAttachAxisXEdit"))
        self._right_attach_axis_y_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "rightAttachAxisYEdit"))
        self._right_attach_axis_z_edit = cast(QLineEdit | None, self._find_ui_child(QLineEdit, "rightAttachAxisZEdit"))
        if self._right_attach_axis_x_edit is None:
            raise RuntimeError("无法找到 rightAttachAxisXEdit 控件")
        if self._right_attach_axis_y_edit is None:
            raise RuntimeError("无法找到 rightAttachAxisYEdit 控件")
        if self._right_attach_axis_z_edit is None:
            raise RuntimeError("无法找到 rightAttachAxisZEdit 控件")
        return (
            self._right_attach_axis_x_edit,
            self._right_attach_axis_y_edit,
            self._right_attach_axis_z_edit,
        )

    def _resolve_right_attach_axis_set_button(self) -> QPushButton:
        """安全获取右手附加点偏移量设置按钮。"""
        if self._right_attach_axis_set_button is not None and isValid(self._right_attach_axis_set_button):
            return self._right_attach_axis_set_button

        self._right_attach_axis_set_button = cast(QPushButton | None, self._find_ui_child(QPushButton, "rightAttachAxisSetButton"))
        if self._right_attach_axis_set_button is None:
            raise RuntimeError("无法找到 rightAttachAxisSetButton 控件")
        return self._right_attach_axis_set_button

    def _resolve_right_attach_axis_rotation_sliders(self) -> tuple[QSlider, QSlider, QSlider]:
        """安全获取右手附加点 XYZ 旋转滑条。"""
        if (
            self._right_attach_axis_x_rotation_slider is not None and isValid(self._right_attach_axis_x_rotation_slider)
            and self._right_attach_axis_y_rotation_slider is not None and isValid(self._right_attach_axis_y_rotation_slider)
            and self._right_attach_axis_z_rotation_slider is not None and isValid(self._right_attach_axis_z_rotation_slider)
        ):
            return (
                self._right_attach_axis_x_rotation_slider,
                self._right_attach_axis_y_rotation_slider,
                self._right_attach_axis_z_rotation_slider,
            )

        self._right_attach_axis_x_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "rightAttachAxisXRotationSlider"))
        self._right_attach_axis_y_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "rightAttachAxisYRotationSlider"))
        self._right_attach_axis_z_rotation_slider = cast(QSlider | None, self._find_ui_child(QSlider, "rightAttachAxisZRotationSlider"))
        if self._right_attach_axis_x_rotation_slider is None:
            raise RuntimeError("无法找到 rightAttachAxisXRotationSlider 控件")
        if self._right_attach_axis_y_rotation_slider is None:
            raise RuntimeError("无法找到 rightAttachAxisYRotationSlider 控件")
        if self._right_attach_axis_z_rotation_slider is None:
            raise RuntimeError("无法找到 rightAttachAxisZRotationSlider 控件")
        return (
            self._right_attach_axis_x_rotation_slider,
            self._right_attach_axis_y_rotation_slider,
            self._right_attach_axis_z_rotation_slider,
        )

    def _resolve_right_attach_axis_rotation_value_labels(self) -> tuple[QLabel, QLabel, QLabel]:
        """安全获取右手附加点 XYZ 旋转数值标签。"""
        if (
            self._right_attach_axis_x_rotation_value_label is not None and isValid(self._right_attach_axis_x_rotation_value_label)
            and self._right_attach_axis_y_rotation_value_label is not None and isValid(self._right_attach_axis_y_rotation_value_label)
            and self._right_attach_axis_z_rotation_value_label is not None and isValid(self._right_attach_axis_z_rotation_value_label)
        ):
            return (
                self._right_attach_axis_x_rotation_value_label,
                self._right_attach_axis_y_rotation_value_label,
                self._right_attach_axis_z_rotation_value_label,
            )

        self._right_attach_axis_x_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "rightAttachAxisXRotationValueLabel"))
        self._right_attach_axis_y_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "rightAttachAxisYRotationValueLabel"))
        self._right_attach_axis_z_rotation_value_label = cast(QLabel | None, self._find_ui_child(QLabel, "rightAttachAxisZRotationValueLabel"))
        if self._right_attach_axis_x_rotation_value_label is None:
            raise RuntimeError("无法找到 rightAttachAxisXRotationValueLabel 控件")
        if self._right_attach_axis_y_rotation_value_label is None:
            raise RuntimeError("无法找到 rightAttachAxisYRotationValueLabel 控件")
        if self._right_attach_axis_z_rotation_value_label is None:
            raise RuntimeError("无法找到 rightAttachAxisZRotationValueLabel 控件")
        return (
            self._right_attach_axis_x_rotation_value_label,
            self._right_attach_axis_y_rotation_value_label,
            self._right_attach_axis_z_rotation_value_label,
        )

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

    def sync_left_attach_axis_button_text(self):
        """同步左手附加点按钮文本。"""
        left_attach_axis_button = self._resolve_left_attach_axis_button()

        has_attach_axis = False
        if self._vive_tracker_widget is not None:
            has_attach_axis = self._vive_tracker_widget.has_left_tracker_attach_axis()

        left_attach_axis_button.setText(
            "删除左手附加点" if has_attach_axis else "附加左手附加点"
        )

    def sync_right_attach_axis_button_text(self):
        """同步右手附加点按钮文本。"""
        right_attach_axis_button = self._resolve_right_attach_axis_button()

        has_attach_axis = False
        if self._vive_tracker_widget is not None:
            has_attach_axis = self._vive_tracker_widget.has_right_tracker_attach_axis()

        right_attach_axis_button.setText(
            "删除右手附加点" if has_attach_axis else "附加右手附加点"
        )

    def sync_left_attach_axis_offset_values(self):
        """同步左手附加点偏移量到输入框。"""
        left_attach_axis_x_edit, left_attach_axis_y_edit, left_attach_axis_z_edit = self._resolve_left_attach_axis_edits()

        offset_xyz = (0.0, 0.05, 0.03)
        if self._vive_tracker_widget is not None:
            offset_xyz = self._vive_tracker_widget.get_left_tracker_attach_axis_offset_xyz()

        left_attach_axis_x_edit.setText(f"{offset_xyz[0]:.4f}")
        left_attach_axis_y_edit.setText(f"{offset_xyz[1]:.4f}")
        left_attach_axis_z_edit.setText(f"{offset_xyz[2]:.4f}")

    def sync_left_attach_axis_rotation_values(self):
        """同步左手附加点局部旋转到滑条和数值标签。"""
        x_slider, y_slider, z_slider = self._resolve_left_attach_axis_rotation_sliders()
        x_label, y_label, z_label = self._resolve_left_attach_axis_rotation_value_labels()

        rotation_xyz_deg = (0.0, 0.0, 0.0)
        if self._vive_tracker_widget is not None:
            rotation_xyz_deg = self._vive_tracker_widget.get_left_tracker_attach_axis_local_rotation_xyz_degrees()

        for slider, value in (
            (x_slider, rotation_xyz_deg[0]),
            (y_slider, rotation_xyz_deg[1]),
            (z_slider, rotation_xyz_deg[2]),
        ):
            slider.blockSignals(True)
            slider.setValue(int(round(value)) % 361)
            slider.blockSignals(False)

        x_label.setText(f"{x_slider.value()}°")
        y_label.setText(f"{y_slider.value()}°")
        z_label.setText(f"{z_slider.value()}°")

    def sync_right_attach_axis_offset_values(self):
        """同步右手附加点偏移量到输入框。"""
        right_attach_axis_x_edit, right_attach_axis_y_edit, right_attach_axis_z_edit = self._resolve_right_attach_axis_edits()

        offset_xyz = (0.0, 0.0, 0.2)
        if self._vive_tracker_widget is not None:
            offset_xyz = self._vive_tracker_widget.get_right_tracker_attach_axis_offset_xyz()

        right_attach_axis_x_edit.setText(f"{offset_xyz[0]:.4f}")
        right_attach_axis_y_edit.setText(f"{offset_xyz[1]:.4f}")
        right_attach_axis_z_edit.setText(f"{offset_xyz[2]:.4f}")

    def sync_right_attach_axis_rotation_values(self):
        """同步右手附加点局部旋转到滑条和数值标签。"""
        x_slider, y_slider, z_slider = self._resolve_right_attach_axis_rotation_sliders()
        x_label, y_label, z_label = self._resolve_right_attach_axis_rotation_value_labels()

        rotation_xyz_deg = (0.0, 0.0, 0.0)
        if self._vive_tracker_widget is not None:
            rotation_xyz_deg = self._vive_tracker_widget.get_right_tracker_attach_axis_local_rotation_xyz_degrees()

        for slider, value in (
            (x_slider, rotation_xyz_deg[0]),
            (y_slider, rotation_xyz_deg[1]),
            (z_slider, rotation_xyz_deg[2]),
        ):
            slider.blockSignals(True)
            slider.setValue(int(round(value)) % 361)
            slider.blockSignals(False)

        x_label.setText(f"{x_slider.value()}°")
        y_label.setText(f"{y_slider.value()}°")
        z_label.setText(f"{z_slider.value()}°")

    def _on_left_attach_axis_clicked(self):
        """创建或删除左手附加点坐标轴。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法切换左手附加点")
            return

        if self._vive_tracker_widget.has_left_tracker_attach_axis():
            removed = self._vive_tracker_widget.remove_left_tracker_attach_axis()
            if removed:
                self.sync_left_attach_axis_button_text()
                print("[CaliApply] 已删除左手附加点")
            else:
                print("[CaliApply] 左手附加点当前不存在")
            return

        created = self._vive_tracker_widget.create_left_tracker_attach_axis()
        if created:
            self.sync_left_attach_axis_button_text()
            print("[CaliApply] 已附加左手附加点")
        else:
            print("[CaliApply] 左手附加点创建失败")

    def _on_right_attach_axis_clicked(self):
        """创建或删除右手附加点坐标轴。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法切换右手附加点")
            return

        if self._vive_tracker_widget.has_right_tracker_attach_axis():
            removed = self._vive_tracker_widget.remove_right_tracker_attach_axis()
            if removed:
                self.sync_right_attach_axis_button_text()
                print("[CaliApply] 已删除右手附加点")
            else:
                print("[CaliApply] 右手附加点当前不存在")
            return

        created = self._vive_tracker_widget.create_right_tracker_attach_axis()
        if created:
            self.sync_right_attach_axis_button_text()
            print("[CaliApply] 已附加右手附加点")
        else:
            print("[CaliApply] 右手附加点创建失败")

    def _on_set_left_attach_axis_offset_clicked(self):
        """应用左手附加点偏移量设置。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法设置左手附加点偏移量")
            return

        left_attach_axis_x_edit, left_attach_axis_y_edit, left_attach_axis_z_edit = self._resolve_left_attach_axis_edits()

        try:
            x = float(left_attach_axis_x_edit.text())
            y = float(left_attach_axis_y_edit.text())
            z = float(left_attach_axis_z_edit.text())
        except ValueError as e:
            print(f"[CaliApply] 左手附加点偏移量设置失败：无效的数值 - {e}")
            return

        self._vive_tracker_widget.set_left_tracker_attach_axis_offset_xyz((x, y, z))
        self._save_attach_axis_config()
        self.sync_left_attach_axis_offset_values()
        print(f"[CaliApply] 左手附加点偏移量已设置：X={x:.4f}m, Y={y:.4f}m, Z={z:.4f}m")

    def _on_set_right_attach_axis_offset_clicked(self):
        """应用右手附加点偏移量设置。"""
        if self._vive_tracker_widget is None:
            print("[CaliApply] ViveTrackerWidget 不可用，无法设置右手附加点偏移量")
            return

        right_attach_axis_x_edit, right_attach_axis_y_edit, right_attach_axis_z_edit = self._resolve_right_attach_axis_edits()

        try:
            x = float(right_attach_axis_x_edit.text())
            y = float(right_attach_axis_y_edit.text())
            z = float(right_attach_axis_z_edit.text())
        except ValueError as e:
            print(f"[CaliApply] 右手附加点偏移量设置失败：无效的数值 - {e}")
            return

        self._vive_tracker_widget.set_right_tracker_attach_axis_offset_xyz((x, y, z))
        self._save_attach_axis_config()
        self.sync_right_attach_axis_offset_values()
        print(f"[CaliApply] 右手附加点偏移量已设置：X={x:.4f}m, Y={y:.4f}m, Z={z:.4f}m")

    def _on_left_attach_axis_rotation_value_changed(self, _value: int):
        """实时更新左手附加点局部旋转。"""
        x_slider, y_slider, z_slider = self._resolve_left_attach_axis_rotation_sliders()
        x_label, y_label, z_label = self._resolve_left_attach_axis_rotation_value_labels()

        x_label.setText(f"{x_slider.value()}°")
        y_label.setText(f"{y_slider.value()}°")
        z_label.setText(f"{z_slider.value()}°")

        if self._vive_tracker_widget is None:
            return

        self._vive_tracker_widget.set_left_tracker_attach_axis_local_rotation_xyz_degrees(
            (
                float(x_slider.value()),
                float(y_slider.value()),
                float(z_slider.value()),
            )
        )

    def _on_left_attach_axis_rotation_slider_released(self):
        """左手旋转滑条释放时保存配置。"""
        self._save_attach_axis_config()

    def _on_right_attach_axis_rotation_value_changed(self, _value: int):
        """实时更新右手附加点局部旋转。"""
        x_slider, y_slider, z_slider = self._resolve_right_attach_axis_rotation_sliders()
        x_label, y_label, z_label = self._resolve_right_attach_axis_rotation_value_labels()

        x_label.setText(f"{x_slider.value()}°")
        y_label.setText(f"{y_slider.value()}°")
        z_label.setText(f"{z_slider.value()}°")

        if self._vive_tracker_widget is None:
            return

        self._vive_tracker_widget.set_right_tracker_attach_axis_local_rotation_xyz_degrees(
            (
                float(x_slider.value()),
                float(y_slider.value()),
                float(z_slider.value()),
            )
        )

    def _on_right_attach_axis_rotation_slider_released(self):
        """右手旋转滑条释放时保存配置。"""
        self._save_attach_axis_config()


    def _save_attach_axis_config(self):
        """保存左右手附加点配置到 config.json。"""
        if self._vive_tracker_widget is None:
            return
        try:
            from src.config_io import read_config, write_config
            cfg = read_config()
            if "vive_tracker_attach_axis" not in cfg:
                cfg["vive_tracker_attach_axis"] = {}
            
            left_offset = self._vive_tracker_widget.get_left_tracker_attach_axis_offset_xyz()
            left_rotation = self._vive_tracker_widget.get_left_tracker_attach_axis_local_rotation_xyz_degrees()
            right_offset = self._vive_tracker_widget.get_right_tracker_attach_axis_offset_xyz()
            right_rotation = self._vive_tracker_widget.get_right_tracker_attach_axis_local_rotation_xyz_degrees()
            
            cfg["vive_tracker_attach_axis"]["left"] = {
                "offset_xyz": list(left_offset),
                "rotation_xyz_degrees": list(left_rotation),
            }
            cfg["vive_tracker_attach_axis"]["right"] = {
                "offset_xyz": list(right_offset),
                "rotation_xyz_degrees": list(right_rotation),
            }
            
            write_config(cfg)
            print("[CaliApply] 附加点配置已保存到 config.json")
        except Exception as e:
            print(f"[CaliApply] 保存附加点配置失败：{e}")


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