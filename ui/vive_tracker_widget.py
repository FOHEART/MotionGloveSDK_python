"""vive_tracker_widget.py
Vive Tracker 配置显示和追踪面板

功能：
- 从 triad_openvr/hand_tracker_config.json 读取配置
- 初始化 OpenVR 系统
- 后台线程以 60Hz 读取追踪数据
- UI 以 60Hz 刷新显示位置和旋转信息

UI 布局定义在 vive_tracker.ui 文件中，可用 Qt Designer 编辑。
"""

import sys
import json
import threading
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton, QTextEdit, QLineEdit, QFrame, QTabWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu

# 导入 SteamVR 状态检查器
from triad_openvr.steamvr_status_checker import SteamVRStatusChecker

# 导入 Tracker 管理器和追踪数据类
from triad_openvr.tracker_manager import ViveTrackerMgr, TrackerManager, TrackerData, get_global_tracker_manager

# 导入 LightHouse 管理器
from triad_openvr.lighthouse_manager import LighthouseManager, get_global_lighthouse_manager

# 导入标定 widget
from calibration_widget import CalibrationWidget


def _find_ui_file() -> Path:
    """查找 vive_tracker.ui 文件的路径。"""
    candidates = [
        Path(__file__).parent / "vive_tracker.ui",
        Path(__file__).parent.parent / "ui" / "vive_tracker.ui",
        Path.cwd() / "ui" / "vive_tracker.ui",
    ]
    
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(2, Path(meipass) / "ui" / "vive_tracker.ui")
        candidates.insert(3, Path(meipass) / "_internal" / "ui" / "vive_tracker.ui")
    
    try:
        exe_dir = Path(sys.executable).parent
        candidates.insert(len(candidates) - 1, exe_dir / "ui" / "vive_tracker.ui")
        candidates.insert(len(candidates) - 1, exe_dir / "_internal" / "ui" / "vive_tracker.ui")
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
            for p in root.rglob("vive_tracker.ui"):
                return p
        except Exception:
            continue
    
    return candidates[0]


