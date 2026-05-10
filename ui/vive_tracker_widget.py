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

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt


@dataclass
class TrackerData:
    """追踪器数据结构。"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
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
        
        self._init_ui()
        self._load_config()
        
        # UI 更新定时器（30Hz）
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_update_timer)
        self._update_timer.setInterval(33)  # ~30Hz

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
        self._start_tracking_btn: QPushButton = self._ui.findChild(QPushButton, "startTrackingButton")
        self._refresh_btn: QPushButton = self._ui.findChild(QPushButton, "refreshButton")
        self._left_group: QGroupBox = self._ui.findChild(QGroupBox, "leftHandGroup")
        self._right_group: QGroupBox = self._ui.findChild(QGroupBox, "rightHandGroup")
        
        # 验证所有必要的控件存在
        assert self._left_config_label is not None, "UI 控件未找到：leftHandConfigInfo"
        assert self._right_config_label is not None, "UI 控件未找到：rightHandConfigInfo"
        assert self._left_position_label is not None, "UI 控件未找到：leftHandPositionLabel"
        assert self._right_position_label is not None, "UI 控件未找到：rightHandPositionLabel"
        assert self._left_rotation_label is not None, "UI 控件未找到：leftHandRotationLabel"
        assert self._right_rotation_label is not None, "UI 控件未找到：rightHandRotationLabel"
        assert self._start_tracking_btn is not None, "UI 控件未找到：startTrackingButton"
        assert self._refresh_btn is not None, "UI 控件未找到：refreshButton"
        
        # 连接信号
        self._start_tracking_btn.clicked.connect(self._on_start_tracking_clicked)
        self._refresh_btn.clicked.connect(self._load_config)

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
        
        # 构建序列号到设备的映射
        for device_name, device in self._openvr_system.devices.items():
            try:
                serial = device.get_serial()
                if isinstance(serial, bytes):
                    serial = serial.decode('utf-8')
                
                if serial == left_serial:
                    self._devices["left"] = device
                elif serial == right_serial:
                    self._devices["right"] = device
            except Exception:
                pass

        if not self._devices:
            error_text = "<font color='red'><b>未找到匹配的追踪器</b></font>"
            self._left_config_label.setText(error_text)
            self._right_config_label.setText(error_text)
            self._openvr_system = None
            return

        # 启动后台数据收集线程
        self._tracking_enabled = True
        self._thread_stop_event.clear()
        self._tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._tracking_thread.start()
        
        # 启动 UI 更新定时器
        self._update_timer.start()
        
        # 更新按钮文本
        self._start_tracking_btn.setText("停止追踪")

    def _stop_tracking(self):
        """停止追踪。"""
        self._tracking_enabled = False
        self._update_timer.stop()
        
        if self._tracking_thread is not None:
            self._thread_stop_event.set()
            self._tracking_thread.join(timeout=1)
            self._tracking_thread = None
        
        self._openvr_system = None
        self._devices = {}
        
        # 重置显示
        self._left_position_label.setText("位置：X= 0.0000m  Y= 0.0000m  Z= 0.0000m")
        self._left_rotation_label.setText("旋转：Yaw= 0.00°  Pitch= 0.00°  Roll= 0.00°")
        self._right_position_label.setText("位置：X= 0.0000m  Y= 0.0000m  Z= 0.0000m")
        self._right_rotation_label.setText("旋转：Yaw= 0.00°  Pitch= 0.00°  Roll= 0.00°")
        
        # 更新按钮文本
        self._start_tracking_btn.setText("开启追踪")

    def _tracking_loop(self):
        """后台追踪线程，60Hz 数据收集。"""
        interval = 1.0 / 60.0  # 60Hz
        
        while not self._thread_stop_event.is_set():
            try:
                left_device = self._devices.get("left")
                right_device = self._devices.get("right")
                
                # 读取左手数据
                if left_device is not None:
                    pose = left_device.get_pose_euler()
                    if pose:
                        x, y, z, yaw, pitch, roll = pose
                        with self._data_lock:
                            self._left_data.x = x
                            self._left_data.y = y
                            self._left_data.z = z
                            self._left_data.yaw = yaw
                            self._left_data.pitch = pitch
                            self._left_data.roll = roll
                            self._left_data.valid = True
                
                # 读取右手数据
                if right_device is not None:
                    pose = right_device.get_pose_euler()
                    if pose:
                        x, y, z, yaw, pitch, roll = pose
                        with self._data_lock:
                            self._right_data.x = x
                            self._right_data.y = y
                            self._right_data.z = z
                            self._right_data.yaw = yaw
                            self._right_data.pitch = pitch
                            self._right_data.roll = roll
                            self._right_data.valid = True
                
                time.sleep(interval)
            except Exception:
                pass

    def _on_update_timer(self):
        """UI 更新定时器回调，30Hz 刷新。"""
        with self._data_lock:
            # 更新左手显示
            if self._left_data.valid:
                pos_text = f"位置：X={self._left_data.x:8.4f}m  Y={self._left_data.y:8.4f}m  Z={self._left_data.z:8.4f}m"
                rot_text = f"旋转：Yaw={self._left_data.yaw:7.2f}°  Pitch={self._left_data.pitch:7.2f}°  Roll={self._left_data.roll:7.2f}°"
                self._left_position_label.setText(pos_text)
                self._left_rotation_label.setText(rot_text)
            
            # 更新右手显示
            if self._right_data.valid:
                pos_text = f"位置：X={self._right_data.x:8.4f}m  Y={self._right_data.y:8.4f}m  Z={self._right_data.z:8.4f}m"
                rot_text = f"旋转：Yaw={self._right_data.yaw:7.2f}°  Pitch={self._right_data.pitch:7.2f}°  Roll={self._right_data.roll:7.2f}°"
                self._right_position_label.setText(pos_text)
                self._right_rotation_label.setText(rot_text)

    def closeEvent(self, event):
        """窗口关闭时清理资源。"""
        if self._tracking_enabled:
            self._stop_tracking()
        super().closeEvent(event)
