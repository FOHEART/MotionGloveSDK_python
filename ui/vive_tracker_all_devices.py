"""vive_tracker_all_devices.py
独立的所有设备信息页面。

功能：
- 提供一个独立 tab 页面，用于枚举当前检测到的所有 OpenVR 设备
- 点击按钮后清空文本框并重新输出当前 Vive Tracker / Lighthouse 等设备详情
- 不依赖追踪开启状态，也不与其他 tab 页面联动
"""

from datetime import datetime

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit


class ViveTrackerAllDevicesWidget(QWidget):
    """所有设备信息页面。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vive_tracker_widget = parent
        self._refresh_button = None
        self._output_text = None
        self._copy_button = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._refresh_button = QPushButton("检测当前所有设备")
        self._refresh_button.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self._refresh_button)

        self._output_text = QTextEdit()
        self._output_text.setReadOnly(True)
        self._output_text.setPlaceholderText("点击上方按钮后，这里会显示当前检测到的所有 Vive Tracker / Lighthouse / HMD / Controller 详细信息。")
        layout.addWidget(self._output_text)

        self._copy_button = QPushButton("复制")
        self._copy_button.clicked.connect(self._on_copy_clicked)
        layout.addWidget(self._copy_button)

    def _safe_call(self, func, default="不可用"):
        try:
            value = func()
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value if value is not None else default
        except Exception as exc:
            return f"错误: {exc}"

    def _device_type_map(self, openvr_system):
        type_map = {}
        object_names = getattr(openvr_system, "object_names", {})
        for device_type, names in object_names.items():
            for device_name in names:
                type_map[device_name] = device_type
        return type_map

    def _format_pose(self, pose_value):
        if isinstance(pose_value, str):
            return pose_value
        if pose_value in (None, "不可用"):
            return "不可用"
        if not isinstance(pose_value, (list, tuple)):
            return str(pose_value)
        return ", ".join(f"{float(v):.4f}" for v in pose_value)

    def _build_device_lines(self, device_name, device, device_type):
        lines = [f"设备名称: {device_name}", f"设备类型: {device_type}"]

        serial = self._safe_call(device.get_serial)
        model = self._safe_call(device.get_model)
        battery = self._safe_call(device.get_battery_percent)
        charging = self._safe_call(device.is_charging)
        pose_euler = self._safe_call(device.get_pose_euler)
        pose_quat = self._safe_call(device.get_pose_quaternion)
        velocity = self._safe_call(device.get_velocity)
        angular_velocity = self._safe_call(device.get_angular_velocity)

        lines.append(f"序列号: {serial}")
        lines.append(f"型号: {model}")
        lines.append(f"电量: {battery}")
        lines.append(f"充电中: {charging}")
        lines.append(f"欧拉角位姿: {self._format_pose(pose_euler)}")
        lines.append(f"四元数位姿: {self._format_pose(pose_quat)}")
        lines.append(f"线速度: {self._format_pose(velocity)}")
        lines.append(f"角速度: {self._format_pose(angular_velocity)}")

        if hasattr(device, "get_mode"):
            lines.append(f"模式: {self._safe_call(device.get_mode)}")

        return lines

    def _on_refresh_clicked(self):
        self._output_text.clear()

        lines = [
            "=== 当前 OpenVR 设备检测结果 ===",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        try:
            temporary_system = None
            openvr_system = getattr(self._vive_tracker_widget, "_openvr_system", None)
            if openvr_system is None:
                from triad_openvr.triad_openvr import triad_openvr
                temporary_system = triad_openvr()
                openvr_system = temporary_system

            openvr_system.poll_vr_events()

            device_type_map = self._device_type_map(openvr_system)
            device_names = sorted(openvr_system.devices.keys())

            if not device_names:
                lines.append("未检测到任何 OpenVR 设备。")
            else:
                lines.append(f"设备总数: {len(device_names)}")
                lines.append("")

                for index, device_name in enumerate(device_names, start=1):
                    device = openvr_system.devices[device_name]
                    device_type = device_type_map.get(device_name, "Unknown")
                    lines.append(f"----- 设备 {index} -----")
                    lines.extend(self._build_device_lines(device_name, device, device_type))
                    lines.append("")

            del temporary_system
        except Exception as exc:
            lines.append(f"检测失败: {exc}")

        self._output_text.setPlainText("\n".join(lines))

    def _on_copy_clicked(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self._output_text.toPlainText())


class AllDevicesTabManager:
    """所有设备 tab 管理器。"""

    def __init__(self, vive_tracker_widget):
        self._vive_tracker_widget = vive_tracker_widget
        self._all_devices_widget = None
        self._all_devices_tab_index = None

    def setup_all_devices_tab(self, tab_widget):
        self._all_devices_widget = ViveTrackerAllDevicesWidget(parent=self._vive_tracker_widget)
        self._all_devices_tab_index = tab_widget.addTab(self._all_devices_widget, "所有设备")
        tab_widget.setTabEnabled(self._all_devices_tab_index, True)
        return self._all_devices_widget

    def get_all_devices_widget(self):
        return self._all_devices_widget

    def get_all_devices_tab_index(self):
        return self._all_devices_tab_index