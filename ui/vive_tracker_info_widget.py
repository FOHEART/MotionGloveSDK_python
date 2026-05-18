"""vive_tracker_info_widget.py
ViveTracker 追踪信息面板组件

功能：
- 显示左右手追踪器的配置信息
- 显示实时位置和旋转数据
- 支持欧拉角和四元数显示切换
- 支持位置偏差设置
- SteamVR 状态监控
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox, QPushButton, QTextEdit, QLineEdit
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu


def _find_info_ui_file() -> Path:
    """查找 vive_tracker_info_widget.ui 文件的路径。"""
    candidates = [
        Path(__file__).parent / "vive_tracker_info_widget.ui",
        Path(__file__).parent.parent / "ui" / "vive_tracker_info_widget.ui",
        Path.cwd() / "ui" / "vive_tracker_info_widget.ui",
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(2, Path(meipass) / "ui" / "vive_tracker_info_widget.ui")
        candidates.insert(3, Path(meipass) / "_internal" / "ui" / "vive_tracker_info_widget.ui")

    try:
        exe_dir = Path(sys.executable).parent
        candidates.insert(len(candidates) - 1, exe_dir / "ui" / "vive_tracker_info_widget.ui")
        candidates.insert(len(candidates) - 1, exe_dir / "_internal" / "ui" / "vive_tracker_info_widget.ui")
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
            for path in root.rglob("vive_tracker_info_widget.ui"):
                return path
        except Exception:
            continue

    return candidates[0]


class ViveTrackerInfoWidget(QWidget):
    """追踪信息显示面板组件。"""
    
    def __init__(self, parent=None):
        """初始化追踪信息面板。
        
        Args:
            parent: 父窗口
        """
        super().__init__(parent)
        self._ui = None
        self._parent = parent
        
        # UI 控件引用
        self._left_config_label = None
        self._right_config_label = None
        self._left_position_label = None
        self._right_position_label = None
        self._left_rotation_label = None
        self._right_rotation_label = None
        self._left_quat_label = None
        self._right_quat_label = None
        self._start_tracking_btn = None
        self._left_group = None
        self._right_group = None
        self._connection_status_text = None
        self._steamvr_status_label = None
        
        # 显示模式标志
        self._left_show_quat = False
        self._right_show_quat = False
        
        # 偏差控件
        self._left_bias_x_edit = None
        self._left_bias_y_edit = None
        self._left_bias_z_edit = None
        self._right_bias_x_edit = None
        self._right_bias_y_edit = None
        self._right_bias_z_edit = None
        self._left_bias_set_btn = None
        self._right_bias_set_btn = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """从 UI 文件加载并初始化 UI。"""
        ui_file_path = _find_info_ui_file()

        loader = QUiLoader()
        ui_file = QFile(str(ui_file_path))

        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{ui_file_path}")

        self._ui = loader.load(ui_file, self)
        ui_file.close()

        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{ui_file_path}")
        
        # 将 UI 添加到当前 widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ui)
        
        # 获取 UI 中的控件
        self._left_config_label = self._ui.findChild(QLabel, "leftHandConfigInfo")
        self._right_config_label = self._ui.findChild(QLabel, "rightHandConfigInfo")
        self._left_position_label = self._ui.findChild(QLabel, "leftHandPositionLabel")
        self._right_position_label = self._ui.findChild(QLabel, "rightHandPositionLabel")
        self._left_rotation_label = self._ui.findChild(QLabel, "leftHandRotationLabel")
        self._right_rotation_label = self._ui.findChild(QLabel, "rightHandRotationLabel")
        self._left_quat_label = self._ui.findChild(QLabel, "leftHandQuatLabel")
        self._right_quat_label = self._ui.findChild(QLabel, "rightHandQuatLabel")
        self._start_tracking_btn = self._ui.findChild(QPushButton, "startTrackingButton")
        self._left_group = self._ui.findChild(QGroupBox, "leftHandGroup")
        self._right_group = self._ui.findChild(QGroupBox, "rightHandGroup")
        self._connection_status_text = self._ui.findChild(QTextEdit, "connectionStatusText")
        self._steamvr_status_label = self._ui.findChild(QLabel, "steamvrStatusLabel")
        
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
        self._left_bias_x_edit = self._ui.findChild(QLineEdit, "leftBiasXEdit")
        self._left_bias_y_edit = self._ui.findChild(QLineEdit, "leftBiasYEdit")
        self._left_bias_z_edit = self._ui.findChild(QLineEdit, "leftBiasZEdit")
        self._left_bias_set_btn = self._ui.findChild(QPushButton, "leftBiasSetBtn")
        
        # 从 UI 中查找右手偏差控件
        self._right_bias_x_edit = self._ui.findChild(QLineEdit, "rightBiasXEdit")
        self._right_bias_y_edit = self._ui.findChild(QLineEdit, "rightBiasYEdit")
        self._right_bias_z_edit = self._ui.findChild(QLineEdit, "rightBiasZEdit")
        self._right_bias_set_btn = self._ui.findChild(QPushButton, "rightBiasSetBtn")
        
        # 验证所有偏差控件已找到
        assert self._left_bias_x_edit is not None, "UI 控件未找到：leftBiasXEdit"
        assert self._left_bias_y_edit is not None, "UI 控件未找到：leftBiasYEdit"
        assert self._left_bias_z_edit is not None, "UI 控件未找到：leftBiasZEdit"
        assert self._left_bias_set_btn is not None, "UI 控件未找到：leftBiasSetBtn"
        assert self._right_bias_x_edit is not None, "UI 控件未找到：rightBiasXEdit"
        assert self._right_bias_y_edit is not None, "UI 控件未找到：rightBiasYEdit"
        assert self._right_bias_z_edit is not None, "UI 控件未找到：rightBiasZEdit"
        assert self._right_bias_set_btn is not None, "UI 控件未找到：rightBiasSetBtn"
        
        # 连接信号
        self._left_bias_set_btn.clicked.connect(self._on_set_left_bias)
        self._right_bias_set_btn.clicked.connect(self._on_set_right_bias)
    
    def _on_set_left_bias(self):
        """处理设置左手偏差按钮点击事件。"""
        try:
            x = float(self._left_bias_x_edit.text())
            y = float(self._left_bias_y_edit.text())
            z = float(self._left_bias_z_edit.text())
            
            # 调用父窗口的方法来处理偏差设置
            if hasattr(self._parent, '_left_data') and hasattr(self._parent, '_data_lock'):
                with self._parent._data_lock:
                    self._parent._left_data.pos_bias_x_m = x
                    self._parent._left_data.pos_bias_y_m = y
                    self._parent._left_data.pos_bias_z_m = z
                
                print(f"[PosBias] 左手偏差已设置：X={x:.4f}m, Y={y:.4f}m, Z={z:.4f}m")
                
                # 触发场景更新
                if hasattr(self._parent, '_renderer') and hasattr(self._parent, '_mark_scene_dirty'):
                    if self._parent._renderer is not None and self._parent._mark_scene_dirty is not None:
                        self._parent._mark_scene_dirty()
        except ValueError as e:
            print(f"[PosBias] 左手偏差设置失败：无效的数值 - {e}")
    
    def _on_set_right_bias(self):
        """处理设置右手偏差按钮点击事件。"""
        try:
            x = float(self._right_bias_x_edit.text())
            y = float(self._right_bias_y_edit.text())
            z = float(self._right_bias_z_edit.text())
            
            # 调用父窗口的方法来处理偏差设置
            if hasattr(self._parent, '_right_data') and hasattr(self._parent, '_data_lock'):
                with self._parent._data_lock:
                    self._parent._right_data.pos_bias_x_m = x
                    self._parent._right_data.pos_bias_y_m = y
                    self._parent._right_data.pos_bias_z_m = z
                
                print(f"[PosBias] 右手偏差已设置：X={x:.4f}m, Y={y:.4f}m, Z={z:.4f}m")
                
                # 触发场景更新
                if hasattr(self._parent, '_renderer') and hasattr(self._parent, '_mark_scene_dirty'):
                    if self._parent._renderer is not None and self._parent._mark_scene_dirty is not None:
                        self._parent._mark_scene_dirty()
        except ValueError as e:
            print(f"[PosBias] 右手偏差设置失败：无效的数值 - {e}")

    def set_tracking_controls_enabled(self, enabled: bool):
        """切换依赖追踪状态的内部控件。

        开始/停止追踪按钮始终保持可点击，只有偏差编辑与设置按钮随追踪状态启停。
        """
        for widget in (
            self._left_bias_x_edit,
            self._left_bias_y_edit,
            self._left_bias_z_edit,
            self._right_bias_x_edit,
            self._right_bias_y_edit,
            self._right_bias_z_edit,
            self._left_bias_set_btn,
            self._right_bias_set_btn,
        ):
            if widget is not None:
                widget.setEnabled(enabled)
    
    def _set_steamvr_status(self, running: bool):
        """更新 SteamVR 状态标签。
        
        Args:
            running: True 表示 SteamVR 已启动，False 表示未启动
        """
        status_label = self._resolve_steamvr_status_label()
        if running:
            status_label.setText("SteamVR: 已启动")
            status_label.setStyleSheet(
                "background-color: green; color: white; padding: 2px 8px; border-radius: 3px; font-weight: bold;"
            )
        else:
            status_label.setText("SteamVR: 未启动")
            status_label.setStyleSheet(
                "background-color: red; color: white; padding: 2px 8px; border-radius: 3px; font-weight: bold;"
            )
    
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
    
    # 公开方法供外部调用
    def get_ui(self):
        """获取加载的 UI 对象。"""
        return self._ui
    
    def get_start_tracking_button(self):
        """获取开始追踪按钮。"""
        return self._start_tracking_btn
    
    def get_connection_status_text(self):
        """获取连接状态文本编辑框。"""
        return self._connection_status_text

    def _resolve_connection_status_text(self):
        """获取仍然有效的连接状态文本控件。"""
        try:
            if self._connection_status_text is not None:
                self._connection_status_text.objectName()
                return self._connection_status_text
        except RuntimeError:
            self._connection_status_text = None

        self._connection_status_text = self.findChild(QTextEdit, "connectionStatusText")
        if self._connection_status_text is None:
            raise RuntimeError("UI 控件不可用：connectionStatusText")
        return self._connection_status_text

    def _resolve_steamvr_status_label(self):
        """获取仍然有效的 SteamVR 状态标签。"""
        try:
            if self._steamvr_status_label is not None:
                self._steamvr_status_label.objectName()
                return self._steamvr_status_label
        except RuntimeError:
            self._steamvr_status_label = None

        self._steamvr_status_label = self.findChild(QLabel, "steamvrStatusLabel")
        if self._steamvr_status_label is None:
            raise RuntimeError("UI 控件不可用：steamvrStatusLabel")
        return self._steamvr_status_label

    def _resolve_named_widget(self, attr_name: str, widget_type, object_name: str):
        """按 objectName 获取仍然有效的控件。"""
        widget = getattr(self, attr_name)
        try:
            if widget is not None:
                widget.objectName()
                return widget
        except RuntimeError:
            widget = None

        widget = self.findChild(widget_type, object_name)
        if widget is None:
            raise RuntimeError(f"UI 控件不可用：{object_name}")
        setattr(self, attr_name, widget)
        return widget

    def set_connection_status_text(self, text: str):
        """更新连接状态文本。"""
        self._resolve_connection_status_text().setText(text)

    def get_connection_status_plain_text(self) -> str:
        """获取连接状态的纯文本内容。"""
        return self._resolve_connection_status_text().toPlainText()
    
    def get_position_labels(self):
        """获取位置标签字典。"""
        return {
            "left": self._resolve_named_widget("_left_position_label", QLabel, "leftHandPositionLabel"),
            "right": self._resolve_named_widget("_right_position_label", QLabel, "rightHandPositionLabel")
        }
    
    def get_rotation_labels(self):
        """获取旋转标签字典。"""
        return {
            "left": self._resolve_named_widget("_left_rotation_label", QLabel, "leftHandRotationLabel"),
            "right": self._resolve_named_widget("_right_rotation_label", QLabel, "rightHandRotationLabel")
        }
    
    def get_quat_labels(self):
        """获取四元数标签字典。"""
        return {
            "left": self._resolve_named_widget("_left_quat_label", QLabel, "leftHandQuatLabel"),
            "right": self._resolve_named_widget("_right_quat_label", QLabel, "rightHandQuatLabel")
        }
    
    def get_config_labels(self):
        """获取配置标签字典。"""
        return {
            "left": self._resolve_named_widget("_left_config_label", QLabel, "leftHandConfigInfo"),
            "right": self._resolve_named_widget("_right_config_label", QLabel, "rightHandConfigInfo")
        }
    
    def get_groups(self):
        """获取 GroupBox 字典。"""
        return {
            "left": self._resolve_named_widget("_left_group", QGroupBox, "leftHandGroup"),
            "right": self._resolve_named_widget("_right_group", QGroupBox, "rightHandGroup")
        }
    
    def set_groupbox_online_status(self, side: str, is_online: bool):
        """设置 GroupBox 在线状态。"""
        if side == "left":
            groupbox = self._resolve_named_widget("_left_group", QGroupBox, "leftHandGroup")
            self._set_groupbox_online_status(groupbox, is_online)
        elif side == "right":
            groupbox = self._resolve_named_widget("_right_group", QGroupBox, "rightHandGroup")
            self._set_groupbox_online_status(groupbox, is_online)
    
    def set_steamvr_status(self, running: bool):
        """设置 SteamVR 状态。"""
        self._set_steamvr_status(running)
    
    def update_left_config(self, text: str):
        """更新左手配置标签。"""
        label = self._resolve_named_widget("_left_config_label", QLabel, "leftHandConfigInfo")
        label.setText(text)
    
    def update_right_config(self, text: str):
        """更新右手配置标签。"""
        label = self._resolve_named_widget("_right_config_label", QLabel, "rightHandConfigInfo")
        label.setText(text)
    
    def update_left_position(self, text: str):
        """更新左手位置标签。"""
        label = self._resolve_named_widget("_left_position_label", QLabel, "leftHandPositionLabel")
        label.setText(text)
    
    def update_right_position(self, text: str):
        """更新右手位置标签。"""
        label = self._resolve_named_widget("_right_position_label", QLabel, "rightHandPositionLabel")
        label.setText(text)
    
    def update_left_rotation(self, text: str):
        """更新左手旋转标签。"""
        label = self._resolve_named_widget("_left_rotation_label", QLabel, "leftHandRotationLabel")
        label.setText(text)
    
    def update_right_rotation(self, text: str):
        """更新右手旋转标签。"""
        label = self._resolve_named_widget("_right_rotation_label", QLabel, "rightHandRotationLabel")
        label.setText(text)
    
    def update_left_quat(self, text: str):
        """更新左手四元数标签。"""
        label = self._resolve_named_widget("_left_quat_label", QLabel, "leftHandQuatLabel")
        label.setText(text)
    
    def update_right_quat(self, text: str):
        """更新右手四元数标签。"""
        label = self._resolve_named_widget("_right_quat_label", QLabel, "rightHandQuatLabel")
        label.setText(text)


class InfoTabManager:
    """追踪信息tab管理器。
    
    负责管理追踪信息tab的创建、初始化、配置加载、数据更新等。
    """
    
    def __init__(self, vive_tracker_widget):
        """初始化追踪信息tab管理器。
        
        Args:
            vive_tracker_widget: ViveTrackerWidget 实例
        """
        self._vive_tracker_widget = vive_tracker_widget
        self._info_widget = None
        self._info_tab_index = None
    
    def setup_info_tab(self, tab_widget):
        """设置追踪信息tab。
        
        Args:
            tab_widget: QTabWidget 实例
        
        Returns:
            创建的 ViveTrackerInfoWidget 实例
        """
        # 创建追踪信息tab
        self._info_widget = ViveTrackerInfoWidget(parent=self._vive_tracker_widget)
        self._info_tab_index = tab_widget.addTab(self._info_widget, "追踪信息")
        tab_widget.setTabEnabled(self._info_tab_index, True)
        
        return self._info_widget
    
    def load_config(self):
        """从 JSON 文件加载配置。"""
        import json
        from pathlib import Path
        
        # 查找配置文件
        config_file = Path(__file__).parent.parent / "config.json"
        if not config_file.exists():
            self._vive_tracker_widget._config = {}
            error_text = f"<font color='red'><b>配置文件未找到</b></font><br>{config_file}"
            self._info_widget.update_left_config(error_text)
            self._info_widget.update_right_config(error_text)
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            self._vive_tracker_widget._config = {}
            error_text = f"<font color='red'><b>读取配置失败</b></font><br>{e}"
            self._info_widget.update_left_config(error_text)
            self._info_widget.update_right_config(error_text)
            return

        self._vive_tracker_widget._config = config
        
        # 更新左手信息
        left_config = config.get("LeftHandTracker", {})
        if left_config:
            left_text = self._format_config(left_config)
            self._info_widget.update_left_config(left_text)
        else:
            self._info_widget.update_left_config("<font color='gray'>未配置</font>")
        
        # 更新右手信息
        right_config = config.get("RightHandTracker", {})
        if right_config:
            right_text = self._format_config(right_config)
            self._info_widget.update_right_config(right_text)
        else:
            self._info_widget.update_right_config("<font color='gray'>未配置</font>")
    
    def update_tracker_display(self, side: str, pos_text: str, rot_text: str, quat_text: str, is_online: bool):
        """更新追踪器显示信息。
        
        Args:
            side: "left" 或 "right"
            pos_text: 位置文本
            rot_text: 旋转文本
            quat_text: 四元数文本
            is_online: 是否在线
        """
        if side == "left":
            self._info_widget.update_left_position(pos_text)
            self._info_widget.update_left_rotation(rot_text)
            self._info_widget.update_left_quat(quat_text)
            self._info_widget.set_groupbox_online_status("left", is_online)
        elif side == "right":
            self._info_widget.update_right_position(pos_text)
            self._info_widget.update_right_rotation(rot_text)
            self._info_widget.update_right_quat(quat_text)
            self._info_widget.set_groupbox_online_status("right", is_online)
    
    def set_steamvr_status(self, running: bool):
        """设置 SteamVR 状态。
        
        Args:
            running: True 表示 SteamVR 已启动
        """
        self._info_widget.set_steamvr_status(running)

    def set_tracking_controls_enabled(self, enabled: bool):
        """切换追踪信息 tab 内部依赖追踪状态的控件。"""
        if self._info_widget is not None:
            self._info_widget.set_tracking_controls_enabled(enabled)

    def set_connection_status_text(self, text: str):
        """更新连接状态文本。"""
        if self._info_widget is not None:
            self._info_widget.set_connection_status_text(text)

    def get_connection_status_plain_text(self) -> str:
        """获取连接状态的纯文本内容。"""
        if self._info_widget is None:
            return ""
        return self._info_widget.get_connection_status_plain_text()
    
    def _format_config(self, config: dict) -> str:
        """将配置字典格式化为显示文本。
        
        Args:
            config: 配置字典
        
        Returns:
            格式化后的 HTML 文本
        """
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
    
    def get_info_widget(self):
        """获取追踪信息widget。
        
        Returns:
            ViveTrackerInfoWidget 实例
        """
        return self._info_widget
    
    def get_info_tab_index(self):
        """获取追踪信息tab索引。
        
        Returns:
            追踪信息tab的索引
        """
        return self._info_tab_index
