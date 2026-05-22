"""vive_tracker_widget.py
Vive Tracker 配置显示和追踪面板

功能：
- 从项目根目录 config.json 读取配置
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
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt, QEvent
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu
from shiboken6 import isValid

# 导入 SteamVR 状态检查器
from triad_openvr.steamvr_status_checker import SteamVRStatusChecker

# 导入 Tracker 管理器和追踪数据类
from triad_openvr.tracker_manager import ViveTrackerMgr, TrackerManager, TrackerData, get_global_tracker_manager
from triad_openvr.tracker_cali_manager import TrackerCaliManager, get_global_tracker_cali_manager

# 导入 LightHouse 管理器
from triad_openvr.lighthouse_manager import LighthouseManager, get_global_lighthouse_manager

# 导入独立的追踪信息、标定和设备列表面板
from vive_tracker_info_widget import ViveTrackerInfoWidget, InfoTabManager
from vive_tracker_cali_widget import ViveTrackerCaliWidget, CaliTabManager
from vive_tracker_caliApply import CaliApplyTabManager
from vive_tracker_all_devices import AllDevicesTabManager
from python_draw3d.vive_tracker_attachAxis import (
    DEFAULT_ATTACH_AXIS_OFFSET_XYZ,
    DEFAULT_LEFT_ATTACH_AXIS_OFFSET_XYZ,
    DEFAULT_LEFT_ATTACH_AXIS_ROTATION_XYZ_DEGREES,
    DEFAULT_RIGHT_ATTACH_AXIS_OFFSET_XYZ,
    DEFAULT_RIGHT_ATTACH_AXIS_ROTATION_XYZ_DEGREES,
    build_vive_tracker_attach_axis_actor,
    compose_vive_tracker_attach_axis_pose,
    apply_pose_to_prop_assembly,
    quaternion_from_euler_xyz_degrees_wxyz,
)


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
    """查找项目根目录 config.json 文件的路径。"""
    candidates = [
        Path(__file__).parent.parent / "config.json",
        Path.cwd() / "config.json",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate
    
    # 未找到文件，返回第一个候选路径（便于错误提示）
    return candidates[0]




class ViveTrackerWidget(QWidget):
    """Vive Tracker 配置显示和追踪面板。"""

    _TAB_DEBUG_ENABLED = True

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 追踪器管理器（存储所有 Tracker 的统一信息）
        self._tracker_manager: TrackerManager = get_global_tracker_manager()
        
        # LightHouse 管理器（存储所有 LightHouse 基站的统一信息）
        self._lighthouse_manager: LighthouseManager = get_global_lighthouse_manager()

        # Tracker 标定偏移管理器（存储所有 Vive Tracker 共享的偏移四元数）
        self._tracker_cali_manager: TrackerCaliManager = get_global_tracker_cali_manager()

        # 追踪状态
        self._tracking_enabled = False
        self._calibration_active = False
        self._rotate_position_by_calibration = True
        self._left_hand_root_follow_tracker = False
        self._left_hand_last_tracker_display_position_xyz: tuple[float, float, float] | None = None
        self._right_hand_root_follow_tracker = False
        self._right_hand_last_tracker_display_position_xyz: tuple[float, float, float] | None = None
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
        self._left_tracker_attach_axis_actor = None
        # 从配置文件读取左手附加点设置
        try:
            from src.config_io import read_config
            cfg = read_config()
            left_cfg = cfg.get("vive_tracker_attach_axis", {}).get("left", {})
            right_cfg = cfg.get("vive_tracker_attach_axis", {}).get("right", {})
            self._left_tracker_attach_axis_offset_xyz = tuple(left_cfg.get("offset_xyz", DEFAULT_LEFT_ATTACH_AXIS_OFFSET_XYZ))
            self._left_tracker_attach_axis_local_rotation_xyz_degrees = tuple(left_cfg.get("rotation_xyz_degrees", DEFAULT_LEFT_ATTACH_AXIS_ROTATION_XYZ_DEGREES))
            self._right_tracker_attach_axis_offset_xyz = tuple(right_cfg.get("offset_xyz", DEFAULT_RIGHT_ATTACH_AXIS_OFFSET_XYZ))
            self._right_tracker_attach_axis_local_rotation_xyz_degrees = tuple(right_cfg.get("rotation_xyz_degrees", DEFAULT_RIGHT_ATTACH_AXIS_ROTATION_XYZ_DEGREES))
        except Exception:
            # 配置读取失败，使用默认值
            self._left_tracker_attach_axis_offset_xyz = DEFAULT_LEFT_ATTACH_AXIS_OFFSET_XYZ
            self._left_tracker_attach_axis_local_rotation_xyz_degrees = DEFAULT_LEFT_ATTACH_AXIS_ROTATION_XYZ_DEGREES
            self._right_tracker_attach_axis_offset_xyz = DEFAULT_RIGHT_ATTACH_AXIS_OFFSET_XYZ
            self._right_tracker_attach_axis_local_rotation_xyz_degrees = DEFAULT_RIGHT_ATTACH_AXIS_ROTATION_XYZ_DEGREES

        self._left_tracker_attach_axis_enabled = False
        self._right_tracker_attach_axis_actor = None
        self._right_tracker_attach_axis_enabled = False
        self._lighthouse_model_actors = {}  # {lighthouse_name: LighthouseModelActor}
        
        # ── VTK 对象缓存（避免每帧新建） ────────────────────
        self._axes_transform_cache = {}  # {"left": vtkTransform, "right": vtkTransform}
        self._axes_matrix_cache = {}     # {"left": vtkMatrix4x4, "right": vtkMatrix4x4}
        # 记录最后一次坐标轴更新的位置和四元数，用于变化检测
        self._last_axes_pose = {}        # {"left": (pos, quat), "right": (pos, quat)}
        self._left_attach_axis_transform_cache = None
        self._left_attach_axis_matrix_cache = None
        self._last_left_attach_axis_pose: tuple[
            tuple[float, float, float],
            tuple[float, float, float, float],
        ] | None = None
        self._right_attach_axis_transform_cache = None
        self._right_attach_axis_matrix_cache = None
        self._last_right_attach_axis_pose: tuple[
            tuple[float, float, float],
            tuple[float, float, float, float],
        ] | None = None
        
        # 追踪信息tab管理器
        self._info_tab_manager = InfoTabManager(self)
        
        # 标定tab管理器
        self._cali_tab_manager = CaliTabManager(self)

        # 应用定位 tab 管理器
        self._cali_apply_tab_manager = CaliApplyTabManager(self)

        # 所有设备tab管理器
        self._all_devices_tab_manager = AllDevicesTabManager(self)
        
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
        # 当前面板只持有一套真实显示的 tab UI，避免额外加载未显示的孤立控件树。
        self._ui = None

        # 创建主布局和 TabWidget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建 TabWidget
        self._tab_widget = QTabWidget()
        layout.addWidget(self._tab_widget)
        
        # 第一个 tab：追踪信息（由 InfoTabManager 管理）
        self._info_widget = self._info_tab_manager.setup_info_tab(self._tab_widget)
        
        # 第二个 tab：定位标定（由 CaliTabManager 管理）
        self._calibration_widget = self._cali_tab_manager.setup_calibration_tab(self._tab_widget)

        # 第三个 tab：应用定位（将 LeftHand 根骨骼附加到左手 Vive Tracker）
        self._cali_apply_widget = self._cali_apply_tab_manager.setup_cali_apply_tab(self._tab_widget)

        # 第四个 tab：所有设备（完全独立）
        self._all_devices_widget = self._all_devices_tab_manager.setup_all_devices_tab(self._tab_widget)

        self._install_tab_debug_hooks()
        
        # 从 InfoTabManager 获取 UI 中的控件（保持向后兼容性）
        info_widget = self._info_widget
        self._left_config_label: QLabel = info_widget.get_config_labels()["left"]
        self._right_config_label: QLabel = info_widget.get_config_labels()["right"]
        self._left_position_label: QLabel = info_widget.get_position_labels()["left"]
        self._right_position_label: QLabel = info_widget.get_position_labels()["right"]
        self._left_rotation_label: QLabel = info_widget.get_rotation_labels()["left"]
        self._right_rotation_label: QLabel = info_widget.get_rotation_labels()["right"]
        self._left_quat_label: QLabel = info_widget.get_quat_labels()["left"]
        self._right_quat_label: QLabel = info_widget.get_quat_labels()["right"]
        self._left_group: QGroupBox = info_widget.get_groups()["left"]
        self._right_group: QGroupBox = info_widget.get_groups()["right"]
        self._start_tracking_btn: QPushButton = info_widget.get_start_tracking_button()
        # 验证关键控件存在
        assert self._left_config_label is not None, "UI 控件未找到：leftHandConfigInfo"
        assert self._right_config_label is not None, "UI 控件未找到：rightHandConfigInfo"
        assert self._start_tracking_btn is not None, "UI 控件未找到：startTrackingButton"
        
        # 连接信号
        self._start_tracking_btn.clicked.connect(self._on_start_tracking_clicked)
        self._sync_start_tracking_button_text()
        self._debug_log_tracking_button_state("init_ui_after_connect")
        self._sync_tab_refresh_flags(self._tab_widget.currentIndex())

    def _install_tab_debug_hooks(self):
        """安装 tab 切换调试日志。"""
        if not self._TAB_DEBUG_ENABLED:
            return

        tab_bar = self._tab_widget.tabBar()
        tab_bar.installEventFilter(self)
        self._tab_widget.installEventFilter(self)

        for index in range(self._tab_widget.count()):
            page = self._tab_widget.widget(index)
            if page is not None:
                page.installEventFilter(self)

        tab_bar.currentChanged.connect(self._on_tab_bar_current_changed)
        tab_bar.tabBarClicked.connect(self._on_tab_bar_clicked)
        self._tab_widget.currentChanged.connect(self._on_tab_widget_current_changed)

        QTimer.singleShot(0, lambda: self._debug_dump_tab_state("init"))

    def _describe_widget_brief(self, widget):
        """生成简短的 QWidget 调试描述。
        
        Args:
            widget: 要描述的 QWidget 对象
        
        Returns:
            str: 包含类名、对象名、可见性、启用状态和几何信息的描述字符串
        """
        if widget is None:
            return "None"

        try:
            object_name = widget.objectName() or "<no-object-name>"
            geometry = widget.geometry()
            return (
                f"{widget.__class__.__name__}(name={object_name}, "
                f"visible={widget.isVisible()}, enabled={widget.isEnabled()}, "
                f"geom={geometry.getRect()})"
            )
        except RuntimeError:
            return f"{widget.__class__.__name__}(deleted)"

    def _debug_log_tracking_button_state(self, reason: str):
        """打印开始/停止追踪按钮状态，辅助排查文本未刷新的问题。"""
        button = None
        info_widget = getattr(self, "_info_widget", None)
        if info_widget is not None:
            try:
                button = info_widget.get_start_tracking_button()
                self._start_tracking_btn = button
            except RuntimeError:
                button = getattr(self, "_start_tracking_btn", None)
        info_widget = getattr(self, "_info_widget", None)
        try:
            info_button = info_widget.get_start_tracking_button() if info_widget is not None else None
        except RuntimeError:
            info_button = None
        current_tab_index = self._tab_widget.currentIndex() if self._tab_widget is not None else -1
        current_tab_text = self._tab_widget.tabText(current_tab_index) if self._tab_widget is not None and current_tab_index >= 0 else "<none>"

        def _button_state(label, widget):
            if widget is None:
                return f"{label}=None"
            try:
                return (
                    f"{label}=id={id(widget)} text={widget.text()} visible={widget.isVisible()} "
                    f"enabled={widget.isEnabled()} parent={self._describe_widget_brief(widget.parentWidget())}"
                )
            except RuntimeError:
                return f"{label}=deleted"

        print(
            "[TrackingButtonDebug] "
            f"reason={reason} tracking_enabled={self._tracking_enabled} "
            f"current_tab={current_tab_index}:{current_tab_text} "
            f"{_button_state('self_btn', button)} "
            f"{_button_state('info_btn', info_button)}"
        )

    def _resolve_start_tracking_button(self):
        """获取当前仍然有效的开始/停止追踪按钮。"""
        self._refresh_info_tab_widget_refs()
        return self._start_tracking_btn

    def _refresh_info_tab_widget_refs(self):
        """刷新追踪信息页控件引用，避免使用已被 Qt 删除的旧对象。"""
        info_widget = self._info_widget
        self._left_config_label = info_widget.get_config_labels()["left"]
        self._right_config_label = info_widget.get_config_labels()["right"]
        self._left_position_label = info_widget.get_position_labels()["left"]
        self._right_position_label = info_widget.get_position_labels()["right"]
        self._left_rotation_label = info_widget.get_rotation_labels()["left"]
        self._right_rotation_label = info_widget.get_rotation_labels()["right"]
        self._left_quat_label = info_widget.get_quat_labels()["left"]
        self._right_quat_label = info_widget.get_quat_labels()["right"]
        self._left_group = info_widget.get_groups()["left"]
        self._right_group = info_widget.get_groups()["right"]
        self._start_tracking_btn = info_widget.get_start_tracking_button()
        return info_widget

    def _set_config_error_text(self, error_text: str) -> None:
        """安全更新左右手配置标签中的错误信息。"""
        try:
            self._refresh_info_tab_widget_refs()
        except RuntimeError:
            return

        for label in (self._left_config_label, self._right_config_label):
            if label is None or not isValid(label):
                continue
            try:
                label.setText(error_text)
            except RuntimeError:
                continue

    def _debug_dump_tab_state(self, reason: str):
        """打印当前 tab 状态，辅助定位切换异常。"""
        if not self._TAB_DEBUG_ENABLED:
            return

        tab_bar = self._tab_widget.tabBar()
        current_index = self._tab_widget.currentIndex()
        current_widget = self._tab_widget.currentWidget()

        print(f"[TabDebug] reason={reason}")
        print(
            f"[TabDebug] tabWidget currentIndex={current_index} "
            f"count={self._tab_widget.count()} currentWidget={self._describe_widget_brief(current_widget)}"
        )
        print(f"[TabDebug] tabBar={self._describe_widget_brief(tab_bar)}")

        for index in range(self._tab_widget.count()):
            page = self._tab_widget.widget(index)
            label = self._tab_widget.tabText(index)
            page_parent = page.parentWidget().__class__.__name__ if page is not None and page.parentWidget() is not None else "None"
            print(
                f"[TabDebug] tab[{index}] text={label} enabled={self._tab_widget.isTabEnabled(index)} "
                f"visible={page.isVisible() if page is not None else False} "
                f"pageParent={page_parent} page={self._describe_widget_brief(page)}"
            )

        if self._info_widget is not None:
            print(f"[TabDebug] infoWidget={self._describe_widget_brief(self._info_widget)}")
            print(f"[TabDebug] infoWidget.ui={self._describe_widget_brief(self._info_widget.get_ui())}")

        if self._calibration_widget is not None:
            print(f"[TabDebug] calibrationWidget={self._describe_widget_brief(self._calibration_widget)}")

    def _on_tab_bar_clicked(self, index: int):
        """记录 tabBar 点击。"""
        self._debug_dump_tab_state(f"tabBarClicked index={index}")

    def _on_tab_bar_current_changed(self, index: int):
        """记录 tabBar 当前项变化。"""
        self._debug_dump_tab_state(f"tabBar.currentChanged index={index}")

    def _on_tab_widget_current_changed(self, index: int):
        """记录 QTabWidget 当前页变化。"""
        self._sync_tab_refresh_flags(index)
        self._debug_dump_tab_state(f"tabWidget.currentChanged index={index}")

    def _sync_tab_refresh_flags(self, current_index: int) -> None:
        """同步各 tab 页面是否允许执行前台 UI 刷新。"""
        calibration_index = self._cali_tab_manager.get_calibration_tab_index()
        if self._calibration_widget is not None and calibration_index is not None:
            self._calibration_widget.set_front_refresh_enabled(current_index == calibration_index)

    def eventFilter(self, watched, event):
        """拦截 tab 相关事件，辅助定位点击失效问题。"""
        if self._TAB_DEBUG_ENABLED and self._tab_widget is not None:
            tab_bar = self._tab_widget.tabBar()
            event_type = event.type()
            watched_name = watched.__class__.__name__

            if watched is tab_bar and event_type in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
                pos = event.position().toPoint()
                tab_index = tab_bar.tabAt(pos)
                print(
                    f"[TabDebug] event={event_type} watched=QTabBar pos=({pos.x()},{pos.y()}) "
                    f"tabAt={tab_index} currentIndex={self._tab_widget.currentIndex()}"
                )
            elif watched is self._tab_widget and event_type in (QEvent.Resize, QEvent.Show):
                self._debug_dump_tab_state(f"QTabWidget event={event_type}")
            elif event_type in (QEvent.Show, QEvent.Hide, QEvent.Resize):
                for index in range(self._tab_widget.count()):
                    if watched is self._tab_widget.widget(index):
                        print(
                            f"[TabDebug] pageEvent tab={index} text={self._tab_widget.tabText(index)} "
                            f"event={event_type} watched={watched_name} geom={watched.geometry().getRect()}"
                        )
                        break

        return super().eventFilter(watched, event)

    def _init_bias_controls(self):
        """兼容旧接口：当前 widget 不再维护隐藏的偏差控件树。"""
        return

    def _on_set_left_bias(self):
        """兼容旧接口：转发到持久化的追踪信息页。"""
        if self._info_widget is not None:
            self._info_widget._on_set_left_bias()

    def _on_set_right_bias(self):
        """兼容旧接口：转发到持久化的追踪信息页。"""
        if self._info_widget is not None:
            self._info_widget._on_set_right_bias()

    def _set_steamvr_status(self, running: bool):
        """更新 SteamVR 状态标签。使用 InfoTabManager 处理。
        
        Args:
            running: True 表示 SteamVR 已启动，False 表示未启动
        """
        self._info_tab_manager.set_steamvr_status(running)

    def _on_steamvr_status_changed(self, running: bool):
        """SteamVR 状态改变回调。
        
        Args:
            running: True 表示 SteamVR 已启动，False 表示未启动
        """
        self._set_steamvr_status(running)

    def _load_config(self):
        """从 JSON 文件加载配置。使用 InfoTabManager 处理。"""
        self._info_tab_manager.load_config()

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
        """左手 GroupBox 的右键菜单（欧拉角/四元数显示切换）。
        
        Args:
            pos: 右键点击位置
        """
        menu = QMenu(self)
        
        euler_action = menu.addAction("显示欧拉角" if self._left_show_quat else "✓ 显示欧拉角")
        quat_action = menu.addAction("✓ 显示四元数" if self._left_show_quat else "显示四元数")
        
        action = menu.exec(QCursor.pos())
        
        if action == euler_action:
            self._left_show_quat = False
        elif action == quat_action:
            self._left_show_quat = True
        self._left_rotation_label.setVisible(True)
        self._left_quat_label.setVisible(True)

    def _on_right_group_context_menu(self, pos):
        """右手 GroupBox 的右键菜单（欧拉角/四元数显示切换）。
        
        Args:
            pos: 右键点击位置
        """
        menu = QMenu(self)
        
        euler_action = menu.addAction("显示欧拉角" if self._right_show_quat else "✓ 显示欧拉角")
        quat_action = menu.addAction("✓ 显示四元数" if self._right_show_quat else "显示四元数")
        
        action = menu.exec(QCursor.pos())
        
        if action == euler_action:
            self._right_show_quat = False
        elif action == quat_action:
            self._right_show_quat = True
        self._right_rotation_label.setVisible(True)
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
                self._info_widget.set_groupbox_online_status("left", is_online)
                
                # 处理模型加载/卸载
                if is_online and self._renderer is not None and self._model_load_callback is not None:
                    try:
                        self._model_load_callback("left", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 加载左手模型失败：{e}")
                elif not is_online and self._renderer is not None and self._model_unload_callback is not None:
                    self.remove_left_tracker_attach_axis()
                    try:
                        self._model_unload_callback("left", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 卸载左手模型失败：{e}")
        elif side == "right":
            if self._right_online_state != is_online:
                self._right_online_state = is_online
                status_str = "上线" if is_online else "离线"
                print(f"[TrackerStatus] 右手 Tracker {status_str}")
                self._info_widget.set_groupbox_online_status("right", is_online)
                
                # 处理模型加载/卸载
                if is_online and self._renderer is not None and self._model_load_callback is not None:
                    try:
                        self._model_load_callback("right", self._renderer)
                    except Exception as e:
                        print(f"[ModelCallback] 加载右手模型失败：{e}")
                elif not is_online and self._renderer is not None and self._model_unload_callback is not None:
                    self.remove_right_tracker_attach_axis()
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
        actor = self._tracker_model_actors.get(side)
        axes_actor = self._tracker_axes_actors.get(side)
        has_attach_axis = (
            (side == "left" and self._left_tracker_attach_axis_actor is not None)
            or (side == "right" and self._right_tracker_attach_axis_actor is not None)
        )
        if actor is None and axes_actor is None and not has_attach_axis:
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
                
                # 计算最终位置（原始位置 + 偏差，并按需应用 quat_calibration 旋转）
                if tracker_data is not None:
                    final_position = self.compose_tracker_data_display_position_xyz(tracker_data)
                else:
                    final_position = position_xyz
            
            # 转换四元数格式从 (w, x, y, z) 到 (x, y, z, w)
            qx, qy, qz, qw = quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]
            
            # 更新追踪器 3D 模型的位置和旋转（使用带偏差的最终位置）
            if actor is not None:
                actor.set_position_and_rotation(final_position, (qx, qy, qz, qw))
            
            # 同时更新坐标轴的位置和旋转
            if axes_actor is not None:
                try:
                    # ── 变化检测：检查位置和旋转是否改变 ────────────────
                    last_pose = self._last_axes_pose.get(side)
                    current_pose = (final_position, quat_wxyz)
                    
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

            if side == "left" and self._left_tracker_attach_axis_actor is not None:
                try:
                    self._update_left_tracker_attach_axis_pose(final_position, quat_wxyz)
                except Exception as e:
                    print(f"[ModelPose] ⚠ 左手附加点坐标轴更新警告：{e}")
            elif side == "right" and self._right_tracker_attach_axis_actor is not None:
                try:
                    self._update_right_tracker_attach_axis_pose(final_position, quat_wxyz)
                except Exception as e:
                    print(f"[ModelPose] ⚠ 右手附加点坐标轴更新警告：{e}")
                        
        except Exception as e:
            print(f"[ModelPose] 更新 {side} 模型位置失败：{e}")

    @staticmethod
    def _normalize_quaternion_wxyz(quat_wxyz: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        """标准化四元数（单位四元数）。
        
        Args:
            quat_wxyz: 输入四元数 (w, x, y, z)
        
        Returns:
            tuple: 标准化后的四元数 (w, x, y, z)。若输入长度过小则返回单位四元数 (1.0, 0.0, 0.0, 0.0)
        """
        w, x, y, z = quat_wxyz
        norm = (w * w + x * x + y * y + z * z) ** 0.5
        if norm <= 1e-8:
            return (1.0, 0.0, 0.0, 0.0)
        return (w / norm, x / norm, y / norm, z / norm)

    @staticmethod
    def _multiply_quaternion_wxyz(
        lhs_wxyz: tuple[float, float, float, float],
        rhs_wxyz: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """四元数乘法运算。
        
        Args:
            lhs_wxyz: 左操作数四元数 (w, x, y, z)
            rhs_wxyz: 右操作数四元数 (w, x, y, z)
        
        Returns:
            tuple: 乘法结果四元数 (w, x, y, z)
        """
        lw, lx, ly, lz = lhs_wxyz
        rw, rx, ry, rz = rhs_wxyz
        return (
            lw * rw - lx * rx - ly * ry - lz * rz,
            lw * rx + lx * rw + ly * rz - lz * ry,
            lw * ry - lx * rz + ly * rw + lz * rx,
            lw * rz + lx * ry - ly * rx + lz * rw,
        )

    @classmethod
    def invert_quaternion_wxyz(cls, quat_wxyz: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        """四元数取逆（共轭）。
        
        Args:
            quat_wxyz: 输入四元数 (w, x, y, z)
        
        Returns:
            tuple: 逆四元数 (w, -x, -y, -z)（已标准化）
        """
        qw, qx, qy, qz = cls._normalize_quaternion_wxyz(quat_wxyz)
        return (qw, -qx, -qy, -qz)

    @classmethod
    def rotate_vector_by_quaternion_wxyz(
        cls,
        vector_xyz: tuple[float, float, float],
        quat_wxyz: tuple[float, float, float, float],
    ) -> tuple[float, float, float]:
        """使用四元数旋转三维向量。

        计算方式：q × (0, v) × inverse(q)
        """
        normalized_quat = cls._normalize_quaternion_wxyz(quat_wxyz)
        vector_quat = (0.0, vector_xyz[0], vector_xyz[1], vector_xyz[2])
        rotated_vector_quat = cls._multiply_quaternion_wxyz(
            cls._multiply_quaternion_wxyz(normalized_quat, vector_quat),
            cls.invert_quaternion_wxyz(normalized_quat),
        )
        return (
            rotated_vector_quat[1],
            rotated_vector_quat[2],
            rotated_vector_quat[3],
        )

    @classmethod
    def apply_calibration_quaternion_wxyz(
        cls,
        calibration_quat_wxyz: tuple[float, float, float, float],
        realtime_quat_wxyz: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """应用校准四元数到实时四元数。
        
        计算方式：calibration_quat × realtime_quat
        
        Args:
            calibration_quat_wxyz: 校准四元数 (w, x, y, z)
            realtime_quat_wxyz: 实时四元数 (w, x, y, z)
        
        Returns:
            tuple: 校准后的四元数 (w, x, y, z)（已标准化）
        """
        calibrated = cls._multiply_quaternion_wxyz(
            cls._normalize_quaternion_wxyz(calibration_quat_wxyz),
            cls._normalize_quaternion_wxyz(realtime_quat_wxyz),
        )
        return cls._normalize_quaternion_wxyz(calibrated)

    @classmethod
    def compose_display_quaternion_wxyz(
        cls,
        additional_quat_wxyz: tuple[float, float, float, float],
        calibration_quat_wxyz: tuple[float, float, float, float],
        realtime_quat_wxyz: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """组合最终用于界面显示和 VTK 的四元数。

        计算方式：quat_additional × inverse(quat_calibration) × quat_origin
        """
        display_quat = cls._multiply_quaternion_wxyz(
            cls._normalize_quaternion_wxyz(additional_quat_wxyz),
            cls._multiply_quaternion_wxyz(
                cls.invert_quaternion_wxyz(calibration_quat_wxyz),
                cls._normalize_quaternion_wxyz(realtime_quat_wxyz),
            ),
        )
        return cls._normalize_quaternion_wxyz(display_quat)

    def _get_tracker_position_bias_quaternion_wxyz_unlocked(self) -> tuple[float, float, float, float]:
        """获取用于位置旋转的四元数偏置。"""
        return self._tracker_cali_manager.get_location_bias_quaternion_wxyz()

    def _get_tracker_additional_quaternion_wxyz_unlocked(self) -> tuple[float, float, float, float]:
        """获取用于姿态显示的附加旋转四元数。"""
        return self._tracker_cali_manager.get_additional_quaternion_wxyz()

    def _get_tracker_position_bias_xyz_unlocked(self) -> tuple[float, float, float]:
        """获取对所有 Vive Tracker 共享的位置偏差。"""
        return self._tracker_cali_manager.get_position_bias_xyz()

    def compose_display_position_xyz(
        self,
        position_xyz: tuple[float, float, float],
        bias_xyz: tuple[float, float, float],
        location_bias_quat_wxyz: tuple[float, float, float, float],
    ) -> tuple[float, float, float]:
        """计算最终用于界面显示和模型更新的位置。"""
        translated_position = (
            position_xyz[0] + bias_xyz[0],
            position_xyz[1] + bias_xyz[1],
            position_xyz[2] + bias_xyz[2],
        )
        if not self._calibration_active or not self._rotate_position_by_calibration:
            return translated_position
        return self.rotate_vector_by_quaternion_wxyz(translated_position, location_bias_quat_wxyz)

    def compose_tracker_data_display_position_xyz(
        self,
        tracker_data: TrackerData,
    ) -> tuple[float, float, float]:
        """基于 TrackerData 计算最终用于界面显示和模型更新的位置。"""
        position_bias_xyz = self._get_tracker_position_bias_xyz_unlocked()
        return self.compose_display_position_xyz(
            (
                tracker_data.pos_origin_x_m,
                tracker_data.pos_origin_y_m,
                tracker_data.pos_origin_z_m,
            ),
            position_bias_xyz,
            self._get_tracker_position_bias_quaternion_wxyz_unlocked(),
        )

    def compose_tracker_data_display_quaternion_wxyz(
        self,
        tracker_data: TrackerData,
    ) -> tuple[float, float, float, float]:
        """基于 TrackerData 计算最终用于界面显示和 VTK 的四元数。"""
        realtime_quat = (
            tracker_data.quat_origin_w,
            tracker_data.quat_origin_x,
            tracker_data.quat_origin_y,
            tracker_data.quat_origin_z,
        )
        if not self._calibration_active:
            return self._normalize_quaternion_wxyz(realtime_quat)

        return self.compose_display_quaternion_wxyz(
            self._get_tracker_additional_quaternion_wxyz_unlocked(),
            (
                tracker_data.quat_calibration_w,
                tracker_data.quat_calibration_x,
                tracker_data.quat_calibration_y,
                tracker_data.quat_calibration_z,
            ),
            realtime_quat,
        )

    def set_calibration_active(self, active: bool) -> None:
        """设置是否启用标定姿态补偿。"""
        self._calibration_active = active

    def set_position_calibration_rotation_enabled(self, enabled: bool) -> None:
        """设置是否启用基于 quat_calibration 的位置向量旋转。"""
        self._rotate_position_by_calibration = enabled

    def is_position_calibration_rotation_enabled(self) -> bool:
        """返回是否启用基于 quat_calibration 的位置向量旋转。"""
        return self._rotate_position_by_calibration

    def get_tracker_cali_manager(self) -> TrackerCaliManager:
        """返回全局 Tracker 标定偏移管理器。"""
        return self._tracker_cali_manager

    def get_left_calibration_quaternion_wxyz(self) -> tuple[float, float, float, float]:
        """获取左手校准四元数（线程安全）。
        
        Returns:
            tuple: 校准四元数 (w, x, y, z)
        """
        with self._data_lock:
            return (
                self._left_data.quat_calibration_w,
                self._left_data.quat_calibration_x,
                self._left_data.quat_calibration_y,
                self._left_data.quat_calibration_z,
            )

    def get_left_calibrated_quaternion_wxyz(self) -> tuple[float, float, float, float]:
        """获取左手已校准的四元数（线程安全）。
        
        计算方式：quat_additional × inverse(quat_calibration) × quat_origin
        
        Returns:
            tuple: 已校准的四元数 (w, x, y, z)
        """
        with self._data_lock:
            return self.compose_tracker_data_display_quaternion_wxyz(self._left_data)
    
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

    def has_left_tracker_attach_axis(self) -> bool:
        """返回左手附加点坐标轴是否已创建。"""
        return self._left_tracker_attach_axis_actor is not None

    def has_right_tracker_attach_axis(self) -> bool:
        """返回右手附加点坐标轴是否已创建。"""
        return self._right_tracker_attach_axis_actor is not None

    def get_left_tracker_attach_axis_offset_xyz(self) -> tuple[float, float, float]:
        """返回左手附加点的本地偏移量。"""
        return self._left_tracker_attach_axis_offset_xyz

    def get_left_tracker_attach_axis_local_rotation_xyz_degrees(self) -> tuple[float, float, float]:
        """返回左手附加点的本地 XYZ 旋转角度。"""
        return self._left_tracker_attach_axis_local_rotation_xyz_degrees

    def get_right_tracker_attach_axis_offset_xyz(self) -> tuple[float, float, float]:
        """返回右手附加点的本地偏移量。"""
        return self._right_tracker_attach_axis_offset_xyz

    def get_right_tracker_attach_axis_local_rotation_xyz_degrees(self) -> tuple[float, float, float]:
        """返回右手附加点的本地 XYZ 旋转角度。"""
        return self._right_tracker_attach_axis_local_rotation_xyz_degrees

    def set_left_tracker_attach_axis_offset_xyz(self, offset_xyz: tuple[float, float, float]) -> None:
        """设置左手附加点的本地偏移量。"""
        self._left_tracker_attach_axis_offset_xyz = (
            float(offset_xyz[0]),
            float(offset_xyz[1]),
            float(offset_xyz[2]),
        )
        self._last_left_attach_axis_pose = None

        tracker_position: tuple[float, float, float] | None = None
        tracker_quat: tuple[float, float, float, float] | None = None
        with self._data_lock:
            has_valid_pose = self._left_data.valid
            if has_valid_pose:
                tracker_position = self.compose_tracker_data_display_position_xyz(self._left_data)
                tracker_quat = self.compose_tracker_data_display_quaternion_wxyz(self._left_data)

        if self._left_tracker_attach_axis_actor is not None and tracker_position is not None and tracker_quat is not None:
            self._update_left_tracker_attach_axis_pose(tracker_position, tracker_quat, force=True)

        cali_apply_widget = self._cali_apply_tab_manager.get_cali_apply_widget()
        if cali_apply_widget is not None and hasattr(cali_apply_widget, "sync_left_attach_axis_offset_values"):
            cali_apply_widget.sync_left_attach_axis_offset_values()

    def get_left_tracker_attach_axis_local_rotation_quaternion_wxyz(self) -> tuple[float, float, float, float]:
        """返回左手附加点本地 XYZ 旋转对应的四元数。"""
        rotation_xyz = self._left_tracker_attach_axis_local_rotation_xyz_degrees
        return quaternion_from_euler_xyz_degrees_wxyz(
            rotation_xyz[0],
            rotation_xyz[1],
            rotation_xyz[2],
        )

    def set_left_tracker_attach_axis_local_rotation_xyz_degrees(
        self,
        rotation_xyz_degrees: tuple[float, float, float],
    ) -> None:
        """设置左手附加点的本地 XYZ 旋转角度。"""
        self._left_tracker_attach_axis_local_rotation_xyz_degrees = (
            max(0.0, min(360.0, float(rotation_xyz_degrees[0]))),
            max(0.0, min(360.0, float(rotation_xyz_degrees[1]))),
            max(0.0, min(360.0, float(rotation_xyz_degrees[2]))),
        )
        self._last_left_attach_axis_pose = None

        tracker_position: tuple[float, float, float] | None = None
        tracker_quat: tuple[float, float, float, float] | None = None
        with self._data_lock:
            has_valid_pose = self._left_data.valid
            if has_valid_pose:
                tracker_position = self.compose_tracker_data_display_position_xyz(self._left_data)
                tracker_quat = self.compose_tracker_data_display_quaternion_wxyz(self._left_data)

        if self._left_tracker_attach_axis_actor is not None and tracker_position is not None and tracker_quat is not None:
            self._update_left_tracker_attach_axis_pose(tracker_position, tracker_quat, force=True)
        elif self._render_request_callback is not None:
            self._render_request_callback()

        cali_apply_widget = self._cali_apply_tab_manager.get_cali_apply_widget()
        if cali_apply_widget is not None and hasattr(cali_apply_widget, "sync_left_attach_axis_rotation_values"):
            cali_apply_widget.sync_left_attach_axis_rotation_values()

    def set_right_tracker_attach_axis_offset_xyz(self, offset_xyz: tuple[float, float, float]) -> None:
        """设置右手附加点的本地偏移量。"""
        self._right_tracker_attach_axis_offset_xyz = (
            float(offset_xyz[0]),
            float(offset_xyz[1]),
            float(offset_xyz[2]),
        )
        self._last_right_attach_axis_pose = None

        tracker_position: tuple[float, float, float] | None = None
        tracker_quat: tuple[float, float, float, float] | None = None
        with self._data_lock:
            has_valid_pose = self._right_data.valid
            if has_valid_pose:
                tracker_position = self.compose_tracker_data_display_position_xyz(self._right_data)
                tracker_quat = self.compose_tracker_data_display_quaternion_wxyz(self._right_data)

        if self._right_tracker_attach_axis_actor is not None and tracker_position is not None and tracker_quat is not None:
            self._update_right_tracker_attach_axis_pose(tracker_position, tracker_quat, force=True)

        cali_apply_widget = self._cali_apply_tab_manager.get_cali_apply_widget()
        if cali_apply_widget is not None and hasattr(cali_apply_widget, "sync_right_attach_axis_offset_values"):
            cali_apply_widget.sync_right_attach_axis_offset_values()

    def get_right_tracker_attach_axis_local_rotation_quaternion_wxyz(self) -> tuple[float, float, float, float]:
        """返回右手附加点本地 XYZ 旋转对应的四元数。"""
        rotation_xyz = self._right_tracker_attach_axis_local_rotation_xyz_degrees
        return quaternion_from_euler_xyz_degrees_wxyz(
            rotation_xyz[0],
            rotation_xyz[1],
            rotation_xyz[2],
        )

    def set_right_tracker_attach_axis_local_rotation_xyz_degrees(
        self,
        rotation_xyz_degrees: tuple[float, float, float],
    ) -> None:
        """设置右手附加点的本地 XYZ 旋转角度。"""
        self._right_tracker_attach_axis_local_rotation_xyz_degrees = (
            max(0.0, min(360.0, float(rotation_xyz_degrees[0]))),
            max(0.0, min(360.0, float(rotation_xyz_degrees[1]))),
            max(0.0, min(360.0, float(rotation_xyz_degrees[2]))),
        )
        self._last_right_attach_axis_pose = None

        tracker_position: tuple[float, float, float] | None = None
        tracker_quat: tuple[float, float, float, float] | None = None
        with self._data_lock:
            has_valid_pose = self._right_data.valid
            if has_valid_pose:
                tracker_position = self.compose_tracker_data_display_position_xyz(self._right_data)
                tracker_quat = self.compose_tracker_data_display_quaternion_wxyz(self._right_data)

        if self._right_tracker_attach_axis_actor is not None and tracker_position is not None and tracker_quat is not None:
            self._update_right_tracker_attach_axis_pose(tracker_position, tracker_quat, force=True)
        elif self._render_request_callback is not None:
            self._render_request_callback()

        cali_apply_widget = self._cali_apply_tab_manager.get_cali_apply_widget()
        if cali_apply_widget is not None and hasattr(cali_apply_widget, "sync_right_attach_axis_rotation_values"):
            cali_apply_widget.sync_right_attach_axis_rotation_values()

    def create_left_tracker_attach_axis(self) -> bool:
        """创建左手 Vive Tracker 附加点坐标轴。"""
        if self._renderer is None:
            print("[AttachAxis] VTK 渲染器不可用，无法创建左手附加点")
            return False

        with self._data_lock:
            if not self._left_data.valid:
                print("[AttachAxis] 左手 Vive Tracker 当前无有效数据，未创建附加点")
                return False
            tracker_position = self.compose_tracker_data_display_position_xyz(self._left_data)
            tracker_quat = self.compose_tracker_data_display_quaternion_wxyz(self._left_data)

        if self._left_tracker_attach_axis_actor is None:
            actor = build_vive_tracker_attach_axis_actor()
            self._renderer.AddActor(actor)
            self._left_tracker_attach_axis_actor = actor

        self._left_tracker_attach_axis_enabled = True
        self._update_left_tracker_attach_axis_pose(tracker_position, tracker_quat, force=True)
        self._sync_left_tracker_attach_axis_button_state()

        if self._render_request_callback is not None:
            self._render_request_callback()
        return True

    def create_right_tracker_attach_axis(self) -> bool:
        """创建右手 Vive Tracker 附加点坐标轴。"""
        if self._renderer is None:
            print("[AttachAxis] VTK 渲染器不可用，无法创建右手附加点")
            return False

        with self._data_lock:
            if not self._right_data.valid:
                print("[AttachAxis] 右手 Vive Tracker 当前无有效数据，未创建附加点")
                return False
            tracker_position = self.compose_tracker_data_display_position_xyz(self._right_data)
            tracker_quat = self.compose_tracker_data_display_quaternion_wxyz(self._right_data)

        if self._right_tracker_attach_axis_actor is None:
            actor = build_vive_tracker_attach_axis_actor()
            self._renderer.AddActor(actor)
            self._right_tracker_attach_axis_actor = actor

        self._right_tracker_attach_axis_enabled = True
        self._update_right_tracker_attach_axis_pose(tracker_position, tracker_quat, force=True)
        self._sync_right_tracker_attach_axis_button_state()

        if self._render_request_callback is not None:
            self._render_request_callback()
        return True

    def remove_left_tracker_attach_axis(self) -> bool:
        """移除左手 Vive Tracker 附加点坐标轴。"""
        actor = self._left_tracker_attach_axis_actor
        if actor is None:
            self._left_tracker_attach_axis_enabled = False
            self._sync_left_tracker_attach_axis_button_state()
            return False

        if self._renderer is not None:
            try:
                self._renderer.RemoveActor(actor)
            except Exception as e:
                print(f"[AttachAxis] 移除左手附加点失败：{e}")

        self._left_tracker_attach_axis_actor = None
        self._left_tracker_attach_axis_enabled = False
        self._left_attach_axis_transform_cache = None
        self._left_attach_axis_matrix_cache = None
        self._last_left_attach_axis_pose = None
        self._sync_left_tracker_attach_axis_button_state()

        if self._render_request_callback is not None:
            self._render_request_callback()
        return True

    def remove_right_tracker_attach_axis(self) -> bool:
        """移除右手 Vive Tracker 附加点坐标轴。"""
        actor = self._right_tracker_attach_axis_actor
        if actor is None:
            self._right_tracker_attach_axis_enabled = False
            self._sync_right_tracker_attach_axis_button_state()
            return False

        if self._renderer is not None:
            try:
                self._renderer.RemoveActor(actor)
            except Exception as e:
                print(f"[AttachAxis] 移除右手附加点失败：{e}")

        self._right_tracker_attach_axis_actor = None
        self._right_tracker_attach_axis_enabled = False
        self._right_attach_axis_transform_cache = None
        self._right_attach_axis_matrix_cache = None
        self._last_right_attach_axis_pose = None
        self._sync_right_tracker_attach_axis_button_state()

        if self._render_request_callback is not None:
            self._render_request_callback()
        return True

    def _sync_left_tracker_attach_axis_button_state(self) -> None:
        """同步应用定位页中左手附加点按钮的文本。"""
        cali_apply_widget = self._cali_apply_tab_manager.get_cali_apply_widget()
        if cali_apply_widget is not None and hasattr(cali_apply_widget, "sync_left_attach_axis_button_text"):
            cali_apply_widget.sync_left_attach_axis_button_text()

    def _compose_left_tracker_attach_axis_pose(
        self,
        tracker_position_xyz: tuple[float, float, float],
        tracker_quat_wxyz: tuple[float, float, float, float],
    ) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
        """组合左手附加点最终姿态。"""
        return compose_vive_tracker_attach_axis_pose(
            tracker_position_xyz,
            tracker_quat_wxyz,
            self._left_tracker_attach_axis_offset_xyz,
            self.get_left_tracker_attach_axis_local_rotation_quaternion_wxyz(),
        )

    def _sync_right_tracker_attach_axis_button_state(self) -> None:
        """同步应用定位页中右手附加点按钮的文本。"""
        cali_apply_widget = self._cali_apply_tab_manager.get_cali_apply_widget()
        if cali_apply_widget is not None and hasattr(cali_apply_widget, "sync_right_attach_axis_button_text"):
            cali_apply_widget.sync_right_attach_axis_button_text()

    def _compose_right_tracker_attach_axis_pose(
        self,
        tracker_position_xyz: tuple[float, float, float],
        tracker_quat_wxyz: tuple[float, float, float, float],
    ) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
        """组合右手附加点最终姿态。"""
        return compose_vive_tracker_attach_axis_pose(
            tracker_position_xyz,
            tracker_quat_wxyz,
            self._right_tracker_attach_axis_offset_xyz,
            self.get_right_tracker_attach_axis_local_rotation_quaternion_wxyz(),
        )

    def _update_left_tracker_attach_axis_pose(
        self,
        tracker_position_xyz: tuple[float, float, float],
        tracker_quat_wxyz: tuple[float, float, float, float],
        force: bool = False,
    ) -> None:
        """更新左手附加点坐标轴的位置和姿态。"""
        if not self._left_tracker_attach_axis_enabled or self._left_tracker_attach_axis_actor is None:
            return

        attach_position_xyz, attach_quat_wxyz = self._compose_left_tracker_attach_axis_pose(
            tracker_position_xyz,
            tracker_quat_wxyz,
        )
        current_pose = (attach_position_xyz, attach_quat_wxyz)

        if not force and self._last_left_attach_axis_pose == current_pose:
            return

        self._last_left_attach_axis_pose = current_pose
        self._left_attach_axis_matrix_cache, self._left_attach_axis_transform_cache = apply_pose_to_prop_assembly(
            self._left_tracker_attach_axis_actor,
            attach_position_xyz,
            attach_quat_wxyz,
            self._left_attach_axis_matrix_cache,
            self._left_attach_axis_transform_cache,
        )

        if self._render_request_callback is not None:
            self._render_request_callback()

    def _update_right_tracker_attach_axis_pose(
        self,
        tracker_position_xyz: tuple[float, float, float],
        tracker_quat_wxyz: tuple[float, float, float, float],
        force: bool = False,
    ) -> None:
        """更新右手附加点坐标轴的位置和姿态。"""
        if not self._right_tracker_attach_axis_enabled or self._right_tracker_attach_axis_actor is None:
            return

        attach_position_xyz, attach_quat_wxyz = self._compose_right_tracker_attach_axis_pose(
            tracker_position_xyz,
            tracker_quat_wxyz,
        )
        current_pose = (attach_position_xyz, attach_quat_wxyz)

        if not force and self._last_right_attach_axis_pose == current_pose:
            return

        self._last_right_attach_axis_pose = current_pose
        self._right_attach_axis_matrix_cache, self._right_attach_axis_transform_cache = apply_pose_to_prop_assembly(
            self._right_tracker_attach_axis_actor,
            attach_position_xyz,
            attach_quat_wxyz,
            self._right_attach_axis_matrix_cache,
            self._right_attach_axis_transform_cache,
        )

        if self._render_request_callback is not None:
            self._render_request_callback()
    
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
        self.remove_left_tracker_attach_axis()
        self.remove_right_tracker_attach_axis()
        for side in ["left", "right"]:
            if self._model_unload_callback is not None and self._renderer is not None:
                try:
                    self._model_unload_callback(side, self._renderer)
                except Exception as e:
                    print(f"[UnloadTrackers] 卸载 {side} 手模型失败：{e}")

    def _sync_start_tracking_button_text(self):
        """根据当前追踪状态同步按钮文案。"""
        self._debug_log_tracking_button_state("sync_before")
        self._resolve_start_tracking_button().setText("停止追踪" if self._tracking_enabled else "开始追踪")
        self._debug_log_tracking_button_state("sync_after")

    def _on_start_tracking_clicked(self):
        """处理 "开启追踪" 按钮点击。"""
        self._debug_log_tracking_button_state("click_entry")
        if not self._tracking_enabled:
            start_success = self._start_tracking()
            if start_success:
                self._debug_log_tracking_button_state("click_start_success_before_sync")
                self._sync_start_tracking_button_text()
            else:
                self._resolve_start_tracking_button().setText("开始追踪")
                self._debug_log_tracking_button_state("click_start_failed")
        else:
            self._debug_log_tracking_button_state("click_stop_before_stop_tracking")
            self._stop_tracking()
            self._debug_log_tracking_button_state("click_stop_after_stop_tracking")

    def _start_tracking(self):
        """启动追踪。
        
        初始化 OpenVR 系统，从配置中查找并匹配左右手追踪器，
        启动后台数据收集线程和 UI 更新定时器。
        
        会打印设备扫描信息和匹配结果。如果初始化失败或未找到设备，
        会在 UI 中显示错误信息并返回。
        """
        try:
            from triad_openvr.triad_openvr import triad_openvr
            self._openvr_system = triad_openvr()
        except Exception as e:
            error_text = f"<font color='red'><b>OpenVR 初始化失败</b></font><br>{e}"
            self._set_config_error_text(error_text)
            print(f"[StartTracking] 启动失败：OpenVR 初始化异常: {e}")
            return False

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
                
                # 只有配置了序列号才进行匹配
                if left_serial and serial == left_serial:
                    self._devices["left"] = device
                    debug_lines.append(f"    ✓ 左手匹配")
                    print(f"[StartTracking] 左手设备已匹配: {serial}")
                elif right_serial and serial == right_serial:
                    self._devices["right"] = device
                    debug_lines.append(f"    ✓ 右手匹配")
                    print(f"[StartTracking] 右手设备已匹配: {serial}")
            except Exception as e:
                debug_lines.append(f"  {device_name}: 读取失败 - {e}")
                print(f"[StartTracking] 读取设备失败: {e}")
        
        debug_text = "\n".join(debug_lines)
        self._info_tab_manager.set_connection_status_text(debug_text)
        print(
            f"[StartTracking] 扫描完成：matched_left={'left' in self._devices} "
            f"matched_right={'right' in self._devices} total_matched={len(self._devices)}"
        )
        
        if not self._devices:
            # 检查是否缺少配置
            if not left_serial and not right_serial:
                error_text = "\n\n<font color='red'><b>错误：未配置追踪器序列号</b></font>\n请在 config.json 中配置 LeftHandTracker 和/或 RightHandTracker 的 SerialNumber"
            else:
                error_text = f"\n\n<font color='red'><b>未找到匹配的追踪器</b></font>\n已配置序列号：\nLeft: {left_serial if left_serial else '未配置'}\nRight: {right_serial if right_serial else '未配置'}"
            
            self._info_tab_manager.set_connection_status_text(debug_text + error_text)
            self._openvr_system = None
            print("[StartTracking] 启动失败：未找到任何匹配的追踪器")
            return False

        # 启动后台数据收集线程
        self._tracking_enabled = True
        
        # 不控制tab页面的enable/disable，保持两个tab始终完整可用
        
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

        self._debug_log_tracking_button_state("start_tracking_success_before_return")
        return True

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
        """停止追踪。
        
        关闭 OpenVR 系统，停止后台数据收集线程，
        重置 UI 显示，卸载已加载的 VR 模型，并恢复各种状态。
        触发追踪状态改变回调。
        """
        print("[StopTracking] entry")
        self._debug_log_tracking_button_state("stop_tracking_entry")
        self._tracking_enabled = False
        self._calibration_active = False
        self._left_hand_last_tracker_display_position_xyz = None
        self._right_hand_last_tracker_display_position_xyz = None
        
        # 不控制tab页面的enable/disable，保持两个tab始终完整可用
        
        self._update_timer.stop()
        self._lighthouse_update_timer.stop()
        print("[StopTracking] timers_stopped")
        
        if self._tracking_thread is not None:
            print(f"[StopTracking] joining_thread alive_before={self._tracking_thread.is_alive()}")
            self._thread_stop_event.set()
            self._tracking_thread.join(timeout=1)
            print(f"[StopTracking] joined_thread alive_after={self._tracking_thread.is_alive()}")
            self._tracking_thread = None
        
        self._openvr_system = None
        self._devices = {}
        print("[StopTracking] openvr_cleared")

        if self._tracking_state_changed_callback is not None:
            try:
                self._tracking_state_changed_callback(False)
                print("[StopTracking] state_changed_callback_done")
            except Exception as e:
                print(f"[ViveTrackerWidget] 追踪状态回调失败（stop）：{e}")

        self._refresh_info_tab_widget_refs()
        
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
        current_text = self._info_tab_manager.get_connection_status_plain_text()
        if "\n=== LightHouse" in current_text:
            current_text = current_text[:current_text.index("\n=== LightHouse")]
            self._info_tab_manager.set_connection_status_text(current_text)
        
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
        self._left_quat_label.setVisible(True)
        self._right_rotation_label.setVisible(True)
        self._right_quat_label.setVisible(True)
        print("[StopTracking] ui_reset_done")
        
        self._debug_log_tracking_button_state("stop_tracking_before_sync")
        self._sync_start_tracking_button_text()
        self._debug_log_tracking_button_state("stop_tracking_after_sync")
        
        # 卸载所有 VR 追踪器模型
        self._unload_all_tracker_models()
        print("[StopTracking] unload_models_done")

    def _tracking_loop(self):
        """后台追踪线程，60Hz 数据收集。"""
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

                left_valid = False
                left_position = None
                left_euler = None
                left_quat_wxyz = (1.0, 0.0, 0.0, 0.0)

                right_valid = False
                right_position = None
                right_euler = None
                right_quat_wxyz = (1.0, 0.0, 0.0, 0.0)
                
                # 读取左手数据
                if left_device is not None:
                    try:
                        pose_euler = left_device.get_pose_euler()
                        
                        if pose_euler is not None:
                            x, y, z, yaw, pitch, roll = pose_euler
                            left_position = (x, y, z)
                            left_euler = (yaw, pitch, roll)

                            try:
                                pose_quat = left_device.get_pose_quaternion()
                                if pose_quat is not None and len(pose_quat) == 7:
                                    _x_q, _y_q, _z_q, qw, qx, qy, qz = pose_quat
                                    left_quat_wxyz = (qw, qx, qy, qz)
                            except Exception as e:
                                if first_run:
                                    print(f"[Left] get_pose_quaternion() error: {e}")

                            left_valid = True
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
                            right_position = (x, y, z)
                            right_euler = (yaw, pitch, roll)

                            try:
                                pose_quat = right_device.get_pose_quaternion()
                                if pose_quat is not None and len(pose_quat) == 7:
                                    _x_q, _y_q, _z_q, qw, qx, qy, qz = pose_quat
                                    right_quat_wxyz = (qw, qx, qy, qz)
                            except Exception as e:
                                if first_run:
                                    print(f"[Right] get_pose_quaternion() error: {e}")

                            right_valid = True
                        elif first_run:
                            print(f"[Right] get_pose_euler() returned None")
                    except Exception as e:
                        if first_run:
                            print(f"[Right] Error: {e}")

                with self._data_lock:
                    if left_valid and left_position is not None and left_euler is not None:
                        self._left_data.pos_origin_x_m = left_position[0]
                        self._left_data.pos_origin_y_m = left_position[1]
                        self._left_data.pos_origin_z_m = left_position[2]
                        self._left_data.yaw = left_euler[0]
                        self._left_data.pitch = left_euler[1]
                        self._left_data.roll = left_euler[2]
                        self._left_data.quat_origin_w = left_quat_wxyz[0]
                        self._left_data.quat_origin_x = left_quat_wxyz[1]
                        self._left_data.quat_origin_y = left_quat_wxyz[2]
                        self._left_data.quat_origin_z = left_quat_wxyz[3]
                    self._left_data.valid = left_valid

                    if right_valid and right_position is not None and right_euler is not None:
                        self._right_data.pos_origin_x_m = right_position[0]
                        self._right_data.pos_origin_y_m = right_position[1]
                        self._right_data.pos_origin_z_m = right_position[2]
                        self._right_data.yaw = right_euler[0]
                        self._right_data.pitch = right_euler[1]
                        self._right_data.roll = right_euler[2]
                        self._right_data.quat_origin_w = right_quat_wxyz[0]
                        self._right_data.quat_origin_x = right_quat_wxyz[1]
                        self._right_data.quat_origin_y = right_quat_wxyz[2]
                        self._right_data.quat_origin_z = right_quat_wxyz[3]
                    self._right_data.valid = right_valid
                
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
            current_text = self._info_tab_manager.get_connection_status_plain_text()
            
            # 移除旧的 LightHouse 部分
            if "\n=== LightHouse" in current_text:
                current_text = current_text[:current_text.index("\n=== LightHouse")]
            
            # 添加新的 LightHouse 信息
            updated_text = current_text + new_lighthouse_content
            self._info_tab_manager.set_connection_status_text(updated_text)
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
                left_calibrated_quat = self.compose_tracker_data_display_quaternion_wxyz(self._left_data)
                left_display_position = self.compose_tracker_data_display_position_xyz(self._left_data)
                pos_text = f"位置：X={left_display_position[0]:8.4f}m  Y={left_display_position[1]:8.4f}m  Z={left_display_position[2]:8.4f}m"
                rot_text = f"旋转：Yaw={self._left_data.yaw:7.2f}°  Pitch={self._left_data.pitch:7.2f}°  Roll={self._left_data.roll:7.2f}°"
                quat_text = (
                    f"四元数：w={left_calibrated_quat[0]:8.4f}  x={left_calibrated_quat[1]:8.4f}  "
                    f"y={left_calibrated_quat[2]:8.4f}  z={left_calibrated_quat[3]:8.4f}"
                )
                
                # 使用 InfoTabManager 更新显示
                self._info_tab_manager.update_tracker_display("left", pos_text, rot_text, quat_text, True)
                self._update_groupbox_status("left", True)
                
                # 更新 TrackerManager 中左手 Tracker 的数据
                left_tracker = self._tracker_manager.get_tracker("left")
                if left_tracker is None:
                    left_tracker = self._tracker_manager.register_tracker("left")
                
                left_tracker.is_online = True
                left_tracker.valid = True
                left_tracker.update_position(*left_display_position)
                left_tracker.update_euler(self._left_data.yaw, self._left_data.pitch, self._left_data.roll)
                left_tracker.update_quat(*left_calibrated_quat)
                left_tracker.timestamp = time.time()
                
                # 更新模型位置和旋转
                self.update_model_pose(
                    "left",
                    left_display_position,
                    left_calibrated_quat
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
                right_display_quat = self.compose_tracker_data_display_quaternion_wxyz(self._right_data)
                right_display_position = self.compose_tracker_data_display_position_xyz(self._right_data)
                pos_text = f"位置：X={right_display_position[0]:8.4f}m  Y={right_display_position[1]:8.4f}m  Z={right_display_position[2]:8.4f}m"
                rot_text = f"旋转：Yaw={self._right_data.yaw:7.2f}°  Pitch={self._right_data.pitch:7.2f}°  Roll={self._right_data.roll:7.2f}°"
                quat_text = f"四元数：w={right_display_quat[0]:8.4f}  x={right_display_quat[1]:8.4f}  y={right_display_quat[2]:8.4f}  z={right_display_quat[3]:8.4f}"
                
                # 使用 InfoTabManager 更新显示
                self._info_tab_manager.update_tracker_display("right", pos_text, rot_text, quat_text, True)
                self._update_groupbox_status("right", True)
                
                # 更新 TrackerManager 中右手 Tracker 的数据
                right_tracker = self._tracker_manager.get_tracker("right")
                if right_tracker is None:
                    right_tracker = self._tracker_manager.register_tracker("right")
                
                right_tracker.is_online = True
                right_tracker.valid = True
                right_tracker.update_position(*right_display_position)
                right_tracker.update_euler(self._right_data.yaw, self._right_data.pitch, self._right_data.roll)
                right_tracker.update_quat(*right_display_quat)
                right_tracker.timestamp = time.time()
                
                # 更新模型位置和旋转
                self.update_model_pose(
                    "right",
                    right_display_position,
                    right_display_quat
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
                quat_calibration_w=self._left_data.quat_calibration_w, quat_calibration_x=self._left_data.quat_calibration_x,
                quat_calibration_y=self._left_data.quat_calibration_y, quat_calibration_z=self._left_data.quat_calibration_z,
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
                quat_calibration_w=self._right_data.quat_calibration_w, quat_calibration_x=self._right_data.quat_calibration_x,
                quat_calibration_y=self._right_data.quat_calibration_y, quat_calibration_z=self._right_data.quat_calibration_z,
                valid=True,
            )

    def enable_left_hand_root_follow_tracker(self, enabled: bool) -> bool:
        """设置左手骨架是否整体跟随左手 Vive Tracker。"""
        if enabled and self.get_left_hand_tracker_display_position_xyz() is None:
            return False
        self._left_hand_root_follow_tracker = enabled
        if not enabled:
            self._left_hand_last_tracker_display_position_xyz = None
        if self._render_request_callback is not None:
            self._render_request_callback()
        return True

    def is_left_hand_root_follow_tracker_enabled(self) -> bool:
        """返回左手骨架是否整体跟随左手 Vive Tracker。"""
        return self._left_hand_root_follow_tracker

    def get_left_hand_tracker_display_position_xyz(self) -> tuple[float, float, float] | None:
        """返回左手 Vive Tracker 当前用于显示的最终位置。"""
        tracker_data = self.get_left_tracker_data()
        if tracker_data is not None:
            position_xyz = self.compose_tracker_data_display_position_xyz(tracker_data)
            self._left_hand_last_tracker_display_position_xyz = position_xyz
            return position_xyz
        return self._left_hand_last_tracker_display_position_xyz

    def get_left_tracker_attach_axis_pose(
        self,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float, float]] | None:
        """返回左手附加点当前世界坐标系的位置和四元数。"""
        tracker_data = self.get_left_tracker_data()
        if tracker_data is not None:
            tracker_position_xyz = self.compose_tracker_data_display_position_xyz(tracker_data)
            tracker_quat_wxyz = self.compose_tracker_data_display_quaternion_wxyz(tracker_data)
            return self._compose_left_tracker_attach_axis_pose(
                tracker_position_xyz,
                tracker_quat_wxyz,
            )
        if self._last_left_attach_axis_pose is not None:
            return self._last_left_attach_axis_pose
        return None

    def enable_right_hand_root_follow_tracker(self, enabled: bool) -> bool:
        """设置右手骨架是否整体跟随右手 Vive Tracker。"""
        if enabled and self.get_right_hand_tracker_display_position_xyz() is None:
            return False
        self._right_hand_root_follow_tracker = enabled
        if not enabled:
            self._right_hand_last_tracker_display_position_xyz = None
        if self._render_request_callback is not None:
            self._render_request_callback()
        return True

    def is_right_hand_root_follow_tracker_enabled(self) -> bool:
        """返回右手骨架是否整体跟随右手 Vive Tracker。"""
        return self._right_hand_root_follow_tracker

    def get_right_hand_tracker_display_position_xyz(self) -> tuple[float, float, float] | None:
        """返回右手 Vive Tracker 当前用于显示的最终位置。"""
        tracker_data = self.get_right_tracker_data()
        if tracker_data is not None:
            position_xyz = self.compose_tracker_data_display_position_xyz(tracker_data)
            self._right_hand_last_tracker_display_position_xyz = position_xyz
            return position_xyz
        return self._right_hand_last_tracker_display_position_xyz

    def get_right_tracker_attach_axis_pose(
        self,
    ) -> tuple[tuple[float, float, float], tuple[float, float, float, float]] | None:
        """返回右手附加点当前世界坐标系的位置和四元数。"""
        tracker_data = self.get_right_tracker_data()
        if tracker_data is not None:
            tracker_position_xyz = self.compose_tracker_data_display_position_xyz(tracker_data)
            tracker_quat_wxyz = self.compose_tracker_data_display_quaternion_wxyz(tracker_data)
            return self._compose_right_tracker_attach_axis_pose(
                tracker_position_xyz,
                tracker_quat_wxyz,
            )
        if self._last_right_attach_axis_pose is not None:
            return self._last_right_attach_axis_pose
        return None

    def is_tracking_enabled(self) -> bool:
        """是否处于追踪开启状态。
        
        Returns:
            bool: True 表示追踪已启用，False 表示未启用
        """
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
