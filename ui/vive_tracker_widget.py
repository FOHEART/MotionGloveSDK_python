"""vive_tracker_widget.py
Vive Tracker 配置显示和追踪面板

功能：
- 从 triad_openvr/hand_tracker_config.json 读取配置
- 初始化 OpenVR 系统
- 后台线程以 60Hz 读取追踪数据
- UI 以 30Hz 刷新显示位置和旋转信息

UI 布局定义在 vive_tracker.ui 文件中，可用 Qt Designer 编辑。
"""

import sys
import json
import threading
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QPushButton, QTextEdit
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu

# 导入 SteamVR 状态检查器
from triad_openvr.steamvr_status_checker import SteamVRStatusChecker


@dataclass
class TrackerData:
    """追踪器数据结构。"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    quat_w: float = 0.0
    quat_x: float = 0.0
    quat_y: float = 0.0
    quat_z: float = 0.0
    valid: bool = False


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
        self._renderer = None  # VTK 渲染器引用
        
        # 模型对象引用（用于跟踪已加载的模型）
        self._tracker_model_actors = {}  # {"left": VRTrackerModelActor, "right": VRTrackerModelActor}
        self._tracker_axes_actors = {}   # {"left": vtkPropAssembly, "right": vtkPropAssembly}
        
        # LightHouse 信息缓存（用于检测内容变化）
        self._last_lighthouse_content = None  # 存储上一次的基站信息内容
        
        self._init_ui()
        self._load_config()
        
        # SteamVR 状态检查器（独立运行，1秒检查一次）
        self._steamvr_checker = SteamVRStatusChecker(check_interval=1000)
        self._steamvr_checker.set_status_changed_callback(self._on_steamvr_status_changed)
        self._steamvr_checker.start()
        
        # UI 更新定时器（30Hz，仅在追踪时运行）
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_update_timer)
        self._update_timer.setInterval(33)  # ~30Hz
        
        # LightHouse 信息更新定时器（1Hz，与 SteamVR 检测频率相同）
        self._lighthouse_update_timer = QTimer()
        self._lighthouse_update_timer.timeout.connect(self._update_light_house_info)
        self._lighthouse_update_timer.setInterval(1000)  # 1Hz

    def _init_ui(self):
        """从 UI 文件加载界面。"""
        loader = QUiLoader()
        ui_file = QFile(str(_find_ui_file()))
        
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_find_ui_file()}")
        
        self._ui = loader.load(ui_file)
        ui_file.close()
        
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_find_ui_file()}")
        
        # 将加载的 UI 添加到当前 widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ui)
        
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
    ):
        """设置 VTK 渲染器和模型加载/卸载回调。
        
        Args:
            renderer: VTK 渲染器对象（vtk.vtkRenderer）
            model_load_callback: 模型加载回调函数 (side: str, renderer) -> None
            model_unload_callback: 模型卸载回调函数 (side: str, renderer) -> None
            lighthouse_update_callback: LightHouse 更新回调 (lighthouse_states: list[dict]) -> None
            tracking_state_changed_callback: 追踪状态改变回调 (enabled: bool) -> None
        """
        self._renderer = renderer
        self._model_load_callback = model_load_callback
        self._model_unload_callback = model_unload_callback
        self._lighthouse_update_callback = lighthouse_update_callback
        self._tracking_state_changed_callback = tracking_state_changed_callback
        print("[ViveTrackerWidget] VTK 渲染器和模型回调已设置")
    
    def update_model_pose(self, side: str, position_xyz: tuple, quat_wxyz: tuple):
        """更新模型的位置和旋转（包括坐标轴）。坐标轴会完全跟随模型的位置和旋转。
        
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
            # 转换四元数格式从 (w, x, y, z) 到 (x, y, z, w)
            qx, qy, qz, qw = quat_wxyz[1], quat_wxyz[2], quat_wxyz[3], quat_wxyz[0]
            
            # 添加调试日志（每 30 帧打印一次以减少日志量）
            if hasattr(self, '_model_pose_log_counter'):
                self._model_pose_log_counter = (self._model_pose_log_counter + 1) % 30
            else:
                self._model_pose_log_counter = 0
            
            if self._model_pose_log_counter == 0:
                print(f"[ModelPose] {side}: pos=({position_xyz[0]:.4f}, {position_xyz[1]:.4f}, {position_xyz[2]:.4f}) "
                      f"quat=(w={qw:.4f}, x={qx:.4f}, y={qy:.4f}, z={qz:.4f})")
            
            # 更新追踪器 3D 模型的位置和旋转
            actor.set_position_and_rotation(position_xyz, (qx, qy, qz, qw))
            
            # 同时更新坐标轴的位置和旋转
            axes_actor = self._tracker_axes_actors.get(side)
            if axes_actor is not None:
                try:
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
                    
                    # 创建 4x4 变换矩阵（旋转 + 平移）
                    matrix = vtk.vtkMatrix4x4()
                    
                    # 设置旋转部分 (3x3)
                    matrix.SetElement(0, 0, r11)
                    matrix.SetElement(0, 1, r12)
                    matrix.SetElement(0, 2, r13)
                    matrix.SetElement(0, 3, position_xyz[0])
                    
                    matrix.SetElement(1, 0, r21)
                    matrix.SetElement(1, 1, r22)
                    matrix.SetElement(1, 2, r23)
                    matrix.SetElement(1, 3, position_xyz[1])
                    
                    matrix.SetElement(2, 0, r31)
                    matrix.SetElement(2, 1, r32)
                    matrix.SetElement(2, 2, r33)
                    matrix.SetElement(2, 3, position_xyz[2])
                    
                    # 齐次坐标
                    matrix.SetElement(3, 0, 0.0)
                    matrix.SetElement(3, 1, 0.0)
                    matrix.SetElement(3, 2, 0.0)
                    matrix.SetElement(3, 3, 1.0)
                    
                    # 为 assembly 中的每个 actor 应用相同的变换
                    transform = vtk.vtkTransform()
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
                    
                except Exception as e:
                    # 如果更新坐标轴失败，不要中断模型更新
                    if self._model_pose_log_counter == 0:
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
        
        # 清除基站信息
        self._last_lighthouse_content = None
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
                                self._left_data.x = x
                                self._left_data.y = y
                                self._left_data.z = z
                                self._left_data.yaw = yaw
                                self._left_data.pitch = pitch
                                self._left_data.roll = roll
                                
                                # 尝试读取四元数
                                try:
                                    pose_quat = left_device.get_pose_quaternion()
                                    if pose_quat is not None and len(pose_quat) == 7:
                                        # pose_quat = [x, y, z, qw, qx, qy, qz]
                                        x_q, y_q, z_q, qw, qx, qy, qz = pose_quat
                                        self._left_data.quat_w = qw
                                        self._left_data.quat_x = qx
                                        self._left_data.quat_y = qy
                                        self._left_data.quat_z = qz
                                    else:
                                        self._left_data.quat_w = 1.0
                                        self._left_data.quat_x = 0.0
                                        self._left_data.quat_y = 0.0
                                        self._left_data.quat_z = 0.0
                                except Exception as e:
                                    if first_run:
                                        print(f"[Left] get_pose_quaternion() error: {e}")
                                    self._left_data.quat_w = 1.0
                                    self._left_data.quat_x = 0.0
                                    self._left_data.quat_y = 0.0
                                    self._left_data.quat_z = 0.0
                                
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
                                self._right_data.x = x
                                self._right_data.y = y
                                self._right_data.z = z
                                self._right_data.yaw = yaw
                                self._right_data.pitch = pitch
                                self._right_data.roll = roll
                                
                                # 尝试读取四元数
                                try:
                                    pose_quat = right_device.get_pose_quaternion()
                                    if pose_quat is not None and len(pose_quat) == 7:
                                        # pose_quat = [x, y, z, qw, qx, qy, qz]
                                        x_q, y_q, z_q, qw, qx, qy, qz = pose_quat
                                        self._right_data.quat_w = qw
                                        self._right_data.quat_x = qx
                                        self._right_data.quat_y = qy
                                        self._right_data.quat_z = qz
                                    else:
                                        self._right_data.quat_w = 1.0
                                        self._right_data.quat_x = 0.0
                                        self._right_data.quat_y = 0.0
                                        self._right_data.quat_z = 0.0
                                except Exception as e:
                                    if first_run:
                                        print(f"[Right] get_pose_quaternion() error: {e}")
                                    self._right_data.quat_w = 1.0
                                    self._right_data.quat_x = 0.0
                                    self._right_data.quat_y = 0.0
                                    self._right_data.quat_z = 0.0
                                
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
        """采集基站位姿列表。

        Returns:
            list[dict]: 每个元素包含 id/name/serial/position/quat_wxyz。
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
                lighthouse_states.append({
                    "id": serial or ref_name,
                    "name": ref_name,
                    "serial": serial,
                    "position": (x, y, z),
                    "quat_wxyz": (qw, qx, qy, qz),
                })
            except Exception:
                continue

        return lighthouse_states

    def _update_light_house_info(self):
        """获取并更新 LightHouse 基站信息，显示在 connectionStatusText 中。
        
        只有当内容发生变化时，才会更新 UI。
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
                        device = self._openvr_system.devices.get(ref_name)
                        if device is None:
                            continue
                        
                        try:
                            serial = device.get_serial()
                            if isinstance(serial, bytes):
                                serial = serial.decode('utf-8')
                            
                            # 获取位置和旋转信息
                            pose_euler = device.get_pose_euler()
                            pose_quat = device.get_pose_quaternion()
                            
                            info_lines.append(f"【{ref_name}】 Serial: {serial}")
                            
                            if pose_euler:
                                x, y, z, yaw, pitch, roll = pose_euler
                                info_lines.append(f"  位置: X={x:8.4f}m Y={y:8.4f}m Z={z:8.4f}m")
                                info_lines.append(f"  旋转: Yaw={yaw:7.2f}° Pitch={pitch:7.2f}° Roll={roll:7.2f}°")
                            
                            if pose_quat:
                                x, y, z, qw, qx, qy, qz = pose_quat
                                info_lines.append(f"  四元数: w={qw:8.4f} x={qx:8.4f} y={qy:8.4f} z={qz:8.4f}")
                            
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
        if self._last_lighthouse_content != new_lighthouse_content:
            # 获取当前连接状态文本的前面部分（不含 LightHouse 部分）
            current_text = self._connection_status_text.toPlainText()
            
            # 移除旧的 LightHouse 部分
            if "\n=== LightHouse" in current_text:
                current_text = current_text[:current_text.index("\n=== LightHouse")]
            
            # 添加新的 LightHouse 信息
            updated_text = current_text + new_lighthouse_content
            self._connection_status_text.setText(updated_text)
            self._last_lighthouse_content = new_lighthouse_content

    def _on_update_timer(self):
        """UI 更新定时器回调，30Hz 刷新追踪数据显示。
        
        使用离线计数器：连续20帧无数据才判定为离线，避免频繁切换。
        同时更新模型的位置和旋转。
        """
        tracker_pose_updated = False
        with self._data_lock:
            # 处理左手数据
            if self._left_data.valid:
                # 有有效数据，重置离线计数器
                self._left_offline_counter = 0
                pos_text = f"位置：X={self._left_data.x:8.4f}m  Y={self._left_data.y:8.4f}m  Z={self._left_data.z:8.4f}m"
                rot_text = f"旋转：Yaw={self._left_data.yaw:7.2f}°  Pitch={self._left_data.pitch:7.2f}°  Roll={self._left_data.roll:7.2f}°"
                quat_text = f"四元数：w={self._left_data.quat_w:8.4f}  x={self._left_data.quat_x:8.4f}  y={self._left_data.quat_y:8.4f}  z={self._left_data.quat_z:8.4f}"
                self._left_position_label.setText(pos_text)
                self._left_rotation_label.setText(rot_text)
                self._left_quat_label.setText(quat_text)
                self._update_groupbox_status("left", True)
                
                # 更新模型位置和旋转
                self.update_model_pose(
                    "left",
                    (self._left_data.x, self._left_data.y, self._left_data.z),
                    (self._left_data.quat_w, self._left_data.quat_x, self._left_data.quat_y, self._left_data.quat_z)
                )
                tracker_pose_updated = True
            else:
                # 无有效数据，增加离线计数器
                self._left_offline_counter += 1
                if self._left_offline_counter >= self._offline_threshold:
                    # 连续20帧无数据，标记为离线
                    self._update_groupbox_status("left", False)
            
            # 处理右手数据
            if self._right_data.valid:
                # 有有效数据，重置离线计数器
                self._right_offline_counter = 0
                pos_text = f"位置：X={self._right_data.x:8.4f}m  Y={self._right_data.y:8.4f}m  Z={self._right_data.z:8.4f}m"
                rot_text = f"旋转：Yaw={self._right_data.yaw:7.2f}°  Pitch={self._right_data.pitch:7.2f}°  Roll={self._right_data.roll:7.2f}°"
                quat_text = f"四元数：w={self._right_data.quat_w:8.4f}  x={self._right_data.quat_x:8.4f}  y={self._right_data.quat_y:8.4f}  z={self._right_data.quat_z:8.4f}"
                self._right_position_label.setText(pos_text)
                self._right_rotation_label.setText(rot_text)
                self._right_quat_label.setText(quat_text)
                self._update_groupbox_status("right", True)
                
                # 更新模型位置和旋转
                self.update_model_pose(
                    "right",
                    (self._right_data.x, self._right_data.y, self._right_data.z),
                    (self._right_data.quat_w, self._right_data.quat_x, self._right_data.quat_y, self._right_data.quat_z)
                )
                tracker_pose_updated = True
            else:
                # 无有效数据，增加离线计数器
                self._right_offline_counter += 1
                if self._right_offline_counter >= self._offline_threshold:
                    # 连续20帧无数据，标记为离线
                    self._update_groupbox_status("right", False)

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
                x=self._left_data.x, y=self._left_data.y, z=self._left_data.z,
                yaw=self._left_data.yaw, pitch=self._left_data.pitch, roll=self._left_data.roll,
                quat_w=self._left_data.quat_w, quat_x=self._left_data.quat_x,
                quat_y=self._left_data.quat_y, quat_z=self._left_data.quat_z,
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
                x=self._right_data.x, y=self._right_data.y, z=self._right_data.z,
                yaw=self._right_data.yaw, pitch=self._right_data.pitch, roll=self._right_data.roll,
                quat_w=self._right_data.quat_w, quat_x=self._right_data.quat_x,
                quat_y=self._right_data.quat_y, quat_z=self._right_data.quat_z,
                valid=True,
            )

    def is_tracking_enabled(self) -> bool:
        """是否处于追踪开启状态。"""
        return self._tracking_enabled

    def closeEvent(self, event):
        """窗口关闭时清理资源。"""
        if self._tracking_enabled:
            self._stop_tracking()
        super().closeEvent(event)
