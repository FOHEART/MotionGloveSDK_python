"""calibration_widget.py
定位标定面板

功能：
- 提供定位标定的 UI 界面
- 处理标定按钮点击
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

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._calibration_in_progress = False
        
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
        self._status_label: QLabel = self._ui.findChild(QLabel, "statusLabel")
        self._time_label: QLabel = self._ui.findChild(QLabel, "timeLabel")
        self._log_text: QTextEdit = self._ui.findChild(QTextEdit, "logText")
        
        # 验证所有必要的控件存在
        assert self._calibration_btn is not None, "UI 控件未找到：calibrationButton"
        assert self._status_label is not None, "UI 控件未找到：statusLabel"
        assert self._time_label is not None, "UI 控件未找到：timeLabel"
        assert self._log_text is not None, "UI 控件未找到：logText"
        
        # 连接信号
        self._calibration_btn.clicked.connect(self._on_calibration_clicked)

    def _on_calibration_clicked(self):
        """处理标定按钮点击事件。"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        calibration_msg = f"[{timestamp}] 标定按钮已按下"
        
        print(calibration_msg)
        self._add_log(calibration_msg)

    def _add_log(self, message: str):
        """添加日志信息到日志显示区域。"""
        self._log_text.moveCursor(QTextCursor.End)
        self._log_text.insertPlainText(f"{message}\n")
        self._log_text.moveCursor(QTextCursor.End)
