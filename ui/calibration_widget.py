"""calibration_widget.py
定位标定面板

功能：
- 提供定位标定的 UI 界面
- 处理标定按钮点击，获取左手 tracker 位置，计算偏差并应用到所有 tracker 和 lighthouse
- 处理取消标定按钮点击，重置所有位置偏差为 0
- 记录标定日志
"""

import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtGui import QTextCursor


def _find_calibration_ui_file() -> Path:
    """查找 calibration_panel.ui 文件的路径。"""
    candidates = [
        Path(__file__).parent / "calibration_panel.ui",
        Path(__file__).parent.parent / "ui" / "calibration_panel.ui",
        Path.cwd() / "ui" / "calibration_panel.ui",
    ]
    
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.insert(2, Path(meipass) / "ui" / "calibration_panel.ui")
        candidates.insert(3, Path(meipass) / "_internal" / "ui" / "calibration_panel.ui")
    
    try:
        exe_dir = Path(sys.executable).parent
        candidates.insert(len(candidates) - 1, exe_dir / "ui" / "calibration_panel.ui")
        candidates.insert(len(candidates) - 1, exe_dir / "_internal" / "ui" / "calibration_panel.ui")
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
            for p in root.rglob("calibration_panel.ui"):
                return p
        except Exception:
            continue
    
    return candidates[0]


class CalibrationWidget(QWidget):
    """定位标定面板。"""

    def __init__(self, parent=None, vive_tracker_widget=None):
        super().__init__(parent)
        
        self._calibration_in_progress = False
        self._vive_tracker_widget = vive_tracker_widget  # 对 ViveTrackerWidget 的引用
        
        self._init_ui()
        self._add_log("系统初始化完成")

    def _init_ui(self):
        """从 UI 文件加载界面。"""
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
        
        # 获取 UI 中的控件
        self._calibration_btn: QPushButton = self._ui.findChild(QPushButton, "calibrationButton")
        self._cancel_calibration_btn: QPushButton = self._ui.findChild(QPushButton, "cancelCalibrationButton")
        self._status_label: QLabel = self._ui.findChild(QLabel, "statusLabel")
        self._time_label: QLabel = self._ui.findChild(QLabel, "timeLabel")
        self._log_text: QTextEdit = self._ui.findChild(QTextEdit, "logText")
        
        # 验证所有必要的控件存在
        assert self._calibration_btn is not None, "UI 控件未找到：calibrationButton"
        assert self._cancel_calibration_btn is not None, "UI 控件未找到：cancelCalibrationButton"
        assert self._status_label is not None, "UI 控件未找到：statusLabel"
        assert self._time_label is not None, "UI 控件未找到：timeLabel"
        assert self._log_text is not None, "UI 控件未找到：logText"
        
        # 连接信号
        self._calibration_btn.clicked.connect(self._on_calibration_clicked)
        self._cancel_calibration_btn.clicked.connect(self._on_cancel_calibration_clicked)

    def set_tracking_controls_enabled(self, enabled: bool):
        """切换依赖追踪状态的标定按钮。"""
        self._calibration_btn.setEnabled(enabled)
        self._cancel_calibration_btn.setEnabled(enabled)
        if not enabled and not self._calibration_in_progress:
            self._status_label.setText("状态：等待开启追踪")

    def _on_calibration_clicked(self):
        """处理标定按钮点击事件。
        
        获取左手 tracker 当前位置，取反后作为位置偏差，
        并应用到所有 tracker 和 lighthouse。
        """
        if self._vive_tracker_widget is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 错误：无法访问 ViveTrackerWidget"
            print(error_msg)
            self._add_log(error_msg)
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
                    self._add_log(warning_msg)
                    return
                
                # 计算位置偏差（取反）
                bias_x = -pos_x
                bias_y = -pos_y
                bias_z = -pos_z
                
                # 设置左手 tracker 的位置偏差
                left_data.pos_bias_x_m = bias_x
                left_data.pos_bias_y_m = bias_y
                left_data.pos_bias_z_m = bias_z
                
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
                f"  应用的位置偏差: X={bias_x:.4f}m, Y={bias_y:.4f}m, Z={bias_z:.4f}m\n"
                f"  已应用到: 左手 Tracker + {len(all_lighthouses)} 个 Lighthouse\n"
                f"  效果: 所有设备虚拟位置已设置为原点，后续运动相对于原点"
            )
            print(calibration_msg)
            self._add_log(calibration_msg)
            
            # 更新状态标签
            self._status_label.setText("状态：已标定")
            self._time_label.setText(f"上次标定时间：{timestamp}")
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 标定失败：{e}"
            print(error_msg)
            self._add_log(error_msg)
            import traceback
            traceback.print_exc()

    def _on_cancel_calibration_clicked(self):
        """处理取消标定按钮点击事件。
        
        将所有 tracker 和 lighthouse 的位置偏差都重置为 0。
        """
        if self._vive_tracker_widget is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 错误：无法访问 ViveTrackerWidget"
            print(error_msg)
            self._add_log(error_msg)
            return
        
        try:
            with self._vive_tracker_widget._data_lock:
                # 重置左手 tracker 的位置偏差
                left_data = self._vive_tracker_widget._left_data
                left_data.pos_bias_x_m = 0.0
                left_data.pos_bias_y_m = 0.0
                left_data.pos_bias_z_m = 0.0
                
                # 重置所有 lighthouse 的位置偏差
                lighthouse_manager = self._vive_tracker_widget._lighthouse_manager
                all_lighthouses = lighthouse_manager.get_all_lighthouses()
                
                for lighthouse_name, lighthouse_data in all_lighthouses.items():
                    lighthouse_data.update_position_bias(0.0, 0.0, 0.0)
            
            # 记录取消标定完成
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cancel_msg = (
                f"[{timestamp}] ✅ 取消标定完成\n"
                f"  已重置: 左手 Tracker + {len(all_lighthouses)} 个 Lighthouse\n"
                f"  所有设备位置偏差已恢复为 0"
            )
            print(cancel_msg)
            self._add_log(cancel_msg)
            
            # 更新状态标签
            self._status_label.setText("状态：已取消标定")
            self._time_label.setText(f"上次操作时间：{timestamp}")
            
        except Exception as e:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            error_msg = f"[{timestamp}] ❌ 取消标定失败：{e}"
            print(error_msg)
            self._add_log(error_msg)
            import traceback
            traceback.print_exc()

    def _add_log(self, message: str):
        """添加日志信息到日志显示区域。"""
        self._log_text.moveCursor(QTextCursor.End)
        self._log_text.insertPlainText(f"{message}\n")
        self._log_text.moveCursor(QTextCursor.End)