def _find_config_file() -> Path:
    """查找 hand_tracker_config.json 文件的路径。"""
    candidates = [
        Path(__file__).parent.parent / "triad_openvr" / "hand_tracker_config.json",
        Path(__file__).parent.parent / "hand_tracker_config.json",
        Path.cwd() / "triad_openvr" / "hand_tracker_config.json",
        Path.cwd() / "hand_tracker_config.json",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    # 未找到文件，返回第一个候选路径（便于错误提示）
    return candidates[0]




class ViveTrackerWidget(QWidget):
    """Vive Tracker 配置显示和追踪面板。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 追踪器管理器（存储所有 Tracker 的统一信息）
        self._tracker_manager: TrackerManager = get_global_tracker_manager()
        
        # LightHouse 管理器（存储所有 LightHouse 基站的统一信息）
        self._lighthouse_manager: LighthouseManager = get_global_lighthouse_manager()

        # 追踪状态
        self._tracking_enabled = False
        self._config = {}
        self._left_data = TrackerData()
        self._right_data = TrackerData()
        self._openvr_system = None
        self._devices = {}
        self._tracking_thread = None
        self._thread_stop_event = threading.Event()
        self._data_lock = threading.RLock()
        
        # Tracker 在线状态追踪（用于检测状态变化）
        self._left_online_state = False
        self._right_online_state = False
        # Tracker 离线计数器（连续20帧无数据才判定为离线）
        self._left_offline_counter = 0
        self._right_offline_counter = 0
        self._offline_threshold = 20  # 连续帧数阈值
        
        # 显示模式（True 表示显示四元数，False 表示显示欧拉角）
        self._left_show_quat = False
        self._right_show_quat = False
        
        # 模型加载/卸载回调（外部可以设置这些来响应模型状态变化）
        self._model_load_callback = None  # 回调签名：(side: str, renderer) -> None
        self._model_unload_callback = None  # 回调签名：(side: str, renderer) -> None
        self._lighthouse_update_callback = None  # 回调签名：(list[dict]) -> None
        self._tracking_state_changed_callback = None  # 回调签名：(enabled: bool) -> None
        self._render_request_callback = None  # 回调签名：() -> None
        self._renderer = None  # VTK 渲染器引用
        
        # 模型对象引用（用于跟踪已加载的模型）
        self._tracker_model_actors = {}  # {"left": VRTrackerModelActor, "right": VRTrackerModelActor}
        self._tracker_axes_actors = {}   # {"left": vtkPropAssembly, "right": vtkPropAssembly}
        self._lighthouse_model_actors = {}  # {lighthouse_name: LighthouseModelActor}
        
        # ── VTK 对象缓存（避免每帧新建） ────────────────────
        self._axes_transform_cache = {}  # {"left": vtkTransform, "right": vtkTransform}
        self._axes_matrix_cache = {}     # {"left": vtkMatrix4x4, "right": vtkMatrix4x4}
        # 记录最后一次坐标轴更新的位置和四元数，用于变化检测
        self._last_axes_pose = {}        # {"left": (pos, quat), "right": (pos, quat)}
        
        self._init_ui()
        self._load_config()
        
        # SteamVR 状态检查器（独立运行，1秒检查一次）
        self._steamvr_checker = SteamVRStatusChecker(check_interval=1000)
        self._steamvr_checker.set_status_changed_callback(self._on_steamvr_status_changed)
        self._steamvr_checker.start()
        
        # UI 更新定时器（60Hz，仅在追踪时运行）
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_update_timer)
        self._update_timer.setInterval(17)  # ~60Hz
        
        # LightHouse 信息更新定时器（1Hz，与 SteamVR 检测频率相同）
        self._lighthouse_update_timer = QTimer()
        self._lighthouse_update_timer.timeout.connect(self._update_light_house_info)
        self._lighthouse_update_timer.setInterval(1000)  # 1Hz

    def _init_ui(self):
        """从 UI 文件加载界面，并添加标定 tab。"""
        loader = QUiLoader()
        ui_file = QFile(str(_find_ui_file()))
        
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_find_ui_file()}")
        
        self._ui = loader.load(ui_file)
        ui_file.close()
        
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_find_ui_file()}")
        
        # 创建主布局和 TabWidget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建 TabWidget
        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)
        
        # 第一个 tab：追踪信息（原有的 UI）
        tracker_tab = QWidget()
        tracker_layout = QVBoxLayout(tracker_tab)
        tracker_layout.setContentsMargins(0, 0, 0, 0)
        tracker_layout.addWidget(self._ui)
        self._tab_widget.addTab(tracker_tab, "追踪信息")
        
        # 第二个 tab：定位标定
        self._calibration_widget = CalibrationWidget()
        self._calibration_tab_index = self._tab_widget.addTab(self._calibration_widget, "定位标定")
        
        # 默认禁用定位标定 tab（只有追踪成功开启后才启用）
        self._tab_widget.setTabEnabled(self._calibration_tab_index, False)
        
        # 获取 UI 中的控件
        self._left_config_label: QLabel = self._ui.findChild(QLabel, "leftHandConfigInfo")
        self._right_config_label: QLabel = self._ui.findChild(QLabel, "rightHandConfigInfo")
        self._left_position_label: QLabel = self._ui.findChild(QLabel, "leftHandPositionLabel")
        self._right_position_label: QLabel = self._ui.findChild(QLabel, "rightHandPositionLabel")
        self._left_rotation_label: QLabel = self._ui.findChild(QLabel, "leftHandRotationLabel")
        self._right_rotation_label: QLabel = self._ui.findChild(QLabel, "rightHandRotationLabel")
        self._left_quat_label: QLabel = self._ui.findChild(QLabel, "leftHandQuatLabel")
        self._right_quat_label: QLabel = self._ui.findChild(QLabel, "rightHandQuatLabel")
        self._start_tracking_btn: QPushButton = self._ui.findChild(QPushButton, "startTrackingButton")
        self._refresh_btn: QPushButton = self._ui.findChild(QPushButton, "refreshButton")
        self._left_group: QGroupBox = self._ui.findChild(QGroupBox, "leftHandGroup")
        self._right_group: QGroupBox = self._ui.findChild(QGroupBox, "rightHandGroup")
        self._connection_status_text: QTextEdit = self._ui.findChild(QTextEdit, "connectionStatusText")
        self._steamvr_status_label: QLabel = self._ui.findChild(QLabel, "steamvrStatusLabel")
        
        # 验证所有必要的控件存在
        assert self._left_config_label is not None, "UI 控件未找到：leftHandConfigInfo"
        assert self._right_config_label is not None, "UI 控件未找到：rightHandConfigInfo"
        assert self._left_position_label is not None, "UI 控件未找到：leftHandPositionLabel"
        assert self._right_position_label is not None, "UI 控件未找到：rightHandPositionLabel"
        assert self._left_rotation_label is not None, "UI 控件未找到：leftHandRotationLabel"
        assert self._right_rotation_label is not None, "UI 控件未找到：rightHandRotationLabel"
        assert self._left_quat_label is not None, "UI 控件未找到：leftHandQuatLabel"
        assert self._right_quat_label is not None, "UI 控件未找到：rightHandQuatLabel"
        assert self._start_tracking_btn is not None, "UI 控件未找到：startTrackingButton"
        assert self._connection_status_text is not None, "UI 控件未找到：connectionStatusText"
        assert self._steamvr_status_label is not None, "UI 控件未找到：steamvrStatusLabel"
        
        # 初始化 GroupBox 样式为离线（红色）
        self._set_groupbox_online_status(self._left_group, False)
        self._set_groupbox_online_status(self._right_group, False)
        
        # 默认隐藏四元数标签
        self._left_quat_label.setVisible(False)
        self._right_quat_label.setVisible(False)
        
        # 连接信号
        self._start_tracking_btn.clicked.connect(self._on_start_tracking_clicked)
        
        # 为 GroupBox 设置右键菜单
        self._left_group.setContextMenuPolicy(Qt.CustomContextMenu)
        self._left_group.customContextMenuRequested.connect(self._on_left_group_context_menu)
        
        self._right_group.setContextMenuPolicy(Qt.CustomContextMenu)
        self._right_group.customContextMenuRequested.connect(self._on_right_group_context_menu)
        
        # 初始化位置偏差控件
        self._init_bias_controls()

    def _init_bias_controls(self):
        """初始化位置偏差控件（从 UI 文件加载）。"""
        # 从 UI 中查找左手偏差控件
        self._left_bias_x_edit: QLineEdit = self._ui.findChild(QLineEdit, "leftBiasXEdit")
        self._left_bias_y_edit: QLineEdit = self._ui.findChild(QLineEdit, "leftBiasYEdit")
        self._left_bias_z_edit: QLineEdit = self._ui.findChild(QLineEdit, "leftBiasZEdit")
        left_bias_set_btn: QPushButton = self._ui.findChild(QPushButton, "leftBiasSetBtn")
        
        # 从 UI 中查找右手偏差控件
        self._right_bias_x_edit: QLineEdit = self._ui.findChild(QLineEdit, "rightBiasXEdit")
        self._right_bias_y_edit: QLineEdit = self._ui.findChild(QLineEdit, "rightBiasYEdit")
        self._right_bias_z_edit: QLineEdit = self._ui.findChild(QLineEdit, "rightBiasZEdit")
        right_bias_set_btn: QPushButton = self._ui.findChild(QPushButton, "rightBiasSetBtn")
        
        # 验证所有偏差控件已找到
        assert self._left_bias_x_edit is not None, "UI 控件未找到：leftBiasXEdit"
        assert self._left_bias_y_edit is not None, "UI 控件未找到：leftBiasYEdit"
        assert self._left_bias_z_edit is not None, "UI 控件未找到：leftBiasZEdit"
        assert left_bias_set_btn is not None, "UI 控件未找到：leftBiasSetBtn"
        assert self._right_bias_x_edit is not None, "UI 控件未找到：rightBiasXEdit"
        assert self._right_bias_y_edit is not None, "UI 控件未找到：rightBiasYEdit"
        assert self._right_bias_z_edit is not None, "UI 控件未找到：rightBiasZEdit"
        assert right_bias_set_btn is not None, "UI 控件未找到：rightBiasSetBtn"
        
        # 连接信号
        left_bias_set_btn.clicked.connect(self._on_set_left_bias)
        right_bias_set_btn.clicked.connect(self._on_set_right_bias)

    def _on_set_left_bias(self):
        """处理设置左手偏差按钮点击事件。"""
        try:
            x = float(self._left_bias_x_edit.text())
            y = float(self._left_bias_y_edit.text())
            z = float(self._left_bias_z_edit.text())
            
            with self._data_lock:
                self._left_data.pos_bias_x_m = x
                self._left_data.pos_bias_y_m = y
                self._left_data.pos_bias_z_m = z
            
            print(f"[PosBias] 左手偏差已设置：X={x:.4f}m, Y={y:.4f}m, Z={z:.4f}m")
            
            # 触发场景更新
            if self._renderer is not None and self._mark_scene_dirty is not None:
                self._mark_scene_dirty()
        except ValueError as e:
            print(f"[PosBias] 左手偏差设置失败：无效的数值 - {e}")

    def _on_set_right_bias(self):
        """处理设置右手偏差按钮点击事件。"""
        try:
            x = float(self._right_bias_x_edit.text())
            y = float(self._right_bias_y_edit.text())
            z = float(self._right_bias_z_edit.text())
            
            with self._data_lock:
                self._right_data.pos_bias_x_m = x
                self._right_data.pos_bias_y_m = y
                self._right_data.pos_bias_z_m = z
            
            print(f"[PosBias] 右手偏差已设置：X={x:.4f}m, Y={y:.4f}m, Z={z:.4f}m")
            
            # 触发场景更新
            if self._renderer is not None and self._mark_scene_dirty is not None:
                self._mark_scene_dirty()
        except ValueError as e:
            print(f"[PosBias] 右手偏差设置失败：无效的数值 - {e}")

    def _set_steamvr_status(self, running: bool):
        """更新 SteamVR 状态标签。
        
        Args:
            running: True 表示 SteamVR 已启动，False 表示未启动
        """
        if running:
            self._steamvr_status_label.setText("SteamVR: 已启动")
            self._steamvr_status_label.setStyleSheet(
                "background-color: green; color: white; padding: 2px 8px; border-radius: 3px; font-weight: bold;"
            )
        else:
            self._steamvr_status_label.setText("SteamVR: 未启动")
            self._steamvr_status_label.setStyleSheet(
                "background-color: red; color: white; padding: 2px 8px; border-radius: 3px; font-weight: bold;"
            )

    def _on_steamvr_status_changed(self, running: bool):
        """SteamVR 状态改变回调。
        
        Args:
            running: True 表示 SteamVR 已启动，False 表示未启动
        """
        self._set_steamvr_status(running)

    def _load_config(self):
        """从 JSON 文件加载配置。"""
        config_file = _find_config_file()

        if not config_file.exists():
            error_text = f"<font color='red'><b>配置文件未找到</b></font><br>{config_file}"
            self._left_config_label.setText(error_text)
            self._right_config_label.setText(error_text)
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except Exception as e:
            error_text = f"<font color='red'><b>读取配置失败</b></font><br>{e}"
            self._left_config_label.setText(error_text)
            self._right_config_label.setText(error_text)
            return

        # 更新左手信息
        left_config = self._config.get("LeftHandTracker", {})
        if left_config:
            left_text = self._format_config(left_config)
            self._left_config_label.setText(left_text)
            self._left_group.setEnabled(True)
        else:
            self._left_config_label.setText("<font color='gray'>未配置</font>")
            self._left_group.setEnabled(False)

        # 更新右手信息
        right_config = self._config.get("RightHandTracker", {})
        if right_config:
            right_text = self._format_config(right_config)
            self._right_config_label.setText(right_text)
            self._right_group.setEnabled(True)
        else:
            self._right_config_label.setText("<font color='gray'>未配置</font>")
            self._right_group.setEnabled(False)

    def _format_config(self, config: dict) -> str:
        """将配置字典格式化为显示文本。"""
        lines = []
        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"<b>{key}:</b> {value}")
            elif isinstance(value, dict):
                lines.append(f"<b>{key}:</b>")
                for k, v in value.items():
                    lines.append(f"&nbsp;&nbsp;{k}: {v}")
            else:
                lines.append(f"<b>{key}:</b> {value}")

        return "<br>".join(lines) if lines else "无配置数据"

    def _on_left_group_context_menu(self, pos):
        """左手 GroupBox 的右键菜单。"""
        menu = QMenu(self)
        
        euler_action = menu.addAction("显示欧拉角" if self._left_show_quat else "✓ 显示欧拉角")
        quat_action = menu.addAction("✓ 显示四元数" if self._left_show_quat else "显示四元数")
        
        action = menu.exec(QCursor.pos())
        
        if action == euler_action:
            self._left_show_quat = False
            self._left_rotation_label.setVisible(True)
            self._left_quat_label.setVisible(False)
        elif action == quat_action:
            self._left_show_quat = True
            self._left_rotation_label.setVisible(False)
            self._left_quat_label.setVisible(True)

    def _on_right_group_context_menu(self, pos):
        """右手 GroupBox 的右键菜单。"""
        menu = QMenu(self)
        
        euler_action = menu.addAction("显示欧拉角" if self._right_show_quat else "✓ 显示欧拉角")
        quat_action = menu.addAction("✓ 显示四元数" if self._right_show_quat else "显示四元数")
        
        action = menu.exec(QCursor.pos())
        
        if action == euler_action:
            self._right_show_quat = False
            self._right_rotation_label.setVisible(True)
            self._right_quat_label.setVisible(False)
        elif action == quat_action:
            self._right_show_quat = True
            self._right_rotation_label.setVisible(False)
            self._right_quat_label.setVisible(True)

    def _format_config(self, config: dict) -> str:
        """将配置字典格式化为显示文本。"""
        lines = []
        for key, value in config.items():
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"<b>{key}:</b> {value}")
            elif isinstance(value, dict):
                lines.append(f"<b>{key}:</b>")
                for k, v in value.items():
                    lines.append(f"&nbsp;&nbsp;{k}: {v}")
            else:
                lines.append(f"<b>{key}:</b> {value}")

        return "<br>".join(lines) if lines else "无配置数据"

    def _set_groupbox_online_status(self, groupbox: QGroupBox, is_online: bool):
        """根据在线状态设置 GroupBox 标题背景色。
        
        Args:
            groupbox: 目标 GroupBox
            is_online: True 为在线（绿色），False 为离线（红色）
        """
        if is_online:
            groupbox.setStyleSheet(
                "QGroupBox { border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; padding-top: 10px; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0px 5px; "
                "background-color: green; color: white; font-weight: bold; border-radius: 3px; }"
            )
        else:
            groupbox.setStyleSheet(
                "QGroupBox { border: 1px solid #ccc; border-radius: 4px; margin-top: 10px; padding-top: 10px; }"
                "QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0px 5px; "
                "background-color: red; color: white; font-weight: bold; border-radius: 3px; }"
            )

    def _update_groupbox_status(self, side: str, is_online: bool):
        """更新 GroupBox 状态并打印状态改变信息。同时处理模型加载/卸载。
        
        Args:
            side: "left" 或 "right"
            is_online: 是否在线
        """
        if side == "left":
            if self._left_online_state != is_online:
                self._left_online_state = is_online
                status_str = "上线" if is_online else "离线"
                print(f"[TrackerStatus] 左手 Tracker {status_str}")
                self._set_groupbox_online_status(self._left_group, is_online)
                
                # 处理模型加载/卸载
                if is_online and self._renderer is not None and self._model_load_callback is not None:
                    try:
                        self._model_load_callback("left", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 加载左手模型失败：{e}")
                elif not is_online and self._renderer is not None and self._model_unload_callback is not None:
                    try:
                        self._model_unload_callback("left", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 卸载左手模型失败：{e}")
        elif side == "right":
            if self._right_online_state != is_online:
                self._right_online_state = is_online
                status_str = "上线" if is_online else "离线"
                print(f"[TrackerStatus] 右手 Tracker {status_str}")
                self._set_groupbox_online_status(self._right_group, is_online)
                
                # 处理模型加载/卸载
                if is_online and self._renderer is not None and self._model_load_callback is not None:
                    try:
                        self._model_load_callback("right", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 加载右手模型失败：{e}")
                elif not is_online and self._renderer is not None and self._model_unload_callback is not None:
                    try:
                        self._model_unload_callback("right", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 卸载右手模型失败：{e}")

    def set_renderer_and_callbacks(
        self,
        renderer,
        model_load_callback=None,
        model_unload_callback=None,
        lighthouse_update_callback=None,
        tracking_state_changed_callback=None,
        render_request_callback=None,
    ):
        """设置 VTK 渲染器和模型加载/卸载回调。
        
        Args:
            renderer: VTK 渲染器对象（vtk.vtkRenderer）
            model_load_callback: 模型加载回调函数 (side: str, renderer) -> None
            model_unload_callback: 模型卸载回调函数 (side: str, renderer) -> None
            lighthouse_update_callback: LightHouse 更新回调 (lighthouse_states: list[dict]) -> None
            tracking_state_changed_callback: 追踪状态改变回调 (enabled: bool) -> None
            render_request_callback: 请求主窗口渲染回调 () -> None
        """
        self._renderer = renderer
        self._model_load_callback = model_load_callback
        self._model_unload_callback = model_unload_callback
        self._lighthouse_update_callback = lighthouse_update_callback
        self._tracking_state_changed_callback = tracking_state_changed_callback
        self._render_request_callback = render_request_callback
        print("[ViveTrackerWidget] VTK 渲染器和模型回调已设置")
    
    def update_model_pose(self, side: str, position_xyz: tuple, quat_wxyz: tuple):
        """更新模型的位置和旋转（包括坐标轴）。坐标轴会完全跟随模型的位置和旋转。
        
        已优化：
        - VTK 对象复用：缓存 vtkMatrix4x4 和 vtkTransform，避免每帧新建
        - 变化检测：仅当位置/旋转改变时才更新坐标轴
        - 位置偏差：应用位置偏差到最终位置
        
        Args:
            side: "left" 或 "right"
            position_xyz: 位置 (x, y, z)，单位：米
            quat_wxyz: 四元数 (w, x, y, z)
        """
        if side not in self._tracker_model_actors:
            return
        
        actor = self._tracker_model_actors[side]
        if actor is None:
            return
        
        try:
            # ── 应用位置偏差 ────────────────
            # 获取对应的 TrackerData 以读取偏差
            tracker_data = None
            with self._data_lock:
                if side == "left":
                    tracker_data = self._left_data
                elif side == "right":
                    tracker_data = self._right_data
                
                # 计算最终位置（原始位置 + 偏差）
                if tracker_data is not None:
                    final_x = position_xyz[0] + tracker_data.pos_bias_x_m
                    final_y = position_xyz[1] + tracker_data.pos_bias_y_m
                    final_z = position_xyz[2] + tracker_data.pos_bias_z_m
                    final_position = (final_x, final_y, final_z)
                else:
                    final_position = position_xyz
            
            # 转换四元数格式从 (w, x, y, z) 到 (x, y, z, w)
            qx, qy, qz, qw = quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]
            
            # 更新追踪器 3D 模型的位置和旋转（使用带偏差的最终位置）
            actor.set_position_and_rotation(final_position, (qx, qy, qz, qw))
            
            # 同时更新坐标轴的位置和旋转
            axes_actor = self._tracker_axes_actors.get(side)
            if axes_actor is not None:
                try:
                    # ── 变化检测：检查位置和旋转是否改变 ────────────────
                    last_pose = self._last_axes_pose.get(side)
                    current_pose = (position_xyz, quat_wxyz)
                    
                    # 比较函数：检查浮点数相等性（容差 1e-6）
                    def _poses_equal(pose1, pose2, epsilon=1e-6):
                        if pose1 is None or pose2 is None:
                            return False
                        pos1, quat1 = pose1
                        pos2, quat2 = pose2
                        return all(abs(a - b) < epsilon for a, b in zip(pos1, pos2)) and \
                               all(abs(a - b) < epsilon for a, b in zip(quat1, quat2))
                    
                    # 如果位置和旋转未改变，跳过更新
                    if _poses_equal(last_pose, current_pose):
                        return
                    
                    # 记录本次更新（供下一帧比较）
                    self._last_axes_pose[side] = current_pose
                    
                    import vtk
                    
                    # 标准化四元数
                    quat_norm = (qx*qx + qy*qy + qz*qz + qw*qw) ** 0.5
                    if quat_norm > 1e-6:
                        qx_norm = qx / quat_norm
                        qy_norm = qy / quat_norm
                        qz_norm = qz / quat_norm
                        qw_norm = qw / quat_norm
                    else:
                        qx_norm, qy_norm, qz_norm, qw_norm = 0, 0, 0, 1
                    
                    # 将四元数转换为旋转矩阵
                    # 公式源于标准的四元数到旋转矩阵转换
                    r11 = 1 - 2*(qy_norm*qy_norm + qz_norm*qz_norm)
                    r12 = 2*(qx_norm*qy_norm - qz_norm*qw_norm)
                    r13 = 2*(qx_norm*qz_norm + qy_norm*qw_norm)
                    
                    r21 = 2*(qx_norm*qy_norm + qz_norm*qw_norm)
                    r22 = 1 - 2*(qx_norm*qx_norm + qz_norm*qz_norm)
                    r23 = 2*(qy_norm*qz_norm - qx_norm*qw_norm)
                    
                    r31 = 2*(qx_norm*qz_norm - qy_norm*qw_norm)
                    r32 = 2*(qy_norm*qz_norm + qx_norm*qw_norm)
                    r33 = 1 - 2*(qx_norm*qx_norm + qy_norm*qy_norm)
                    
                    # ── 复用缓存的 VTK 对象（避免每帧新建） ────────────────
                    if side not in self._axes_matrix_cache:
                        self._axes_matrix_cache[side] = vtk.vtkMatrix4x4()
                    if side not in self._axes_transform_cache:
                        self._axes_transform_cache[side] = vtk.vtkTransform()
                    
                    matrix = self._axes_matrix_cache[side]
                    transform = self._axes_transform_cache[side]
                    
                    # 更新矩阵元素（复用对象）
                    # 设置旋转部分 (3x3) + 平移（使用带偏差的最终位置）
                    matrix.SetElement(0, 0, r11)
                    matrix.SetElement(0, 1, r12)
                    matrix.SetElement(0, 2, r13)
                    matrix.SetElement(0, 3, final_position[0])
                    
                    matrix.SetElement(1, 0, r21)
                    matrix.SetElement(1, 1, r22)
                    matrix.SetElement(1, 2, r23)
                    matrix.SetElement(1, 3, final_position[1])
                    
                    matrix.SetElement(2, 0, r31)
                    matrix.SetElement(2, 1, r32)
                    matrix.SetElement(2, 2, r33)
                    matrix.SetElement(2, 3, final_position[2])
                    
                    # 齐次坐标
                    matrix.SetElement(3, 0, 0.0)
                    matrix.SetElement(3, 1, 0.0)
                    matrix.SetElement(3, 2, 0.0)
                    matrix.SetElement(3, 3, 1.0)
                    
                    # 为 assembly 中的每个 actor 应用相同的变换
                    transform.SetMatrix(matrix)
                    
                    parts = axes_actor.GetParts()
                    for i in range(parts.GetNumberOfItems()):
                        part = parts.GetItemAsObject(i)
                        if part is not None:
                            # 直接应用变换矩阵，不清除位置和方向
                            # SetUserTransform 会完全控制actor的变换
                            part.SetUserTransform(transform)
                            part.Modified()
                    
                    # 标记 assembly 为已更新
                    axes_actor.Modified()

                    if self._render_request_callback is not None:
                        self._render_request_callback()
                    
                except Exception as e:
                    print(f"[ModelPose] ⚠ {side} 手坐标轴更新警告：{e}")
                        
        except Exception as e:
            print(f"[ModelPose] 更新 {side} 模型位置失败：{e}")
    
    def store_model_actor(self, side: str, actor):
        """存储模型 Actor 引用。
        
        Args:
            side: "left" 或 "right"
            actor: VRTrackerModelActor 实例
        """
        self._tracker_model_actors[side] = actor
    
    def store_axes_actor(self, side: str, axes_actor):
        """存储坐标轴 Actor 引用。
        
        Args:
            side: "left" 或 "right"
            axes_actor: vtkPropAssembly 实例
        """
        self._tracker_axes_actors[side] = axes_actor
    
    def update_lighthouse_model_pose(self, lighthouse_name: str, position_xyz: tuple, quat_wxyz: tuple):
        """更新基站 3D 模型的位置和旋转（使用最终位置）。
        
        Args:
            lighthouse_name: 基站名称
            position_xyz: 原始位置 (x, y, z)，单位：米
            quat_wxyz: 四元数 (w, x, y, z)
        """
        if lighthouse_name not in self._lighthouse_model_actors:
            return
        
        actor = self._lighthouse_model_actors[lighthouse_name]
        if actor is None:
            return
        
        try:
            # 获取基站数据以计算最终位置
            lighthouse_data = self._lighthouse_manager.get_lighthouse(lighthouse_name)
            if lighthouse_data is None:
                final_position = position_xyz
            else:
                # 使用最终位置（原始位置 + 偏差）
                final_position = lighthouse_data.get_position_final()
            
            # 转换四元数格式从 (w, x, y, z) 到 (x, y, z, w)
            qx, qy, qz, qw = quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]
            
            # 更新基站 3D 模型的位置和旋转（使用最终位置）
            actor.set_position_and_rotation(final_position, (qx, qy, qz, qw))
            
            if self._render_request_callback is not None:
                self._render_request_callback()
                    
        except Exception as e:
            print(f"[LighthousePose] 更新 {lighthouse_name} 模型位置失败：{e}")
    
    def set_lighthouse_position_bias(self, lighthouse_name: str, x_bias: float, y_bias: float, z_bias: float):
        """设置指定基站的位置偏差，并立即更新 VTK 显示。
        
        Args:
            lighthouse_name: 基站名称（如 "Tracking Reference 1"）
            x_bias: X 轴偏差（米）
            y_bias: Y 轴偏差（米）
            z_bias: Z 轴偏差（米）
        
        Example:
            widget.set_lighthouse_position_bias("Tracking Reference 1", 0.0, 1.0, 0.0)  # Y 轴 +1.0 米
        """
        try:
            lighthouse_data = self._lighthouse_manager.get_lighthouse(lighthouse_name)
            if lighthouse_data is None:
                print(f"[LighthouseBias] 基站不存在：{lighthouse_name}")
                return
            
            # 更新偏差值
            lighthouse_data.update_position_bias(x_bias, y_bias, z_bias)
            print(f"[LighthouseBias] {lighthouse_name} 位置偏差已设置："
                  f"X={x_bias:.4f}m, Y={y_bias:.4f}m, Z={z_bias:.4f}m")
            print(f"[LighthouseBias] 最终位置：{lighthouse_data.get_position_final()}")
            
            # 立即更新 VTK 模型位置
            if lighthouse_name in self._lighthouse_model_actors:
                actor = self._lighthouse_model_actors[lighthouse_name]
                if actor is not None:
                    final_position = lighthouse_data.get_position_final()
                    qw, qx, qy, qz = lighthouse_data.get_quat()
                    actor.set_position_and_rotation(final_position, (qx, qy, qz, qw))
                    
                    if self._render_request_callback is not None:
                        self._render_request_callback()
                    print(f"[LighthouseBias] VTK 模型已更新")
            else:
                print(f"[LighthouseBias] 基站模型未加载（可能还未加载 3D 模型）")
            
        except Exception as e:
            print(f"[LighthouseBias] 设置 {lighthouse_name} 偏差失败：{e}")
    
    def set_all_lighthouses_position_bias(self, x_bias: float, y_bias: float, z_bias: float):
        """为所有基站设置相同的位置偏差，并立即更新 VTK 显示。
        
        Args:
            x_bias: X 轴偏差（米）
            y_bias: Y 轴偏差（米）
            z_bias: Z 轴偏差（米）
        
        Example:
            widget.set_all_lighthouses_position_bias(0.0, 1.0, 0.0)  # 所有基站 Y 轴 +1.0 米
        """
        all_lighthouses = self._lighthouse_manager.get_all_lighthouses()
        print(f"[LighthouseBias] 为 {len(all_lighthouses)} 个基站设置位置偏差...")
        
        for name in all_lighthouses.keys():
            self.set_lighthouse_position_bias(name, x_bias, y_bias, z_bias)
        
        print(f"[LighthouseBias] ✅ 所有基站位置偏差已设置完成")
    
    def _unload_all_tracker_models(self):
        """卸载所有已加载的 VR 追踪器模型。"""
        for side in ["left", "right"]:
            if self._model_unload_callback is not None and self._renderer is not None:
                try:
                    self._model_unload_callback(side, self._renderer)
                except Exception as e:
                    print(f"[UnloadTrackers] 卸载 {side} 手模型失败：{e}")

    def _on_start_tracking_clicked(self):
        """处理 "开启追踪" 按钮点击。"""
        if not self._tracking_enabled:
            self._start_tracking()
        else:
            self._stop_tracking()

    def _start_tracking(self):
        """启动追踪。"""
        try:
            from triad_openvr.triad_openvr import triad_openvr
            self._openvr_system = triad_openvr()
        except Exception as e:
            error_text = f"<font color='red'><b>OpenVR 初始化失败</b></font><br>{e}"
            self._left_config_label.setText(error_text)
            self._right_config_label.setText(error_text)
            return

        # 根据配置查找设备
        self._devices = {}
        left_serial = self._config.get("LeftHandTracker", {}).get("SerialNumber")
        right_serial = self._config.get("RightHandTracker", {}).get("SerialNumber")
        
        # 调试：打印所有发现的设备
        debug_lines = ["配置序列号："]
        debug_lines.append(f"  左手: {left_serial if left_serial else '未配置'}")
        debug_lines.append(f"  右手: {right_serial if right_serial else '未配置'}")
        debug_lines.append("")
        debug_lines.append("系统设备：")
        
        for device_name, device in self._openvr_system.devices.items():
            try:
                serial = device.get_serial()
                if isinstance(serial, bytes):
                    serial = serial.decode('utf-8')
                debug_lines.append(f"  {device_name}: {serial}")
                
                if serial == left_serial:
                    self._devices["left"] = device
                    debug_lines.append(f"    ✓ 左手匹配")
                    print(f"[StartTracking] 左手设备已匹配: {serial}")
                elif serial == right_serial:
                    self._devices["right"] = device
                    debug_lines.append(f"    ✓ 右手匹配")
                    print(f"[StartTracking] 右手设备已匹配: {serial}")
            except Exception as e:
                debug_lines.append(f"  {device_name}: 读取失败 - {e}")
                print(f"[StartTracking] 读取设备失败: {e}")
        
        debug_text = "\n".join(debug_lines)
        self._connection_status_text.setText(debug_text)
        
        if not self._devices:
            error_text = f"未找到匹配的追踪器\n已配置序列号：\nLeft: {left_serial}\nRight: {right_serial}"
            self._connection_status_text.setText(debug_text + "\n\n" + error_text)
            self._openvr_system = None
            return

        # 启动后台数据收集线程
        self._tracking_enabled = True
        
        # 启用定位标定 tab（追踪成功开启）
        self._tab_widget.setTabEnabled(self._calibration_tab_index, True)
        
        self._thread_stop_event.clear()
        self._tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._tracking_thread.start()
        
        # 启动 UI 更新定时器
        self._update_timer.start()
        
        # 启动 LightHouse 更新定时器
        self._lighthouse_update_timer.start()

        if self._tracking_state_changed_callback is not None:
            try:
                self._tracking_state_changed_callback(True)
            except Exception as e:
                print(f"[ViveTrackerWidget] 追踪状态回调失败（start）：{e}")
        
        # 更新按钮文本
        self._start_tracking_btn.setText("停止追踪")

    def _rescan_devices(self):
        """重新扫描系统中的设备，查找新连接的传感器。"""
        if self._openvr_system is None:
            return
        
        try:
            # 先轮询 VR 事件，触发新设备加入 devices 字典
            self._openvr_system.poll_vr_events()
            
            left_serial = self._config.get("LeftHandTracker", {}).get("SerialNumber")
            right_serial = self._config.get("RightHandTracker", {}).get("SerialNumber")
            
            need_left = "left" not in self._devices or self._devices["left"] is None
            need_right = "right" not in self._devices or self._devices["right"] is None
            
            if not need_left and not need_right:
                return  # 两个设备都已找到，无需扫描
            
            for device_name, device in self._openvr_system.devices.items():
                try:
                    serial = device.get_serial()
                    if isinstance(serial, bytes):
                        serial = serial.decode('utf-8')
                    
                    if need_left and serial == left_serial:
                        self._devices["left"] = device
                        print(f"[RescanDevices] ✓ 左手设备已匹配: {serial}")
                        need_left = False
                    elif need_right and serial == right_serial:
                        self._devices["right"] = device
                        print(f"[RescanDevices] ✓ 右手设备已匹配: {serial}")
                        need_right = False
                    
                    if not need_left and not need_right:
                        break
                except Exception:
                    pass
        except Exception as e:
            print(f"[RescanDevices] 异常: {e}")
            import traceback
            traceback.print_exc()

    def _stop_tracking(self):
        """停止追踪。"""
        self._tracking_enabled = False
        
        # 禁用定位标定 tab（追踪已关闭）
        self._tab_widget.setTabEnabled(self._calibration_tab_index, False)
        
        self._update_timer.stop()
        self._lighthouse_update_timer.stop()
        
        if self._tracking_thread is not None:
            self._thread_stop_event.set()
            self._tracking_thread.join(timeout=1)
            self._tracking_thread = None
        
        self._openvr_system = None
        self._devices = {}

        if self._tracking_state_changed_callback is not None:
            try:
                self._tracking_state_changed_callback(False)
            except Exception as e:
                print(f"[ViveTrackerWidget] 追踪状态回调失败（stop）：{e}")
        
        # 重置显示
        self._left_position_label.setText("位置：X= 0.0000m  Y= 0.0000m  Z= 0.0000m")
        self._left_rotation_label.setText("旋转：Yaw= 0.00°  Pitch= 0.00°  Roll= 0.00°")
        self._left_quat_label.setText("四元数：w= 0.0000  x= 0.0000  y= 0.0000  z= 0.0000")
        self._right_position_label.setText("位置：X= 0.0000m  Y= 0.0000m  Z= 0.0000m")
        self._right_rotation_label.setText("旋转：Yaw= 0.00°  Pitch= 0.00°  Roll= 0.00°")
        self._right_quat_label.setText("四元数：w= 0.0000  x= 0.0000  y= 0.0000  z= 0.0000")
        
        # 清除基站信息并重置 LighthouseManager
        self._lighthouse_manager.clear()
        # 移除 connectionStatusText 中的 LightHouse 部分
        current_text = self._connection_status_text.toPlainText()
        if "\n=== LightHouse" in current_text:
            current_text = current_text[:current_text.index("\n=== LightHouse")]
            self._connection_status_text.setText(current_text)
        
        # 重置在线状态并更新 GroupBox 样式
        self._left_online_state = False
        self._right_online_state = False
        # 重置离线计数器
        self._left_offline_counter = 0
        self._right_offline_counter = 0
        self._set_groupbox_online_status(self._left_group, False)
        self._set_groupbox_online_status(self._right_group, False)
        
        # 重置显示模式为欧拉角
        self._left_show_quat = False
        self._right_show_quat = False
        self._left_rotation_label.setVisible(True)
        self._left_quat_label.setVisible(False)
        self._right_rotation_label.setVisible(True)
        self._right_quat_label.setVisible(False)
        
        # 更新按钮文本
        self._start_tracking_btn.setText("开始追踪")
        
        # 卸载所有 VR 追踪器模型
        self._unload_all_tracker_models()

    def _tracking_loop(self):
        """后台追踪线程，60Hz 数据收集。"""
        import math
        interval = 1.0 / 60.0  # 60Hz
        
        first_run = True
        rescan_counter = 0  # 每秒重新扫描一次设备（60Hz，所以计数到60）
        
        while not self._thread_stop_event.is_set():
            try:
                # 每秒重新检查一次是否有新设备连接
                rescan_counter += 1
                if rescan_counter >= 60:
                    rescan_counter = 0
                    self._rescan_devices()
                
                left_device = self._devices.get("left")
                right_device = self._devices.get("right")
                
                # 每帧开始时重置 valid 标志为 False，只有成功读取数据时才设置为 True
                with self._data_lock:
                    self._left_data.valid = False
                    self._right_data.valid = False
                
                # 读取左手数据
                if left_device is not None:
                    try:
                        pose_euler = left_device.get_pose_euler()
                        
                        if pose_euler is not None:
                            x, y, z, yaw, pitch, roll = pose_euler
                            with self._data_lock:
                                self._left_data.pos_origin_x_m = x
                                self._left_data.pos_origin_y_m = y
                                self._left_data.pos_origin_z_m = z
                                self._left_data.yaw = yaw
                                self._left_data.pitch = pitch
                                self._left_data.roll = roll
                                
                                # 尝试读取四元数
                                try:
                                    pose_quat = left_device.get_pose_quaternion()
                                    if pose_quat is not None and len(pose_quat) == 7:
                                        # pose_quat = [x, y, z, qw, qx, qy, qz]
                                        x_q, y_q, z_q, qw, qx, qy, qz = pose_quat
                                        self._left_data.quat_origin_w = qw
                                        self._left_data.quat_origin_x = qx
                                        self._left_data.quat_origin_y = qy
                                        self._left_data.quat_origin_z = qz
                                    else:
                                        self._left_data.quat_origin_w = 1.0
                                        self._left_data.quat_origin_x = 0.0
                                        self._left_data.quat_origin_y = 0.0
                                        self._left_data.quat_origin_z = 0.0
                                except Exception as e:
                                    if first_run:
                                        print(f"[Left] get_pose_quaternion() error: {e}")
                                    self._left_data.quat_origin_w = 1.0
                                    self._left_data.quat_origin_x = 0.0
                                    self._left_data.quat_origin_y = 0.0
                                    self._left_data.quat_origin_z = 0.0
                                
                                # 标记数据有效
                                self._left_data.valid = True
                        elif first_run:
                            print(f"[Left] get_pose_euler() returned None")
                    except Exception as e:
                        if first_run:
                            print(f"[Left] Error: {e}")
                
                # 读取右手数据
                if right_device is not None:
                    try:
                        pose_euler = right_device.get_pose_euler()
                        
                        if pose_euler is not None:
                            x, y, z, yaw, pitch, roll = pose_euler
                            with self._data_lock:
                                self._right_data.pos_origin_x_m = x
                                self._right_data.pos_origin_y_m = y
                                self._right_data.pos_origin_z_m = z
                                self._right_data.yaw = yaw
                                self._right_data.pitch = pitch
                                self._right_data.roll = roll
                                
                                # 尝试读取四元数
                                try:
                                    pose_quat = right_device.get_pose_quaternion()
                                    if pose_quat is not None and len(pose_quat) == 7:
                                        # pose_quat = [x, y, z, qw, qx, qy, qz]
                                        x_q, y_q, z_q, qw, qx, qy, qz = pose_quat
                                        self._right_data.quat_origin_w = qw
                                        self._right_data.quat_origin_x = qx
                                        self._right_data.quat_origin_y = qy
                                        self._right_data.quat_origin_z = qz
                                    else:
                                        self._right_data.quat_origin_w = 1.0
                                        self._right_data.quat_origin_x = 0.0
                                        self._right_data.quat_origin_y = 0.0
                                        self._right_data.quat_origin_z = 0.0
                                except Exception as e:
                                    if first_run:
                                        print(f"[Right] get_pose_quaternion() error: {e}")
                                    self._right_data.quat_origin_w = 1.0
                                    self._right_data.quat_origin_x = 0.0
                                    self._right_data.quat_origin_y = 0.0
                                    self._right_data.quat_origin_z = 0.0
                                
                                # 标记数据有效
                                self._right_data.valid = True
                        elif first_run:
                            print(f"[Right] get_pose_euler() returned None")
                    except Exception as e:
                        if first_run:
                            print(f"[Right] Error: {e}")
                
                first_run = False
                time.sleep(interval)
            except Exception as e:
                print(f"Tracking loop exception: {e}")
                pass

    def _collect_lighthouse_states(self):
        """采集基站位姿列表，并通过 LighthouseManager 进行管理。

        Returns:
            list[dict]: 每个元素包含 id/name/serial/position/quat_wxyz。
                       position 是最终位置（原始位置 + 位置偏差）。
        """
        lighthouse_states = []
        if self._openvr_system is None:
            return lighthouse_states

        tracking_refs = self._openvr_system.object_names.get("Tracking Reference", [])
        for ref_name in tracking_refs:
            device = self._openvr_system.devices.get(ref_name)
            if device is None:
                continue

            try:
                serial = device.get_serial()
                if isinstance(serial, bytes):
                    serial = serial.decode('utf-8')

                pose_quat = device.get_pose_quaternion()
                if not pose_quat or len(pose_quat) != 7:
                    continue

                x, y, z, qw, qx, qy, qz = pose_quat
                
                # 通过 LighthouseManager 进行管理
                if ref_name not in self._lighthouse_manager.get_all_lighthouses():
                    self._lighthouse_manager.register_lighthouse(ref_name, serial)
                
                # 更新基站数据
                lighthouse = self._lighthouse_manager.get_lighthouse(ref_name)
                if lighthouse is not None:
                    lighthouse.update_position(x, y, z)
                    lighthouse.update_quat(qw, qx, qy, qz)
                    lighthouse.is_online = True
                    lighthouse.valid = True
                    lighthouse.timestamp = time.time()
                    
                    # 获取最终位置（原始位置 + 位置偏差）
                    final_position = lighthouse.get_position_final()
                else:
                    # 如果获取失败，使用原始位置
                    final_position = (x, y, z)
                
                # 使用最终位置（包含偏差）来返回给VTK
                lighthouse_dict = {
                    "id": serial or ref_name,
                    "name": ref_name,
                    "serial": serial,
                    "position": final_position,  # 这里是最终位置（原始位置 + 偏差）
                    "quat_wxyz": (qw, qx, qy, qz),
                }
                lighthouse_states.append(lighthouse_dict)
                    
            except Exception as e:
                print(f"[LighthouseCollection] 采集基站 {ref_name} 失败: {e}")
                continue

        return lighthouse_states

    def _update_light_house_info(self):
        """获取并更新 LightHouse 基站信息，显示在 connectionStatusText 中。
        
        只有当内容发生变化时，才会更新 UI。使用 LighthouseManager 进行管理。
        """
        if self._openvr_system is None:
            new_lighthouse_content = ""
            lighthouse_states = []
        else:
            try:
                lighthouse_states = self._collect_lighthouse_states()
                # 获取所有基站（Tracking Reference）
                tracking_refs = self._openvr_system.object_names.get("Tracking Reference", [])
                
                if not tracking_refs:
                    new_lighthouse_content = ""
                else:
                    # 获取基站信息
                    info_lines = ["", "=== LightHouse Base Station ==="]
                    for ref_name in tracking_refs:
                        # 从 LighthouseManager 获取基站数据
                        lighthouse_data = self._lighthouse_manager.get_lighthouse(ref_name)
                        if lighthouse_data is None:
                            continue
                        
                        try:
                            device = self._openvr_system.devices.get(ref_name)
                            if device is not None:
                                # 获取位置和旋转信息
                                pose_euler = device.get_pose_euler()
                                pose_quat = device.get_pose_quaternion()
                                
                                info_lines.append(f"【{ref_name}】 Serial: {lighthouse_data.serial}")
                                
                                if pose_euler:
                                    x, y, z, yaw, pitch, roll = pose_euler
                                    # 同时更新 LighthouseData 的欧拉角
                                    lighthouse_data.update_euler(yaw, pitch, roll)
                                    info_lines.append(f"  位置: X={x:8.4f}m Y={y:8.4f}m Z={z:8.4f}m")
                                    info_lines.append(f"  旋转: Yaw={yaw:7.2f}° Pitch={pitch:7.2f}° Roll={roll:7.2f}°")
                                
                                if pose_quat:
                                    x, y, z, qw, qx, qy, qz = pose_quat
                                    info_lines.append(f"  四元数: w={qw:8.4f} x={qx:8.4f} y={qy:8.4f} z={qz:8.4f}")
                                
                                # 更新基站 VTK 模型的位置（使用最终位置）
                                if ref_name in self._lighthouse_model_actors:
                                    self.update_lighthouse_model_pose(
                                        ref_name,
                                        (x, y, z),
                                        (qw, qx, qy, qz)
                                    )
                                
                                info_lines.append("")
                        except Exception as e:
                            info_lines.append(f"【{ref_name}】 错误：{e}")
                            info_lines.append("")
                    
                    new_lighthouse_content = "\n".join(info_lines) if info_lines else ""
            except Exception as e:
                lighthouse_states = []
                new_lighthouse_content = f"\n=== LightHouse Error ===\n获取基站信息失败: {e}"

        if self._lighthouse_update_callback is not None:
            try:
                self._lighthouse_update_callback(lighthouse_states)
            except Exception as e:
                print(f"[ViveTrackerWidget] LightHouse 回调失败：{e}")
        
        # 检测是否有变化，只有发生变化才更新 UI
        # 使用 LighthouseManager 缓存内容
        last_content = self._lighthouse_manager.get_last_content()
        if last_content != new_lighthouse_content:
            # 获取当前连接状态文本的前面部分（不含 LightHouse 部分）
            current_text = self._connection_status_text.toPlainText()
            
            # 移除旧的 LightHouse 部分
            if "\n=== LightHouse" in current_text:
                current_text = current_text[:current_text.index("\n=== LightHouse")]
            
            # 添加新的 LightHouse 信息
            updated_text = current_text + new_lighthouse_content
            self._connection_status_text.setText(updated_text)
            self._lighthouse_manager.set_last_content(new_lighthouse_content)

    def _on_update_timer(self):
        """UI 更新定时器回调，60Hz 刷新追踪数据显示。
        
        使用离线计数器：连续20帧无数据才判定为离线，避免频繁切换。
        同时更新模型的位置和旋转，以及 TrackerManager 中的数据。
        """
        tracker_pose_updated = False
        with self._data_lock:
            # 处理左手数据
            if self._left_data.valid:
                # 有有效数据，重置离线计数器
                self._left_offline_counter = 0
                pos_text = f"位置：X={self._left_data.pos_origin_x_m:8.4f}m  Y={self._left_data.pos_origin_y_m:8.4f}m  Z={self._left_data.pos_origin_z_m:8.4f}m"
                rot_text = f"旋转：Yaw={self._left_data.yaw:7.2f}°  Pitch={self._left_data.pitch:7.2f}°  Roll={self._left_data.roll:7.2f}°"
                quat_text = f"四元数：w={self._left_data.quat_origin_w:8.4f}  x={self._left_data.quat_origin_x:8.4f}  y={self._left_data.quat_origin_y:8.4f}  z={self._left_data.quat_origin_z:8.4f}"
                self._left_position_label.setText(pos_text)
                self._left_rotation_label.setText(rot_text)
                self._left_quat_label.setText(quat_text)
                self._update_groupbox_status("left", True)
                
                # 更新 TrackerManager 中左手 Tracker 的数据
                left_tracker = self._tracker_manager.get_tracker("left")
                if left_tracker is None:
                    left_tracker = self._tracker_manager.register_tracker("left")
                
                left_tracker.is_online = True
                left_tracker.valid = True
                left_tracker.update_position(self._left_data.pos_origin_x_m, self._left_data.pos_origin_y_m, self._left_data.pos_origin_z_m)
                left_tracker.update_euler(self._left_data.yaw, self._left_data.pitch, self._left_data.roll)
                left_tracker.update_quat(self._left_data.quat_origin_w, self._left_data.quat_origin_x, self._left_data.quat_origin_y, self._left_data.quat_origin_z)
                left_tracker.timestamp = time.time()
                
                # 更新模型位置和旋转
                self.update_model_pose(
                    "left",
                    (self._left_data.pos_origin_x_m, self._left_data.pos_origin_y_m, self._left_data.pos_origin_z_m),
                    (self._left_data.quat_origin_w, self._left_data.quat_origin_x, self._left_data.quat_origin_y, self._left_data.quat_origin_z)
                )
                tracker_pose_updated = True
            else:
                # 无有效数据，增加离线计数器
                self._left_offline_counter += 1
                if self._left_offline_counter >= self._offline_threshold:
                    # 连续20帧无数据，标记为离线
                    self._update_groupbox_status("left", False)
                    # 更新 TrackerManager 中左手 Tracker 的在线状态
                    left_tracker = self._tracker_manager.get_tracker("left")
                    if left_tracker is not None:
                        left_tracker.is_online = False
            
            # 处理右手数据
            if self._right_data.valid:
                # 有有效数据，重置离线计数器
                self._right_offline_counter = 0
                pos_text = f"位置：X={self._right_data.pos_origin_x_m:8.4f}m  Y={self._right_data.pos_origin_y_m:8.4f}m  Z={self._right_data.pos_origin_z_m:8.4f}m"
                rot_text = f"旋转：Yaw={self._right_data.yaw:7.2f}°  Pitch={self._right_data.pitch:7.2f}°  Roll={self._right_data.roll:7.2f}°"
                quat_text = f"四元数：w={self._right_data.quat_origin_w:8.4f}  x={self._right_data.quat_origin_x:8.4f}  y={self._right_data.quat_origin_y:8.4f}  z={self._right_data.quat_origin_z:8.4f}"
                self._right_position_label.setText(pos_text)
                self._right_rotation_label.setText(rot_text)
                self._right_quat_label.setText(quat_text)
                self._update_groupbox_status("right", True)
                
                # 更新 TrackerManager 中右手 Tracker 的数据
                right_tracker = self._tracker_manager.get_tracker("right")
                if right_tracker is None:
                    right_tracker = self._tracker_manager.register_tracker("right")
                
                right_tracker.is_online = True
                right_tracker.valid = True
                right_tracker.update_position(self._right_data.pos_origin_x_m, self._right_data.pos_origin_y_m, self._right_data.pos_origin_z_m)
                right_tracker.update_euler(self._right_data.yaw, self._right_data.pitch, self._right_data.roll)
                right_tracker.update_quat(self._right_data.quat_origin_w, self._right_data.quat_origin_x, self._right_data.quat_origin_y, self._right_data.quat_origin_z)
                right_tracker.timestamp = time.time()
                
                # 更新模型位置和旋转
                self.update_model_pose(
                    "right",
                    (self._right_data.pos_origin_x_m, self._right_data.pos_origin_y_m, self._right_data.pos_origin_z_m),
                    (self._right_data.quat_origin_w, self._right_data.quat_origin_x, self._right_data.quat_origin_y, self._right_data.quat_origin_z)
                )
                tracker_pose_updated = True
            else:
                # 无有效数据，增加离线计数器
                self._right_offline_counter += 1
                if self._right_offline_counter >= self._offline_threshold:
                    # 连续20帧无数据，标记为离线
                    self._update_groupbox_status("right", False)
                    # 更新 TrackerManager 中右手 Tracker 的在线状态
                    right_tracker = self._tracker_manager.get_tracker("right")
                    if right_tracker is not None:
                        right_tracker.is_online = False

        if tracker_pose_updated and self._renderer is not None:
            self._renderer.ResetCameraClippingRange()

    def get_left_tracker_data(self):
        """获取左手追踪器数据快照（线程安全）。未追踪或数据无效时返回 None。"""
        if not self._tracking_enabled:
            return None
        with self._data_lock:
            if not self._left_data.valid:
                return None
            return TrackerData(
                pos_origin_x_m=self._left_data.pos_origin_x_m, pos_origin_y_m=self._left_data.pos_origin_y_m, pos_origin_z_m=self._left_data.pos_origin_z_m,
                yaw=self._left_data.yaw, pitch=self._left_data.pitch, roll=self._left_data.roll,
                quat_origin_w=self._left_data.quat_origin_w, quat_origin_x=self._left_data.quat_origin_x,
                quat_origin_y=self._left_data.quat_origin_y, quat_origin_z=self._left_data.quat_origin_z,
                pos_bias_x_m=self._left_data.pos_bias_x_m, pos_bias_y_m=self._left_data.pos_bias_y_m, pos_bias_z_m=self._left_data.pos_bias_z_m,
                valid=True,
            )

    def get_right_tracker_data(self):
        """获取右手追踪器数据快照（线程安全）。未追踪或数据无效时返回 None。"""
        if not self._tracking_enabled:
            return None
        with self._data_lock:
            if not self._right_data.valid:
                return None
            return TrackerData(
                pos_origin_x_m=self._right_data.pos_origin_x_m, pos_origin_y_m=self._right_data.pos_origin_y_m, pos_origin_z_m=self._right_data.pos_origin_z_m,
                yaw=self._right_data.yaw, pitch=self._right_data.pitch, roll=self._right_data.roll,
                quat_origin_w=self._right_data.quat_origin_w, quat_origin_x=self._right_data.quat_origin_x,
                quat_origin_y=self._right_data.quat_origin_y, quat_origin_z=self._right_data.quat_origin_z,
                pos_bias_x_m=self._right_data.pos_bias_x_m, pos_bias_y_m=self._right_data.pos_bias_y_m, pos_bias_z_m=self._right_data.pos_bias_z_m,
                valid=True,
            )

    def is_tracking_enabled(self) -> bool:
        """是否处于追踪开启状态。"""
        return self._tracking_enabled
    
    def get_tracker_manager(self) -> TrackerManager:
        """获取 Tracker 管理器。
        
        Returns:
            TrackerManager 实例，包含所有已注册的 Tracker
        """
        return self._tracker_manager
    
    def get_tracker(self, name: str) -> Optional[ViveTrackerMgr]:
        """获取指定名称的 Tracker 信息。
        
        Args:
            name: Tracker 名称（"left", "right" 等）
        
        Returns:
            ViveTrackerMgr 实例或 None
        """
        return self._tracker_manager.get_tracker(name)
    
    def get_all_trackers(self) -> Dict[str, ViveTrackerMgr]:
        """获取所有 Tracker 信息。
        
        Returns:
            {name: ViveTrackerMgr} 字典
        """
        return self._tracker_manager.get_all_trackers()
    
    def get_online_trackers(self) -> Dict[str, ViveTrackerMgr]:
        """获取所有在线的 Tracker 信息。
        
        Returns:
            {name: ViveTrackerMgr} 字典，仅包含在线的 Tracker
        """
        return self._tracker_manager.get_online_trackers()
    
    def print_tracker_summary(self):
        """打印所有 Tracker 的摘要信息。"""
        self._tracker_manager.print_summary()
    
    def print_lighthouse_summary(self):
        """打印所有 LightHouse 基站的摘要信息。"""
        self._lighthouse_manager.print_summary()
    
    def get_lighthouse_manager(self) -> LighthouseManager:
        """获取 LightHouse 管理器。
        
        Returns:
            LighthouseManager 实例，包含所有已注册的基站
        """
        return self._lighthouse_manager
    
    def store_lighthouse_actor(self, lighthouse_name: str, actor):
        """存储 LightHouse 模型 Actor 引用。
        
        Args:
            lighthouse_name: 基站名称
            actor: LighthouseModelActor 实例
        """
        self._lighthouse_model_actors[lighthouse_name] = actor

    def closeEvent(self, event):
        """窗口关闭时清理资源。"""
        if self._tracking_enabled:
            self._stop_tracking()
        super().closeEvent(event)
