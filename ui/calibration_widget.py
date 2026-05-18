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
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit, QGroupBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice
from PySide6.QtGui import QTextCursor
from shiboken6 import isValid


CALIBRATION_DEBUG_PRINTS = False


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
        super().__init__(parent)
        
        self._calibration_in_progress = False
        self._vive_tracker_widget = vive_tracker_widget  # 对 ViveTrackerWidget 的引用
        self._bias_value_label: QLabel | None = None
        self._info_group: QGroupBox | None = None
        
        self._init_ui()
        self._add_log("系统初始化完成")

    @staticmethod
    def _format_quaternion_wxyz(quat_wxyz: tuple[float, float, float, float]) -> str:
        return (
            f"w={quat_wxyz[0]:.4f}  x={quat_wxyz[1]:.4f}  "
            f"y={quat_wxyz[2]:.4f}  z={quat_wxyz[3]:.4f}"
        )

    def _build_calibration_info_text(
        self,
        bias_xyz: tuple[float, float, float] | None,
        calibration_quat_wxyz: tuple[float, float, float, float],
    ) -> str:
        if bias_xyz is None:
            bias_line = "位置偏差：-"
        else:
            bias_line = f"位置偏差: X={bias_xyz[0]:.4f}m, Y={bias_xyz[1]:.4f}m, Z={bias_xyz[2]:.4f}m"
        quat_line = f"标定四元数: {self._format_quaternion_wxyz(calibration_quat_wxyz)}"
        return f"{bias_line}\n{quat_line}"

    def _bind_destroyed_debug(self, label: str, widget) -> None:
        """记录 Qt 对象何时被销毁。"""
        if widget is None or not isValid(widget):
            return

        try:
            widget.destroyed.connect(
                lambda *_args, _label=label: print(f"[CalibDebug] destroyed signal: {_label}")
            )
        except RuntimeError as exc:
            print(f"[CalibDebug] bind destroyed failed for {label}: {exc}")

    def _debug_widget_state(self, label: str, widget) -> None:
        """输出 widget 当前状态，便于定位 Qt 对象生命周期问题。"""
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
        """输出标定 UI 与数据状态快照。"""
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
                        f"bias=({tracker_cali_state.pos_bias_x_m:.4f}, {tracker_cali_state.pos_bias_y_m:.4f}, {tracker_cali_state.pos_bias_z_m:.4f}) "
                        f"calib_quat=({left_data.quat_calibration_w:.4f}, {left_data.quat_calibration_x:.4f}, {left_data.quat_calibration_y:.4f}, {left_data.quat_calibration_z:.4f})"
                    )
            except Exception as exc:
                print(f"[CalibDebug] left_data snapshot failed: {exc}")

        print(f"[CalibDebug] ---- snapshot end: {stage} ----")

    def _find_child_from_self(self, widget_type, object_name: str):
        """优先从 self 查找子控件，避免依赖可能失效的 _ui 引用。"""
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
        """确保用于显示位置偏差的专用标签存在且可用。"""
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
        
        # 获取 UI 中的控件。优先从 self 递归查找，避免后续依赖 _ui 生命周期。
        self._calibration_btn: QPushButton = self.findChild(QPushButton, "calibrationButton")
        self._cancel_calibration_btn: QPushButton = self.findChild(QPushButton, "cancelCalibrationButton")
        self._status_label: QLabel = self.findChild(QLabel, "statusLabel")
        self._time_label: QLabel = self.findChild(QLabel, "timeLabel")
        self._log_text: QTextEdit = self.findChild(QTextEdit, "logText")
        
        # 调试：打印找到的控件
        print(f"[CalibDebug] 控件查询结果:")
        print(f"  calibrationButton: {self._calibration_btn}")
        print(f"  cancelCalibrationButton: {self._cancel_calibration_btn}")
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
        assert self._status_label is not None, "UI 控件未找到：statusLabel"
        assert self._time_label is not None, "UI 控件未找到：timeLabel"
        assert self._log_text is not None, "UI 控件未找到：logText"
        
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
        self._bind_destroyed_debug("statusLabel", self._status_label)
        self._bind_destroyed_debug("timeLabel", self._time_label)
        self._bind_destroyed_debug("logText", self._log_text)
        self._bind_destroyed_debug("infoGroup", self._info_group)
        self._debug_snapshot("after_init_ui")
        
        # 连接信号
        self._calibration_btn.clicked.connect(self._on_calibration_clicked)
        self._cancel_calibration_btn.clicked.connect(self._on_cancel_calibration_clicked)

    def set_tracking_controls_enabled(self, enabled: bool):
        """切换依赖追踪状态的标定按钮。"""
        try:
            self._calibration_btn.setEnabled(enabled)
            self._cancel_calibration_btn.setEnabled(enabled)
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

    def _is_ui_valid(self) -> bool:
        """检查 UI 是否仍然有效。"""
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
        """安全地获取 logText 控件引用（防止过期指针）。"""
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
        """安全地获取 statusLabel 控件引用（防止过期指针）。"""
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
        """安全地获取 timeLabel 控件引用（防止过期指针）。"""
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
                calibration_quat_wxyz = self._vive_tracker_widget.invert_quaternion_wxyz(raw_quat_wxyz)
                calibrated_current_quat_wxyz = self._vive_tracker_widget.apply_calibration_quaternion_wxyz(
                    calibration_quat_wxyz,
                    raw_quat_wxyz,
                )

                # 设置左手 tracker 的位置偏差
                self._vive_tracker_widget.get_tracker_cali_manager().set_position_bias_xyz((bias_x, bias_y, bias_z))
                left_data.quat_calibration_w = calibration_quat_wxyz[0]
                left_data.quat_calibration_x = calibration_quat_wxyz[1]
                left_data.quat_calibration_y = calibration_quat_wxyz[2]
                left_data.quat_calibration_z = calibration_quat_wxyz[3]
                
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
                f"  左手 Tracker 原始四元数: {self._format_quaternion_wxyz(raw_quat_wxyz)}\n"
                f"  标定四元数: {self._format_quaternion_wxyz(calibration_quat_wxyz)}\n"
                f"  标定后当前四元数: {self._format_quaternion_wxyz(calibrated_current_quat_wxyz)}\n"
                f"  应用的位置偏差: X={bias_x:.4f}m, Y={bias_y:.4f}m, Z={bias_z:.4f}m\n"
                f"  已应用到: 左手 Tracker + {len(all_lighthouses)} 个 Lighthouse\n"
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
                reset_info = self._build_calibration_info_text(None, (1.0, 0.0, 0.0, 0.0))
                
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
        """添加日志信息到日志显示区域。"""
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
