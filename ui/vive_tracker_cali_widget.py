"""vive_tracker_cali_widget.py
定位标定面板

功能：
- 提供定位标定的 UI 界面
- 处理标定按钮点击，获取左手 tracker 位置，计算偏差并应用到所有 tracker 和 lighthouse
- 处理取消标定按钮点击，重置所有位置偏差为 0
- 记录标定日志
"""

import sys
import builtins
import math
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QGroupBox, QCheckBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt
from PySide6.QtGui import QTextCursor, QCursor
from PySide6.QtWidgets import QMenu
from shiboken6 import isValid

from src.xsqeconverter import quat_to_euler_degree


CALIBRATION_DEBUG_PRINTS = True
_EULER_ORDER_ZXY = 4


def print(*args, **kwargs):
    if CALIBRATION_DEBUG_PRINTS:
        builtins.print(*args, **kwargs)


def _find_calibration_ui_file() -> Path:
    """查找 vive_tracker_cali_widget.ui 文件的路径。"""
    candidates = [
        Path(__file__).parent / "vive_tracker_cali_widget.ui",
        Path(__file__).parent.parent / "ui" / "vive_tracker_cali_widget.ui",
        Path.cwd() / "ui" / "vive_tracker_cali_widget.ui",
    ]
    
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(2, Path(meipass) / "ui" / "vive_tracker_cali_widget.ui")
        candidates.insert(3, Path(meipass) / "_internal" / "ui" / "vive_tracker_cali_widget.ui")
    
    try:
        exe_dir = Path(sys.executable).parent
        candidates.insert(len(candidates) - 1, exe_dir / "ui" / "vive_tracker_cali_widget.ui")
        candidates.insert(len(candidates) - 1, exe_dir / "_internal" / "ui" / "vive_tracker_cali_widget.ui")
    except Exception:
        pass
    
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except Exception:
            continue
    
    # 搜索所有 ui 目录
    search_roots = [Path(__file__).parent, Path(__file__).parent.parent, Path.cwd()]
    if meipass:
        search_roots.insert(0, Path(meipass))
    
    for root in search_roots:
        try:
            for p in root.rglob("vive_tracker_cali_widget.ui"):
                return p
        except Exception:
            continue
    
    return candidates[0]


class CalibrationWidget(QWidget):
    """定位标定面板。"""

    def __init__(self, parent=None, vive_tracker_widget=None):
        """初始化标定面板。
        
        Args:
            parent: 父 QWidget
            vive_tracker_widget: ViveTrackerWidget 实例引用，用于访问追踪器数据
        """
        super().__init__(parent)
        
        self._calibration_in_progress = False
        self._vive_tracker_widget = vive_tracker_widget  # 对 ViveTrackerWidget 的引用
        self._bias_value_label: QLabel | None = None
        self._info_group: QGroupBox | None = None
        self._position_rotation_checkbox: QCheckBox | None = None
        
        # 左手信息标签（10Hz 刷新）
        self._left_hand_position_label: QLabel | None = None
        self._left_hand_rotation_label: QLabel | None = None
        self._left_hand_quat_label: QLabel | None = None
        self._left_hand_show_quat = True
        self._left_hand_info_tick = 0
        
        # 右手信息标签（10Hz 刷新）
        self._right_hand_position_label: QLabel | None = None
        self._right_hand_rotation_label: QLabel | None = None
        self._right_hand_quat_label: QLabel | None = None
        self._right_hand_show_quat = True
        self._right_hand_info_tick = 0
        
        # 左手信息更新定时器（10Hz = 100ms）
        self._left_hand_info_timer = QTimer(self)
        self._left_hand_info_timer.timeout.connect(self._update_left_hand_info)
        self._left_hand_info_timer.setInterval(100)  # 100ms = 10Hz
        
        # 右手信息更新定时器（10Hz = 100ms）
        self._right_hand_info_timer = QTimer(self)
        self._right_hand_info_timer.timeout.connect(self._update_right_hand_info)
        self._right_hand_info_timer.setInterval(100)  # 100ms = 10Hz
        
        self._init_ui()
        self._add_log("系统初始化完成")

    @staticmethod
    def _format_quaternion_wxyz(quat_wxyz: tuple[float, float, float, float]) -> str:
        """将四元数 (w, x, y, z) 格式化为字符串显示。
        
        Args:
            quat_wxyz: 四元数 (w, x, y, z)
        
        Returns:
            str: 格式化的四元数字符串，例如 "w=1.0000  x=0.0000  y=0.0000  z=0.0000"
        """
        return (
            f"w={quat_wxyz[0]:.4f}  x={quat_wxyz[1]:.4f}  "
            f"y={quat_wxyz[2]:.4f}  z={quat_wxyz[3]:.4f}"
        )

    def _build_calibration_info_text(
        self,
        bias_xyz: tuple[float, float, float] | None,
        calibration_quat_wxyz: tuple[float, float, float, float],
        quat_additional_wxyz: tuple[float, float, float, float] | None = None,
        quat_location_bias_wxyz: tuple[float, float, float, float] | None = None,
    ) -> str:
        """构建标定信息显示文本。
        
        Args:
            bias_xyz: 位置偏差 (x, y, z)，单位米。若为 None，显示为 "-"
            calibration_quat_wxyz: 校准四元数 (w, x, y, z)
            quat_additional_wxyz: 附加旋转四元数 (w, x, y, z)，若为 None 则不显示
            quat_location_bias_wxyz: 位置偏移四元数 (w, x, y, z)，若为 None 则不显示
        
        Returns:
            str: 包含位置偏差、校准四元数、附加旋转和位置偏移四元数的格式化文本
        """
        if bias_xyz is None:
            bias_line = "位置偏差：-"
        else:
            bias_line = f"位置偏差: X={bias_xyz[0]:.4f}m, Y={bias_xyz[1]:.4f}m, Z={bias_xyz[2]:.4f}m"
        quat_line = f"标定四元数: {self._format_quaternion_wxyz(calibration_quat_wxyz)}"
        
        lines = [bias_line, quat_line]
        if quat_additional_wxyz is not None:
            additional_line = f"附加旋转: {self._format_quaternion_wxyz(quat_additional_wxyz)}"
            lines.append(additional_line)
        if quat_location_bias_wxyz is not None:
            location_bias_line = f"位置偏移四元数: {self._format_quaternion_wxyz(quat_location_bias_wxyz)}"
            lines.append(location_bias_line)
        
        return "\n".join(lines)

    @staticmethod
    def _build_y_axis_quaternion_wxyz(y_axis_degree: float) -> tuple[float, float, float, float]:
        """根据绕 Y 轴的角度构造四元数。"""
        half_radian = math.radians(y_axis_degree) * 0.5
        return (
            math.cos(half_radian),
            0.0,
            math.sin(half_radian),
            0.0,
        )

    @staticmethod
    def _format_euler_zxy_text(euler_xyz_degree: tuple[float, float, float]) -> str:
        """将由 ZXY 顺序换算得到的欧拉角格式化为显示文本。"""
        x_deg, y_deg, z_deg = euler_xyz_degree
        return f"欧拉角(ZXY)：Z={z_deg:7.2f}°  X={x_deg:7.2f}°  Y={y_deg:7.2f}°"

    def _bind_destroyed_debug(self, label: str, widget) -> None:
        """记录 Qt 对象何时被销毁。
        
        Args:
            label: 对象标签/名称，用于日志输出
            widget: 要监听的 Qt 对象
        """
        if widget is None or not isValid(widget):
            return

        try:
            widget.destroyed.connect(
                lambda *_args, _label=label: print(f"[CalibDebug] destroyed signal: {_label}")
            )
        except RuntimeError as exc:
            print(f"[CalibDebug] bind destroyed failed for {label}: {exc}")

    def _debug_widget_state(self, label: str, widget) -> None:
        """输出 widget 当前状态，便于定位 Qt 对象生命周期问题。
        
        Args:
            label: 调试标签
            widget: 要检查的 QWidget 对象
        """
        if widget is None:
            print(f"[CalibDebug] {label}: valid=False obj=None")
            return

        try:
            valid = isValid(widget)
        except Exception:
            valid = False

        if not valid:
            print(
                f"[CalibDebug] {label}: valid=False "
                f"py_type={type(widget).__name__} id=0x{id(widget):x}"
            )
            return

        try:
            print(
                f"[CalibDebug] {label}: "
                f"valid=True class={widget.metaObject().className()} "
                f"name={widget.objectName()} visible={widget.isVisible()} "
                f"enabled={widget.isEnabled()} parent={widget.parent()}"
            )
        except RuntimeError as exc:
            print(f"[CalibDebug] {label}: valid=True but access failed: {exc}")

    def _debug_snapshot(self, stage: str) -> None:
        """输出标定 UI 与数据状态快照，用于故障排查。
        
        Args:
            stage: 阶段标签，表示当前操作阶段（如 "init_ui", "calibration_complete" 等）
        """
        print(f"[CalibDebug] ---- snapshot: {stage} ----")
        self._debug_widget_state("self", self)
        self._debug_widget_state("ui", getattr(self, "_ui", None))
        self._debug_widget_state("calibration_btn", getattr(self, "_calibration_btn", None))
        self._debug_widget_state("cancel_calibration_btn", getattr(self, "_cancel_calibration_btn", None))
        self._debug_widget_state("status_label", getattr(self, "_status_label", None))
        self._debug_widget_state("time_label", getattr(self, "_time_label", None))
        self._debug_widget_state("log_text", getattr(self, "_log_text", None))
        self._debug_widget_state("bias_value_label", getattr(self, "_bias_value_label", None))
        self._debug_widget_state("info_group", getattr(self, "_info_group", None))

        if self._vive_tracker_widget is not None:
            try:
                with self._vive_tracker_widget._data_lock:
                    left_data = self._vive_tracker_widget._left_data
                    tracker_cali_state = self._vive_tracker_widget.get_tracker_cali_manager().get_state_snapshot()
                    print(
                        "[CalibDebug] left_data: "
                        f"valid={left_data.valid} "
                        f"origin=({left_data.pos_origin_x_m:.4f}, {left_data.pos_origin_y_m:.4f}, {left_data.pos_origin_z_m:.4f}) "
                        f"calib_quat=({left_data.quat_calibration_w:.4f}, {left_data.quat_calibration_x:.4f}, {left_data.quat_calibration_y:.4f}, {left_data.quat_calibration_z:.4f})"
                    )
                    print(
                        "[CalibDebug] tracker_cali_state: "
                        f"pos_bias=({tracker_cali_state.pos_bias_x_m:.4f}, {tracker_cali_state.pos_bias_y_m:.4f}, {tracker_cali_state.pos_bias_z_m:.4f}) "
                        f"location_bias=({tracker_cali_state.quat_location_bias_w:.4f}, {tracker_cali_state.quat_location_bias_x:.4f}, "
                        f"{tracker_cali_state.quat_location_bias_y:.4f}, {tracker_cali_state.quat_location_bias_z:.4f}) "
                        f"additional=({tracker_cali_state.quat_additional_w:.4f}, {tracker_cali_state.quat_additional_x:.4f}, "
                        f"{tracker_cali_state.quat_additional_y:.4f}, {tracker_cali_state.quat_additional_z:.4f})"
                    )
            except Exception as exc:
                print(f"[CalibDebug] left_data snapshot failed: {exc}")

        print(f"[CalibDebug] ---- snapshot end: {stage} ----")

    def _find_child_from_self(self, widget_type, object_name: str):
        """优先从 self 查找子控件，避免依赖可能失效的 _ui 引用。
        
        Args:
            widget_type: 要查找的 QWidget 类型
            object_name: 控件的对象名称
        
        Returns:
            QWidget 或其子类实例，若未找到则返回 None
        """
        try:
            child = self.findChild(widget_type, object_name)
        except RuntimeError as exc:
            print(f"[CalibDebug] self.findChild({object_name}) 失败: {exc}")
            child = None

        if child is not None:
            return child

        if getattr(self, "_ui", None) is not None and isValid(self._ui):
            try:
                return self._ui.findChild(widget_type, object_name)
            except RuntimeError as exc:
                print(f"[CalibDebug] _ui.findChild({object_name}) 失败: {exc}")

        return None

    def _ensure_bias_value_label(self) -> QLabel:
        """确保用于显示位置偏差的专用标签存在且可用。
        
        若标签已存在，直接返回；否则尝试查找或动态创建。
        
        Returns:
            QLabel 实例，用于显示位置偏差信息
        
        Raises:
            RuntimeError: 当 infoGroup 不存在或其布局不可用时
        """
        if self._bias_value_label is not None and isValid(self._bias_value_label):
            return self._bias_value_label

        self._info_group = self._find_child_from_self(QGroupBox, "infoGroup")
        if self._info_group is None:
            self._debug_snapshot("ensure_bias_value_label_no_info_group")
            raise RuntimeError("无法找到 infoGroup 控件")

        existing_label = self._find_child_from_self(QLabel, "biasValueLabel")
        if existing_label is not None:
            self._bias_value_label = existing_label
            self._debug_widget_state("resolved_bias_value_label", self._bias_value_label)
            return self._bias_value_label

        info_layout = self._info_group.layout()
        if info_layout is None:
            raise RuntimeError("infoGroup 没有可用布局")

        self._bias_value_label = QLabel(
            self._build_calibration_info_text(None, (1.0, 0.0, 0.0, 0.0)),
            self._info_group,
        )
        self._bias_value_label.setObjectName("biasValueLabel")
        self._bias_value_label.setWordWrap(True)
        self._bias_value_label.setFont(self._status_label.font())
        info_layout.insertWidget(0, self._bias_value_label)
        self._bias_value_label.setVisible(True)
        self._bind_destroyed_debug("biasValueLabel", self._bias_value_label)
        self._debug_widget_state("created_bias_value_label", self._bias_value_label)
        return self._bias_value_label

    def _ensure_right_hand_info_widgets(self) -> None:
        """确保右手信息区存在；若 UI 未定义则在运行时动态创建。"""
        if (
            self._right_hand_position_label is not None
            and self._right_hand_rotation_label is not None
            and self._right_hand_quat_label is not None
        ):
            return

        right_group = self._find_child_from_self(QGroupBox, "rightHandInfoGroup")
        if right_group is None:
            main_layout = self._ui.layout() if getattr(self, "_ui", None) is not None else None
            if main_layout is None:
                main_layout = self.layout()
            if main_layout is None:
                raise RuntimeError("CalibrationWidget 缺少主布局，无法创建 rightHandInfoGroup")

            right_group = QGroupBox("右手信息", self)
            right_group.setObjectName("rightHandInfoGroup")
            right_layout = QVBoxLayout(right_group)
            right_layout.setObjectName("rightHandInfoLayout")

            font = self._left_hand_position_label.font() if self._left_hand_position_label is not None else self.font()
            label_specs = [
                ("rightHandPositionLabel", "位置：X= 0.0000m  Y= 0.0000m  Z= 0.0000m"),
                ("rightHandRotationLabel", "旋转：Yaw= 0.00°  Pitch= 0.00°  Roll= 0.00°"),
                ("rightHandQuatLabel", "四元数：w= 0.0000  x= 0.0000  y= 0.0000  z= 0.0000"),
            ]
            for object_name, text in label_specs:
                label = QLabel(text, right_group)
                label.setObjectName(object_name)
                label.setWordWrap(True)
                label.setFont(font)
                right_layout.addWidget(label)

            insert_index = main_layout.count()
            log_group = self._find_child_from_self(QGroupBox, "logGroup")
            if log_group is not None:
                for index in range(main_layout.count()):
                    item = main_layout.itemAt(index)
                    if item is not None and item.widget() is log_group:
                        insert_index = index
                        break
            main_layout.insertWidget(insert_index, right_group)

        self._right_hand_position_label = self._find_child_from_self(QLabel, "rightHandPositionLabel")
        self._right_hand_rotation_label = self._find_child_from_self(QLabel, "rightHandRotationLabel")
        self._right_hand_quat_label = self._find_child_from_self(QLabel, "rightHandQuatLabel")

        if (
            self._right_hand_position_label is None
            or self._right_hand_rotation_label is None
            or self._right_hand_quat_label is None
        ):
            self._debug_snapshot("ensure_right_hand_info_widgets_failed")
            raise RuntimeError("无法创建右手信息控件")

    def _init_ui(self):
        """从 UI 文件加载界面并初始化控件连接。
        
        加载 vive_tracker_cali_widget.ui 文件，从中提取必要的控件，
        并连接相应的信号槽。初始化完成后会输出调试信息和状态快照。
        
        Raises:
            RuntimeError: 当 UI 文件无法打开或加载失败时
            AssertionError: 当必要的 UI 控件未找到时
        """
        loader = QUiLoader()
        ui_file = QFile(str(_find_calibration_ui_file()))
        
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_find_calibration_ui_file()}")
        
        self._ui = loader.load(ui_file)
        ui_file.close()
        
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_find_calibration_ui_file()}")
        
        # 将加载的 UI 添加到当前 widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ui)
        
        # 获取 UI 中的控件。优先从 self 递归查找，避免后续依赖 _ui 生命周期。
        self._calibration_btn: QPushButton = self.findChild(QPushButton, "calibrationButton")
        self._cancel_calibration_btn: QPushButton = self.findChild(QPushButton, "cancelCalibrationButton")
        self._position_rotation_checkbox = self.findChild(QCheckBox, "positionRotationCheckBox")
        self._status_label: QLabel = self.findChild(QLabel, "statusLabel")
        self._time_label: QLabel = self.findChild(QLabel, "timeLabel")
        self._log_text: QTextEdit = self.findChild(QTextEdit, "logText")
        
        # 获取左手信息标签
        self._left_hand_position_label = self.findChild(QLabel, "leftHandPositionLabel")
        self._left_hand_rotation_label = self.findChild(QLabel, "leftHandRotationLabel")
        self._left_hand_quat_label = self.findChild(QLabel, "leftHandQuatLabel")
        
        # 获取右手信息标签
        self._right_hand_position_label = self.findChild(QLabel, "rightHandPositionLabel")
        self._right_hand_rotation_label = self.findChild(QLabel, "rightHandRotationLabel")
        self._right_hand_quat_label = self.findChild(QLabel, "rightHandQuatLabel")
        self._ensure_right_hand_info_widgets()
        
        # 调试：打印找到的控件
        print(f"[CalibDebug] 控件查询结果:")
        print(f"  calibrationButton: {self._calibration_btn}")
        print(f"  cancelCalibrationButton: {self._cancel_calibration_btn}")
        print(f"  positionRotationCheckBox: {self._position_rotation_checkbox}")
        print(f"  statusLabel: {self._status_label}")
        print(f"  timeLabel: {self._time_label}")
        print(f"  logText: {self._log_text}")
        
        # 如果通过 findChild 没有找到标签，尝试通过 infoGroup 来查找
        if self._status_label is None:
            print("[CalibDebug] statusLabel 直接查询失败，尝试通过 infoGroup 查询...")
            info_group = self.findChild(QGroupBox, "infoGroup")
            if info_group:
                self._status_label = info_group.findChild(QLabel, "statusLabel")
                print(f"[CalibDebug] 通过 infoGroup 查询结果: {self._status_label}")
        
        if self._time_label is None:
            print("[CalibDebug] timeLabel 直接查询失败，尝试通过 infoGroup 查询...")
            info_group = self.findChild(QGroupBox, "infoGroup")
            if info_group:
                self._time_label = info_group.findChild(QLabel, "timeLabel")
                print(f"[CalibDebug] 通过 infoGroup 查询结果: {self._time_label}")
        
        # 验证所有必要的控件存在
        assert self._calibration_btn is not None, "UI 控件未找到：calibrationButton"
        assert self._cancel_calibration_btn is not None, "UI 控件未找到：cancelCalibrationButton"
        assert self._position_rotation_checkbox is not None, "UI 控件未找到：positionRotationCheckBox"
        assert self._status_label is not None, "UI 控件未找到：statusLabel"
        assert self._time_label is not None, "UI 控件未找到：timeLabel"
        assert self._log_text is not None, "UI 控件未找到：logText"
        assert self._left_hand_position_label is not None, "UI 控件未找到：leftHandPositionLabel"
        assert self._left_hand_rotation_label is not None, "UI 控件未找到：leftHandRotationLabel"
        assert self._left_hand_quat_label is not None, "UI 控件未找到：leftHandQuatLabel"
        assert self._right_hand_position_label is not None, "右手信息控件创建失败：rightHandPositionLabel"
        assert self._right_hand_rotation_label is not None, "右手信息控件创建失败：rightHandRotationLabel"
        assert self._right_hand_quat_label is not None, "右手信息控件创建失败：rightHandQuatLabel"

        if self._vive_tracker_widget is not None:
            self._position_rotation_checkbox.setChecked(
                self._vive_tracker_widget.is_position_calibration_rotation_enabled()
            )

        self._left_hand_rotation_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self._left_hand_rotation_label.customContextMenuRequested.connect(self._on_left_hand_attitude_context_menu)
        self._left_hand_quat_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self._left_hand_quat_label.customContextMenuRequested.connect(self._on_left_hand_attitude_context_menu)
        
        # 为右手标签设置右键菜单
        self._right_hand_rotation_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self._right_hand_rotation_label.customContextMenuRequested.connect(self._on_right_hand_attitude_context_menu)
        self._right_hand_quat_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self._right_hand_quat_label.customContextMenuRequested.connect(self._on_right_hand_attitude_context_menu)
        
        # 强制确保标签可见（解决隐藏问题）
        print("[CalibDebug] 强制设置标签可见性...")
        
        # 检查并显示父容器
        info_group = self.findChild(QGroupBox, "infoGroup")
        if info_group:
            print(f"[CalibDebug] infoGroup 可见性: {info_group.isVisible()}")
            info_group.setVisible(True)
        
        # 显示 _ui
        print(f"[CalibDebug] _ui 可见性: {self._ui.isVisible()}")
        self._ui.setVisible(True)
        
        self._status_label.setVisible(False)
        self._time_label.setVisible(False)
        self._info_group = self.findChild(QGroupBox, "infoGroup")
        self._ensure_bias_value_label()
        print(f"[CalibDebug] statusLabel 可见: {self._status_label.isVisible()}")
        print(f"[CalibDebug] timeLabel 可见: {self._time_label.isVisible()}")
        self._bind_destroyed_debug("self", self)
        self._bind_destroyed_debug("ui", self._ui)
        self._bind_destroyed_debug("calibrationButton", self._calibration_btn)
        self._bind_destroyed_debug("cancelCalibrationButton", self._cancel_calibration_btn)
        self._bind_destroyed_debug("positionRotationCheckBox", self._position_rotation_checkbox)
        self._bind_destroyed_debug("statusLabel", self._status_label)
        self._bind_destroyed_debug("timeLabel", self._time_label)
        self._bind_destroyed_debug("logText", self._log_text)
        self._bind_destroyed_debug("infoGroup", self._info_group)
        self._bind_destroyed_debug("leftHandPositionLabel", self._left_hand_position_label)
        self._bind_destroyed_debug("leftHandRotationLabel", self._left_hand_rotation_label)
        self._bind_destroyed_debug("leftHandQuatLabel", self._left_hand_quat_label)
        self._bind_destroyed_debug("rightHandPositionLabel", self._right_hand_position_label)
        self._bind_destroyed_debug("rightHandRotationLabel", self._right_hand_rotation_label)
        self._bind_destroyed_debug("rightHandQuatLabel", self._right_hand_quat_label)
        self._apply_left_hand_attitude_display_mode()
        self._apply_right_hand_attitude_display_mode()
        self._debug_snapshot("after_init_ui")
        
        # 连接信号
        self._calibration_btn.clicked.connect(self._on_calibration_clicked)
        self._cancel_calibration_btn.clicked.connect(self._on_cancel_calibration_clicked)
        self._position_rotation_checkbox.toggled.connect(self._on_position_rotation_checkbox_toggled)
        
        # 启动左手信息更新定时器（10Hz）
        self._left_hand_info_timer.start()
        print(
            "[CalibDebug] 左手信息定时器已启动: "
            f"active={self._left_hand_info_timer.isActive()} interval={self._left_hand_info_timer.interval()}ms"
        )
        
        # 启动右手信息更新定时器（10Hz）
        self._right_hand_info_timer.start()
        print(
            "[CalibDebug] 右手信息定时器已启动: "
            f"active={self._right_hand_info_timer.isActive()} interval={self._right_hand_info_timer.interval()}ms"
        )

    def set_tracking_controls_enabled(self, enabled: bool):
        """切换依赖追踪状态的标定按钮启用/禁用状态。
        
        Args:
            enabled: True 表示启用按钮，False 表示禁用按钮
        """
        try:
            self._calibration_btn.setEnabled(enabled)
            self._cancel_calibration_btn.setEnabled(enabled)
            if self._position_rotation_checkbox is not None:
                self._position_rotation_checkbox.setEnabled(enabled)
            if not enabled and not self._calibration_in_progress:
                try:
                    self._ensure_bias_value_label().setText(
                        self._build_calibration_info_text(None, (1.0, 0.0, 0.0, 0.0))
                    )
                except RuntimeError:
                    self._bias_value_label = None
                    bias_label = self._ensure_bias_value_label()
                    bias_label.setText(
                        self._build_calibration_info_text(None, (1.0, 0.0, 0.0, 0.0))
                    )
        except RuntimeError as e:
            print(f"[CalibDebug] set_tracking_controls_enabled 失败: {e}")

    def _on_position_rotation_checkbox_toggled(self, checked: bool) -> None:
        """切换是否对位置应用 quat_calibration 旋转。"""
        if self._vive_tracker_widget is None:
            return
        self._vive_tracker_widget.set_position_calibration_rotation_enabled(checked)
        print(f"[CalibDebug] 位置标定旋转开关: enabled={checked}")

    def _is_ui_valid(self) -> bool:
        """检查 UI 是否仍然有效（对象未被删除）。
        
        Returns:
            bool: True 表示 UI 对象有效，False 表示已被删除
        """
        if self._ui is None:
            return False
        if not isValid(self._ui):
            print("[CalibDebug] ⚠️ self._ui 已被删除")
            self._ui = None
            return False
        try:
            _ = self._ui.parent()
            return True
        except RuntimeError:
            print("[CalibDebug] ⚠️ self._ui 已被删除")
            self._ui = None
            return False

    def _resolve_log_text(self) -> QTextEdit:
        """安全地获取 logText 控件引用（防止过期指针）。
        
        Returns:
            QTextEdit 实例
        
        Raises:
            RuntimeError: 当 logText 控件无法找到时
        """
        if self._log_text is not None:
            try:
                _ = self._log_text.parent()
                return self._log_text
            except RuntimeError as e:
                print(f"[CalibDebug] logText 已被删除，重新查询: {e}")
                self._log_text = None
        
        self._log_text = self._find_child_from_self(QTextEdit, "logText")
        if self._log_text is None:
            self._debug_snapshot("resolve_log_text_failed")
            raise RuntimeError("无法找到 logText 控件")
        self._debug_widget_state("resolved_log_text", self._log_text)
        return self._log_text

    def _resolve_status_label(self) -> QLabel:
        """安全地获取 statusLabel 控件引用（防止过期指针）。
        
        Returns:
            QLabel 实例
        
        Raises:
            RuntimeError: 当 statusLabel 控件无法找到时
        """
        if self._status_label is not None:
            try:
                _ = self._status_label.parent()
                text = self._status_label.text()
                print(f"[CalibDebug] statusLabel 有效，当前文本: {text}")
                return self._status_label
            except RuntimeError as e:
                print(f"[CalibDebug] statusLabel 已被删除，重新查询: {e}")
                self._status_label = None
        
        print("[CalibDebug] 重新查询 statusLabel...")
        self._status_label = self._find_child_from_self(QLabel, "statusLabel")
        if self._status_label is None:
            print("[CalibDebug] ❌ statusLabel 未找到！")
            self._debug_snapshot("resolve_status_label_failed")
            raise RuntimeError("无法找到 statusLabel 控件")
        print(f"[CalibDebug] ✅ statusLabel 已找到")
        self._debug_widget_state("resolved_status_label", self._status_label)
        return self._status_label

    def _resolve_time_label(self) -> QLabel:
        """安全地获取 timeLabel 控件引用（防止过期指针）。
        
        Returns:
            QLabel 实例
        
        Raises:
            RuntimeError: 当 timeLabel 控件无法找到时
        """
        if self._time_label is not None:
            try:
                _ = self._time_label.parent()
                text = self._time_label.text()
                print(f"[CalibDebug] timeLabel 有效，当前文本: {text}")
                return self._time_label
            except RuntimeError as e:
                print(f"[CalibDebug] timeLabel 已被删除，重新查询: {e}")
                self._time_label = None
        
        print("[CalibDebug] 重新查询 timeLabel...")
        self._time_label = self._find_child_from_self(QLabel, "timeLabel")
        if self._time_label is None:
            print("[CalibDebug] ❌ timeLabel 未找到！")
            self._debug_snapshot("resolve_time_label_failed")
            raise RuntimeError("无法找到 timeLabel 控件")
        print(f"[CalibDebug] ✅ timeLabel 已找到")
        self._debug_widget_state("resolved_time_label", self._time_label)
        return self._time_label

    def _resolve_left_hand_position_label(self) -> QLabel:
        """安全地获取左手位置标签引用（防止过期指针）。"""
        if self._left_hand_position_label is not None and isValid(self._left_hand_position_label):
            return self._left_hand_position_label
        if self._left_hand_position_label is not None:
            print("[CalibDebug] leftHandPositionLabel 已失效，重新查询")
            self._left_hand_position_label = None

        self._left_hand_position_label = self._find_child_from_self(QLabel, "leftHandPositionLabel")
        if self._left_hand_position_label is None:
            self._debug_snapshot("resolve_left_hand_position_label_failed")
            raise RuntimeError("无法找到 leftHandPositionLabel 控件")
        self._debug_widget_state("resolved_left_hand_position_label", self._left_hand_position_label)
        return self._left_hand_position_label

    def _resolve_left_hand_rotation_label(self) -> QLabel:
        """安全地获取左手旋转标签引用（防止过期指针）。"""
        if self._left_hand_rotation_label is not None and isValid(self._left_hand_rotation_label):
            return self._left_hand_rotation_label
        if self._left_hand_rotation_label is not None:
            print("[CalibDebug] leftHandRotationLabel 已失效，重新查询")
            self._left_hand_rotation_label = None

        self._left_hand_rotation_label = self._find_child_from_self(QLabel, "leftHandRotationLabel")
        if self._left_hand_rotation_label is None:
            self._debug_snapshot("resolve_left_hand_rotation_label_failed")
            raise RuntimeError("无法找到 leftHandRotationLabel 控件")
        self._debug_widget_state("resolved_left_hand_rotation_label", self._left_hand_rotation_label)
        return self._left_hand_rotation_label

    def _resolve_left_hand_quat_label(self) -> QLabel:
        """安全地获取左手四元数标签引用（防止过期指针）。"""
        if self._left_hand_quat_label is not None and isValid(self._left_hand_quat_label):
            return self._left_hand_quat_label
        if self._left_hand_quat_label is not None:
            print("[CalibDebug] leftHandQuatLabel 已失效，重新查询")
            self._left_hand_quat_label = None

        self._left_hand_quat_label = self._find_child_from_self(QLabel, "leftHandQuatLabel")
        if self._left_hand_quat_label is None:
            self._debug_snapshot("resolve_left_hand_quat_label_failed")
            raise RuntimeError("无法找到 leftHandQuatLabel 控件")
        self._debug_widget_state("resolved_left_hand_quat_label", self._left_hand_quat_label)
        return self._left_hand_quat_label

    def _apply_left_hand_attitude_display_mode(self) -> None:
        """应用左手姿态显示模式，只显示四元数或欧拉角其中之一。"""
        rotation_label = self._resolve_left_hand_rotation_label()
        quat_label = self._resolve_left_hand_quat_label()
        rotation_label.setVisible(not self._left_hand_show_quat)
        quat_label.setVisible(self._left_hand_show_quat)

    def _set_label_text_with_retry(
        self,
        resolve_label,
        cache_attr_name: str,
        text: str,
    ) -> QLabel:
        """设置标签文本；若 Qt 底层对象已销毁，则重新查找后重试一次。"""
        label = resolve_label()
        try:
            label.setText(text)
            return label
        except RuntimeError as exc:
            print(f"[CalibDebug] {cache_attr_name} setText 失败，准备重试: {exc}")
            setattr(self, cache_attr_name, None)
            label = resolve_label()
            label.setText(text)
            return label

    def _on_left_hand_attitude_context_menu(self, pos) -> None:
        """左手姿态行右键菜单，切换四元数/欧拉角显示。"""
        menu = QMenu(self)

        euler_action = menu.addAction("显示欧拉角" if self._left_hand_show_quat else "✓ 显示欧拉角")
        quat_action = menu.addAction("✓ 显示四元数" if self._left_hand_show_quat else "显示四元数")

        action = menu.exec(QCursor.pos())
        if action == euler_action:
            self._left_hand_show_quat = False
            self._apply_left_hand_attitude_display_mode()
        elif action == quat_action:
            self._left_hand_show_quat = True
            self._apply_left_hand_attitude_display_mode()

    def _resolve_right_hand_position_label(self) -> QLabel:
        """安全地获取右手位置标签引用（防止过期指针）。"""
        if self._right_hand_position_label is not None and isValid(self._right_hand_position_label):
            return self._right_hand_position_label
        if self._right_hand_position_label is not None:
            print("[CalibDebug] rightHandPositionLabel 已失效，重新查询")
            self._right_hand_position_label = None

        self._right_hand_position_label = self._find_child_from_self(QLabel, "rightHandPositionLabel")
        if self._right_hand_position_label is None:
            self._debug_snapshot("resolve_right_hand_position_label_failed")
            raise RuntimeError("无法找到 rightHandPositionLabel 控件")
        self._debug_widget_state("resolved_right_hand_position_label", self._right_hand_position_label)
        return self._right_hand_position_label

    def _resolve_right_hand_rotation_label(self) -> QLabel:
        """安全地获取右手旋转标签引用（防止过期指针）。"""
        if self._right_hand_rotation_label is not None and isValid(self._right_hand_rotation_label):
            return self._right_hand_rotation_label
        if self._right_hand_rotation_label is not None:
            print("[CalibDebug] rightHandRotationLabel 已失效，重新查询")
            self._right_hand_rotation_label = None

        self._right_hand_rotation_label = self._find_child_from_self(QLabel, "rightHandRotationLabel")
        if self._right_hand_rotation_label is None:
            self._debug_snapshot("resolve_right_hand_rotation_label_failed")
            raise RuntimeError("无法找到 rightHandRotationLabel 控件")
        self._debug_widget_state("resolved_right_hand_rotation_label", self._right_hand_rotation_label)
        return self._right_hand_rotation_label

    def _resolve_right_hand_quat_label(self) -> QLabel:
        """安全地获取右手四元数标签引用（防止过期指针）。"""
        if self._right_hand_quat_label is not None and isValid(self._right_hand_quat_label):
            return self._right_hand_quat_label
        if self._right_hand_quat_label is not None:
            print("[CalibDebug] rightHandQuatLabel 已失效，重新查询")
            self._right_hand_quat_label = None

        self._right_hand_quat_label = self._find_child_from_self(QLabel, "rightHandQuatLabel")
        if self._right_hand_quat_label is None:
            self._debug_snapshot("resolve_right_hand_quat_label_failed")
            raise RuntimeError("无法找到 rightHandQuatLabel 控件")
        self._debug_widget_state("resolved_right_hand_quat_label", self._right_hand_quat_label)
        return self._right_hand_quat_label

    def _apply_right_hand_attitude_display_mode(self) -> None:
        """应用右手姿态显示模式，只显示四元数或欧拉角其中之一。"""
        rotation_label = self._resolve_right_hand_rotation_label()
        quat_label = self._resolve_right_hand_quat_label()
        rotation_label.setVisible(not self._right_hand_show_quat)
        quat_label.setVisible(self._right_hand_show_quat)

    def _on_right_hand_attitude_context_menu(self, pos) -> None:
        """右手姿态行右键菜单，切换四元数/欧拉角显示。"""
        menu = QMenu(self)

        euler_action = menu.addAction("显示欧拉角" if self._right_hand_show_quat else "✓ 显示欧拉角")
        quat_action = menu.addAction("✓ 显示四元数" if self._right_hand_show_quat else "显示四元数")

        action = menu.exec(QCursor.pos())
        if action == euler_action:
            self._right_hand_show_quat = False
            self._apply_right_hand_attitude_display_mode()
        elif action == quat_action:
            self._right_hand_show_quat = True
            self._apply_right_hand_attitude_display_mode()

    def _on_calibration_clicked(self):
        """处理标定按钮点击事件。
        
        获取左手 tracker 当前位置，取反后作为位置偏差，
        并应用到所有 tracker 和 lighthouse。
        """
        print("[CalibDebug] 标定按钮被点击！")
        self._debug_snapshot("before_calibration_click")
        
        if self._vive_tracker_widget is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 错误：无法访问 ViveTrackerWidget"
            print(error_msg)
            try:
                self._add_log(error_msg)
            except Exception as e:
                print(f"[CalibDebug] 日志添加失败: {e}")
            return
        
        # 获取左手 tracker 的原始位置
        try:
            with self._vive_tracker_widget._data_lock:
                left_data = self._vive_tracker_widget._left_data
                
                # 获取原始位置（米）
                pos_x = left_data.pos_origin_x_m
                pos_y = left_data.pos_origin_y_m
                pos_z = left_data.pos_origin_z_m
                
                # 检查数据是否有效
                if not left_data.valid:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    warning_msg = f"[{timestamp}] ⚠️ 警告：左手 Tracker 数据无效，无法标定"
                    print(warning_msg)
                    try:
                        self._add_log(warning_msg)
                    except Exception as e:
                        print(f"[CalibDebug] 日志添加失败: {e}")
                    return
                
                # 计算位置偏差（取反）
                bias_x = -pos_x
                bias_y = -pos_y
                bias_z = -pos_z
                print(
                    "[CalibDebug] 计算偏差完成: "
                    f"origin=({pos_x:.4f}, {pos_y:.4f}, {pos_z:.4f}) "
                    f"bias=({bias_x:.4f}, {bias_y:.4f}, {bias_z:.4f})"
                )
                
                raw_quat_wxyz = (
                    left_data.quat_origin_w,
                    left_data.quat_origin_x,
                    left_data.quat_origin_y,
                    left_data.quat_origin_z,
                )
                location_bias_quat_wxyz = self._build_y_axis_quaternion_wxyz(left_data.pitch)
                tracker_cali_manager = self._vive_tracker_widget.get_tracker_cali_manager()
                additional_quat_wxyz = tracker_cali_manager.get_additional_quaternion_wxyz()
                calibration_quat_wxyz = raw_quat_wxyz
                calibrated_current_quat_wxyz = self._vive_tracker_widget.compose_display_quaternion_wxyz(
                    additional_quat_wxyz,
                    calibration_quat_wxyz,
                    raw_quat_wxyz,
                )

                # 设置左手 tracker 的位置偏差
                tracker_cali_manager.set_position_bias_xyz((bias_x, bias_y, bias_z))
                left_data.quat_calibration_w = calibration_quat_wxyz[0]
                left_data.quat_calibration_x = calibration_quat_wxyz[1]
                left_data.quat_calibration_y = calibration_quat_wxyz[2]
                left_data.quat_calibration_z = calibration_quat_wxyz[3]
                tracker_cali_manager.set_location_bias_quaternion_wxyz(location_bias_quat_wxyz)
                self._vive_tracker_widget.set_calibration_active(True)
                
                # 同时为右手 tracker 应用相同的标定四元数（使用右手原始四元数）
                right_data = self._vive_tracker_widget._right_data
                if right_data.valid:
                    right_raw_quat_wxyz = (
                        right_data.quat_origin_w,
                        right_data.quat_origin_x,
                        right_data.quat_origin_y,
                        right_data.quat_origin_z,
                    )
                    right_calibration_quat_wxyz = right_raw_quat_wxyz
                    right_data.quat_calibration_w = right_calibration_quat_wxyz[0]
                    right_data.quat_calibration_x = right_calibration_quat_wxyz[1]
                    right_data.quat_calibration_y = right_calibration_quat_wxyz[2]
                    right_data.quat_calibration_z = right_calibration_quat_wxyz[3]
                    print(
                        "[CalibDebug] 右手 Tracker 标定四元数已设置: "
                        f"quat=({right_calibration_quat_wxyz[0]:.4f}, {right_calibration_quat_wxyz[1]:.4f}, "
                        f"{right_calibration_quat_wxyz[2]:.4f}, {right_calibration_quat_wxyz[3]:.4f})"
                    )
                
                # 获取所有 lighthouse，应用相同的偏差
                lighthouse_manager = self._vive_tracker_widget._lighthouse_manager
                all_lighthouses = lighthouse_manager.get_all_lighthouses()
                
                for lighthouse_name, lighthouse_data in all_lighthouses.items():
                    # 对所有 lighthouse 应用相同的位置偏差
                    lighthouse_data.update_position_bias(bias_x, bias_y, bias_z)
            
            # 记录标定完成
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            calibration_msg = (
                f"[{timestamp}] ✅ 标定完成\n"
                f"  左手 Tracker 原始位置: X={pos_x:.4f}m, Y={pos_y:.4f}m, Z={pos_z:.4f}m\n"
                f"  左手 Tracker Y 轴欧拉角: {left_data.yaw:.4f}°\n"
                f"  左手 Tracker 原始四元数: {self._format_quaternion_wxyz(raw_quat_wxyz)}\n"
                f"  标定四元数: {self._format_quaternion_wxyz(calibration_quat_wxyz)}\n"
                f"  位置偏移四元数: {self._format_quaternion_wxyz(location_bias_quat_wxyz)}\n"
                f"  标定后当前四元数: {self._format_quaternion_wxyz(calibrated_current_quat_wxyz)}\n"
                f"  应用的位置偏差: X={bias_x:.4f}m, Y={bias_y:.4f}m, Z={bias_z:.4f}m\n"
                f"  已应用到: 左手 Tracker + 右手 Tracker + {len(all_lighthouses)} 个 Lighthouse\n"
                f"  效果: 所有设备虚拟位置已设置为原点，后续运动相对于原点"
            )
            print(calibration_msg)
            print(f"[CalibDebug] calibration_msg_len={len(calibration_msg)}")
            
            # 添加日志
            try:
                self._add_log(calibration_msg)
            except Exception as e:
                print(f"[CalibDebug] 日志添加失败（非致命）: {e}")
            
            # 更新状态标签
            try:
                print("[CalibDebug] 准备更新标定信息标签...")
                
                if not isValid(self):
                    print("[CalibDebug] ⚠️ CalibrationWidget 本体已失效，跳过标签更新（标定已应用）")
                    return
                
                bias_label = self._ensure_bias_value_label()
                
                # 显示位置偏差信息
                bias_info = self._build_calibration_info_text(
                    (bias_x, bias_y, bias_z),
                    calibration_quat_wxyz,
                    additional_quat_wxyz,
                    location_bias_quat_wxyz,
                )
                
                print(f"[CalibDebug] 设置 biasValueLabel 为: {bias_info}")
                bias_label.setText(bias_info)
                print(f"[CalibDebug] biasValueLabel 现在的文本: {bias_label.text()}")
                print(f"[CalibDebug] biasValueLabel 可见: {bias_label.isVisible()}")
                print(f"[CalibDebug] biasValueLabel 启用: {bias_label.isEnabled()}")
                
                # 强制更新
                bias_label.update()
                print("[CalibDebug] 标定信息标签已更新并强制刷新")
                self._debug_snapshot("after_calibration_label_update")
                
            except RuntimeError as e:
                print(f"[CalibDebug] ⚠️ 标签更新失败（UI 可能已被删除）: {e}")
                # UI 已删除但标定已应用，这不是严重错误
            except Exception as e:
                print(f"[CalibDebug] ❌ 状态标签更新失败: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 标定失败：{e}"
            print(error_msg)
            try:
                self._add_log(error_msg)
            except Exception as log_err:
                print(f"[CalibDebug] 日志添加失败: {log_err}")
            import traceback
            traceback.print_exc()

    def _on_cancel_calibration_clicked(self):
        """处理取消标定按钮点击事件。
        
        将所有 tracker 和 lighthouse 的位置偏差都重置为 0。
        """
        print("[CalibDebug] 取消标定按钮被点击！")
        self._debug_snapshot("before_cancel_calibration")
        
        if self._vive_tracker_widget is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 错误：无法访问 ViveTrackerWidget"
            print(error_msg)
            try:
                self._add_log(error_msg)
            except Exception as e:
                print(f"[CalibDebug] 日志添加失败: {e}")
            return
        
        try:
            with self._vive_tracker_widget._data_lock:
                # 重置左手 tracker 的位置偏差
                left_data = self._vive_tracker_widget._left_data
                self._vive_tracker_widget.get_tracker_cali_manager().set_position_bias_xyz((0.0, 0.0, 0.0))
                left_data.quat_calibration_w = 1.0
                left_data.quat_calibration_x = 0.0
                left_data.quat_calibration_y = 0.0
                left_data.quat_calibration_z = 0.0
                
                # 重置右手 tracker 的标定四元数
                right_data = self._vive_tracker_widget._right_data
                right_data.quat_calibration_w = 1.0
                right_data.quat_calibration_x = 0.0
                right_data.quat_calibration_y = 0.0
                right_data.quat_calibration_z = 0.0
                
                self._vive_tracker_widget.set_calibration_active(False)
                
                # 重置所有 lighthouse 的位置偏差
                lighthouse_manager = self._vive_tracker_widget._lighthouse_manager
                all_lighthouses = lighthouse_manager.get_all_lighthouses()
                
                for lighthouse_name, lighthouse_data in all_lighthouses.items():
                    lighthouse_data.update_position_bias(0.0, 0.0, 0.0)
            
            # 记录取消标定完成
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cancel_msg = (
                f"[{timestamp}] ✅ 取消标定完成\n"
                f"  已重置: 左手 Tracker + 右手 Tracker + {len(all_lighthouses)} 个 Lighthouse\n"
                f"  所有设备位置偏差已恢复为 0"
            )
            print(cancel_msg)
            print(f"[CalibDebug] cancel_msg_len={len(cancel_msg)}")
            
            # 添加日志
            try:
                self._add_log(cancel_msg)
            except Exception as e:
                print(f"[CalibDebug] 日志添加失败（非致命）: {e}")
            
            # 更新状态标签
            try:
                print("[CalibDebug] 准备更新标定信息标签（重置）...")
                
                if not isValid(self):
                    print("[CalibDebug] ⚠️ CalibrationWidget 本体已失效，跳过标签更新（标定已重置）")
                    return
                
                bias_label = self._ensure_bias_value_label()
                
                # 重置为初始状态
                reset_info = self._build_calibration_info_text(
                    None,
                    (1.0, 0.0, 0.0, 0.0),
                    self._vive_tracker_widget.get_tracker_cali_manager().get_additional_quaternion_wxyz(),
                    self._vive_tracker_widget.get_tracker_cali_manager().get_location_bias_quaternion_wxyz(),
                )
                
                print(f"[CalibDebug] 设置 biasValueLabel 为: {reset_info}")
                bias_label.setText(reset_info)
                print(f"[CalibDebug] biasValueLabel 现在的文本: {bias_label.text()}")
                print(f"[CalibDebug] biasValueLabel 可见: {bias_label.isVisible()}")
                
                # 强制更新
                bias_label.update()
                print("[CalibDebug] 标定信息标签已重置")
                self._debug_snapshot("after_cancel_label_update")
                
            except RuntimeError as e:
                print(f"[CalibDebug] ⚠️ 标签更新失败（UI 可能已被删除）: {e}")
                # UI 已删除但标定已重置，这不是严重错误
            except Exception as e:
                print(f"[CalibDebug] ❌ 状态标签更新失败: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 取消标定失败：{e}"
            print(error_msg)
            try:
                self._add_log(error_msg)
            except Exception as log_err:
                print(f"[CalibDebug] 日志添加失败: {log_err}")
            import traceback
            traceback.print_exc()

    def _add_log(self, message: str):
        """添加日志信息到日志显示区域（线程安全）。
        
        Args:
            message: 要添加的日志信息
        
        若 UI 已被删除，仅输出到控制台而不抛出异常。
        """
        try:
            if not isValid(self):
                print(f"[CalibDebug] ⚠️ CalibrationWidget 已失效，无法添加日志: {message}")
                return
            
            log_text = self._resolve_log_text()
            # 临时禁用只读模式，以便添加日志
            was_read_only = log_text.isReadOnly()
            if was_read_only:
                log_text.setReadOnly(False)
            
            log_text.moveCursor(QTextCursor.End)
            log_text.insertPlainText(f"{message}\n")
            log_text.moveCursor(QTextCursor.End)
            
            # 恢复只读模式
            if was_read_only:
                log_text.setReadOnly(True)
            
            log_length = len(log_text.toPlainText())
            print(f"[CalibDebug] 日志已添加: {message}")
            print(f"[CalibDebug] log_text_total_len={log_length}")
        except RuntimeError as e:
            print(f"[CalibDebug] ⚠️ 日志添加失败（Qt 对象失效）: {message}")
            print(f"[CalibDebug] add_log_runtime_error={e}")
            self._debug_snapshot("add_log_runtime_error")
        except Exception as e:
            print(f"[CalibDebug] 日志添加失败: {e}")
            import traceback
            traceback.print_exc()

    def _update_left_hand_info(self):
        """更新左手信息显示（10Hz 刷新）。
        
        从 ViveTrackerWidget 中获取左手追踪器的标定后位置和四元数，
        并更新"左手信息"面板中的三个标签。
        """
        if self._vive_tracker_widget is None:
            print("[CalibDebug] _update_left_hand_info: vive_tracker_widget is None")
            return
        
        try:
            self._left_hand_info_tick += 1
            with self._vive_tracker_widget._data_lock:
                left_data = self._vive_tracker_widget._left_data
                tracking_enabled = self._vive_tracker_widget.is_tracking_enabled()
                if self._left_hand_info_tick <= 5 or self._left_hand_info_tick % 20 == 0:
                    tracker_cali_state = self._vive_tracker_widget.get_tracker_cali_manager().get_state_snapshot()
                    print(
                        "[CalibDebug] left_info_tick="
                        f"{self._left_hand_info_tick} tracking={tracking_enabled} valid={left_data.valid} "
                        f"origin=({left_data.pos_origin_x_m:.4f}, {left_data.pos_origin_y_m:.4f}, {left_data.pos_origin_z_m:.4f}) "
                        f"bias=({tracker_cali_state.pos_bias_x_m:.4f}, {tracker_cali_state.pos_bias_y_m:.4f}, {tracker_cali_state.pos_bias_z_m:.4f}) "
                        f"quat_origin=({left_data.quat_origin_w:.4f}, {left_data.quat_origin_x:.4f}, {left_data.quat_origin_y:.4f}, {left_data.quat_origin_z:.4f}) "
                        f"quat_calib=({left_data.quat_calibration_w:.4f}, {left_data.quat_calibration_x:.4f}, {left_data.quat_calibration_y:.4f}, {left_data.quat_calibration_z:.4f}) "
                        f"quat_add=({tracker_cali_state.quat_additional_w:.4f}, {tracker_cali_state.quat_additional_x:.4f}, {tracker_cali_state.quat_additional_y:.4f}, {tracker_cali_state.quat_additional_z:.4f})"
                    )
                if not left_data.valid:
                    if self._left_hand_info_tick <= 5 or self._left_hand_info_tick % 20 == 0:
                        print("[CalibDebug] _update_left_hand_info: left_data.valid is False, skip UI update")
                    return

                # 计算标定后的位置（原始位置 + 偏差，并按需应用 quat_calibration 旋转）
                final_x, final_y, final_z = self._vive_tracker_widget.compose_tracker_data_display_position_xyz(left_data)

                calibrated_quat = self._vive_tracker_widget.compose_tracker_data_display_quaternion_wxyz(left_data)
                euler_degree = tuple(quat_to_euler_degree(list(calibrated_quat), _EULER_ORDER_ZXY))
            
            # 更新位置标签
            pos_text = f"位置：X={final_x:8.4f}m  Y={final_y:8.4f}m  Z={final_z:8.4f}m"
            self._set_label_text_with_retry(self._resolve_left_hand_position_label, "_left_hand_position_label", pos_text)
            
            # 更新旋转标签（由当前显示的四元数换算，顺序固定为 ZXY）
            rot_text = self._format_euler_zxy_text(euler_degree)
            self._set_label_text_with_retry(self._resolve_left_hand_rotation_label, "_left_hand_rotation_label", rot_text)
            
            # 更新四元数标签
            quat_text = (
                f"四元数：w={calibrated_quat[0]:8.4f}  x={calibrated_quat[1]:8.4f}  "
                f"y={calibrated_quat[2]:8.4f}  z={calibrated_quat[3]:8.4f}"
            )
            self._set_label_text_with_retry(self._resolve_left_hand_quat_label, "_left_hand_quat_label", quat_text)
            self._apply_left_hand_attitude_display_mode()

            if self._left_hand_info_tick <= 5 or self._left_hand_info_tick % 20 == 0:
                print(
                    "[CalibDebug] left_info_ui_updated: "
                    f"pos=({final_x:.4f}, {final_y:.4f}, {final_z:.4f}) "
                    f"quat=({calibrated_quat[0]:.4f}, {calibrated_quat[1]:.4f}, {calibrated_quat[2]:.4f}, {calibrated_quat[3]:.4f}) "
                    f"euler_zxy=({euler_degree[2]:.2f}, {euler_degree[0]:.2f}, {euler_degree[1]:.2f})"
                )
        except Exception as e:
            print(f"[CalibDebug] 更新左手信息失败: {e}")
    
    def _update_right_hand_info(self):
        """更新右手信息显示（10Hz 刷新）。
        
        从 ViveTrackerWidget 中获取右手追踪器的标定后位置和四元数，
        并更新"右手信息"面板中的三个标签。
        """
        if self._vive_tracker_widget is None:
            print("[CalibDebug] _update_right_hand_info: vive_tracker_widget is None")
            return
        
        try:
            self._right_hand_info_tick += 1
            with self._vive_tracker_widget._data_lock:
                right_data = self._vive_tracker_widget._right_data
                tracking_enabled = self._vive_tracker_widget.is_tracking_enabled()
                if self._right_hand_info_tick <= 5 or self._right_hand_info_tick % 20 == 0:
                    tracker_cali_state = self._vive_tracker_widget.get_tracker_cali_manager().get_state_snapshot()
                    print(
                        "[CalibDebug] right_info_tick="
                        f"{self._right_hand_info_tick} tracking={tracking_enabled} valid={right_data.valid} "
                        f"origin=({right_data.pos_origin_x_m:.4f}, {right_data.pos_origin_y_m:.4f}, {right_data.pos_origin_z_m:.4f}) "
                        f"bias=({tracker_cali_state.pos_bias_x_m:.4f}, {tracker_cali_state.pos_bias_y_m:.4f}, {tracker_cali_state.pos_bias_z_m:.4f}) "
                        f"quat_origin=({right_data.quat_origin_w:.4f}, {right_data.quat_origin_x:.4f}, {right_data.quat_origin_y:.4f}, {right_data.quat_origin_z:.4f}) "
                        f"quat_calib=({right_data.quat_calibration_w:.4f}, {right_data.quat_calibration_x:.4f}, {right_data.quat_calibration_y:.4f}, {right_data.quat_calibration_z:.4f}) "
                        f"quat_add=({tracker_cali_state.quat_additional_w:.4f}, {tracker_cali_state.quat_additional_x:.4f}, {tracker_cali_state.quat_additional_y:.4f}, {tracker_cali_state.quat_additional_z:.4f})"
                    )
                if not right_data.valid:
                    if self._right_hand_info_tick <= 5 or self._right_hand_info_tick % 20 == 0:
                        print("[CalibDebug] _update_right_hand_info: right_data.valid is False, skip UI update")
                    return

                # 计算标定后的位置（原始位置 + 偏差，并按需应用 quat_calibration 旋转）
                final_x, final_y, final_z = self._vive_tracker_widget.compose_tracker_data_display_position_xyz(right_data)

                calibrated_quat = self._vive_tracker_widget.compose_tracker_data_display_quaternion_wxyz(right_data)
                euler_degree = tuple(quat_to_euler_degree(list(calibrated_quat), _EULER_ORDER_ZXY))
            
            # 更新位置标签
            pos_text = f"位置：X={final_x:8.4f}m  Y={final_y:8.4f}m  Z={final_z:8.4f}m"
            self._set_label_text_with_retry(self._resolve_right_hand_position_label, "_right_hand_position_label", pos_text)
            
            # 更新旋转标签（由当前显示的四元数换算，顺序固定为 ZXY）
            rot_text = self._format_euler_zxy_text(euler_degree)
            self._set_label_text_with_retry(self._resolve_right_hand_rotation_label, "_right_hand_rotation_label", rot_text)
            
            # 更新四元数标签
            quat_text = (
                f"四元数：w={calibrated_quat[0]:8.4f}  x={calibrated_quat[1]:8.4f}  "
                f"y={calibrated_quat[2]:8.4f}  z={calibrated_quat[3]:8.4f}"
            )
            self._set_label_text_with_retry(self._resolve_right_hand_quat_label, "_right_hand_quat_label", quat_text)
            self._apply_right_hand_attitude_display_mode()

            if self._right_hand_info_tick <= 5 or self._right_hand_info_tick % 20 == 0:
                print(
                    "[CalibDebug] right_info_ui_updated: "
                    f"pos=({final_x:.4f}, {final_y:.4f}, {final_z:.4f}) "
                    f"quat=({calibrated_quat[0]:.4f}, {calibrated_quat[1]:.4f}, {calibrated_quat[2]:.4f}, {calibrated_quat[3]:.4f}) "
                    f"euler_zxy=({euler_degree[2]:.2f}, {euler_degree[0]:.2f}, {euler_degree[1]:.2f})"
                )
        except Exception as e:
            print(f"[CalibDebug] 更新右手信息失败: {e}")
    
    def cleanup(self):
        """清理资源，停止定时器。"""
        if self._left_hand_info_timer.isActive():
            self._left_hand_info_timer.stop()
        if self._right_hand_info_timer.isActive():
            self._right_hand_info_timer.stop()


class ViveTrackerCaliWidget(CalibrationWidget):
    """定位标定面板组件（CalibrationWidget 的包装）。"""

    def __init__(self, vive_tracker_widget=None, parent=None):
        """初始化 Vive Tracker 标定面板。
        
        Args:
            vive_tracker_widget: ViveTrackerWidget 实例
            parent: 父 QWidget
        """
        super().__init__(vive_tracker_widget=vive_tracker_widget, parent=parent)


class CaliTabManager:
    """标定 tab 管理器。"""

    def __init__(self, vive_tracker_widget):
        """初始化标定 tab 管理器。
        
        Args:
            vive_tracker_widget: ViveTrackerWidget 实例，用于传递给标定面板
        """
        self._vive_tracker_widget = vive_tracker_widget
        self._calibration_widget = None
        self._calibration_tab_index = None

    def setup_calibration_tab(self, tab_widget):
        """设置标定 tab 并添加到 QTabWidget。
        
        Args:
            tab_widget: 目标 QTabWidget
        
        Returns:
            ViveTrackerCaliWidget 实例
        """
        self._calibration_widget = ViveTrackerCaliWidget(vive_tracker_widget=self._vive_tracker_widget)
        self._calibration_tab_index = tab_widget.addTab(self._calibration_widget, "定位标定")
        tab_widget.setTabEnabled(self._calibration_tab_index, True)
        return self._calibration_widget

    def enable_calibration_tab(self, tab_widget):
        """启用标定 tab 内部控件。
        
        Args:
            tab_widget: QTabWidget 实例（用于一致性，此方法主要作用于内部标定面板）
        """
        if self._calibration_widget is not None:
            self._calibration_widget.set_tracking_controls_enabled(True)

    def disable_calibration_tab(self, tab_widget):
        """禁用标定 tab 内部控件。
        
        Args:
            tab_widget: QTabWidget 实例（用于一致性，此方法主要作用于内部标定面板）
        """
        if self._calibration_widget is not None:
            self._calibration_widget.set_tracking_controls_enabled(False)

    def get_calibration_widget(self):
        """获取标定 widget。
        
        Returns:
            ViveTrackerCaliWidget 实例或 None
        """
        return self._calibration_widget

    def get_calibration_tab_index(self):
        """获取标定 tab 索引。
        
        Returns:
            int: 标定 tab 在 QTabWidget 中的索引，若未设置则为 None
        """
        return self._calibration_tab_index
