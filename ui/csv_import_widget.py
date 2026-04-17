"""csv_import_widget.py
CSV 回放模式的左侧控制面板（固定宽度 220px）。

布局由 csv_import_panel.ui 定义，可用 Qt Designer 编辑。
Python 代码只负责信号连接和运行时逻辑。

公开接口
--------
CsvImportWidget(parent)
    .fps -> int                          — 当前选定帧率（Hz）
    .set_playing(is_playing: bool)       — 由主窗口驱动按钮文字和状态
    .set_total_frames(total: int)        — 加载文件后设置总帧数，重置进度条
    .set_frame_index(index: int)         — 更新帧号标签和进度条（1-based，0=未播放）
    .file_selected                       — Signal(str)：用户选中文件路径
    .play_pause_clicked                  — Signal()：播放/暂停按钮点击
    .reset_clicked                       — Signal()：重置按钮点击
    .fps_changed                         — Signal(int)：帧率变更
    .seek_requested                      — Signal(int)：用户松开进度条，传递目标帧索引（0-based），不自动恢复播放
    .seek_started                        — Signal()：用户按下进度条，通知主窗口停止定时器
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSlider, QFileDialog, QMessageBox,
)
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal, QFile, QIODevice


# QComboBox 选项：显示文字 → 实际帧率值
_FPS_OPTIONS = [10, 24, 30, 60]
_DEFAULT_FPS = 60
_SLIDER_MAX  = 1000   # 千分比精度


def _ui_path() -> Path:
    """返回 csv_import_panel.ui 的绝对路径，兼容源码运行和 PyInstaller 打包。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "ui" / "csv_import_panel.ui"  # type: ignore[attr-defined]
    return Path(__file__).parent / "csv_import_panel.ui"


class CsvImportWidget(QWidget):
    """CSV 回放模式左侧面板（固定宽度 220px）。"""

    file_selected      = Signal(str)   # 用户选中 CSV 文件，传递绝对路径
    play_pause_clicked = Signal()      # 播放/暂停按钮点击
    reset_clicked      = Signal()      # 重置按钮点击
    fps_changed        = Signal(int)   # 帧率下拉框变更，传递新帧率（Hz）
    seek_started       = Signal()      # 进度条按下：通知主窗口停止定时器（不切换播放状态）
    seek_requested     = Signal(int)   # 进度条松开：传递目标帧索引（0-based），不自动恢复播放

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)

        # ── 加载 .ui ──────────────────────────────────
        loader = QUiLoader()
        ui_file = QFile(str(_ui_path()))
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_ui_path()}")
        self._ui = loader.load(ui_file)
        ui_file.close()
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_ui_path()}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._ui)

        # ── 获取控件引用 ───────────────────────────────
        def _find(typ, name):  # type: ignore[no-untyped-def]
            w = self._ui.findChild(typ, name)
            assert w is not None, f"UI 控件未找到：{name}"
            return w

        self._path_edit:      QLineEdit   = _find(QLineEdit,   "path_edit")
        self._fps_combo:      QComboBox   = _find(QComboBox,   "fps_combo")
        self._lbl_frame:      QLabel      = _find(QLabel,      "lbl_frame")
        self._slider:         QSlider     = _find(QSlider,     "slider_progress")
        self._btn_play_pause: QPushButton = _find(QPushButton, "btn_play_pause")
        self._btn_reset:      QPushButton = _find(QPushButton, "btn_reset")
        self._btn_export_bvh: QPushButton = _find(QPushButton, "btn_export_bvh")
        btn_browse:           QPushButton = _find(QPushButton, "btn_browse")

        # ── QComboBox userData（.ui 中只能存文字，这里补充整数 data）──
        for i, fps in enumerate(_FPS_OPTIONS):
            self._fps_combo.setItemData(i, fps)
        self._fps_combo.setCurrentIndex(_FPS_OPTIONS.index(_DEFAULT_FPS))

        # ── 内部状态 ───────────────────────────────────
        self._total_frames:  int  = 0
        self._slider_pressed: bool = False

        # ── 信号连接 ───────────────────────────────────
        btn_browse.clicked.connect(self._on_browse)
        self._btn_export_bvh.clicked.connect(self._on_export_bvh)
        self._fps_combo.currentIndexChanged.connect(self._on_fps_changed)
        self._slider.sliderPressed.connect(self._on_slider_pressed)
        self._slider.sliderReleased.connect(self._on_slider_released)
        self._btn_play_pause.clicked.connect(self.play_pause_clicked)
        self._btn_reset.clicked.connect(self.reset_clicked)

    # ── 属性 ──────────────────────────────────────────

    @property
    def fps(self) -> int:
        """当前选定帧率（Hz）。"""
        return self._fps_combo.currentData()

    # ── 公开方法 ───────────────────────────────────────

    def set_playing(self, is_playing: bool) -> None:
        """由主窗口调用，同步按钮文字和状态。"""
        self._btn_play_pause.setText(self.tr("暂停播放") if is_playing else self.tr("开始播放"))

    def set_total_frames(self, total: int) -> None:
        """由主窗口调用，设置总帧数（加载文件后调用一次）。"""
        self._total_frames = total
        self._slider.setValue(0)
        self._slider.setEnabled(total > 0)
        self._lbl_frame.setText(self.tr("—"))

    def set_frame_index(self, index: int) -> None:
        """由主窗口调用，更新帧号标签和进度条（1-based，index=0 表示未播放）。
        拖动期间不更新滑块，避免抖动。"""
        if index == 0 or self._total_frames == 0:
            self._lbl_frame.setText(self.tr("—"))
            if not self._slider_pressed:
                self._slider.setValue(0)
        else:
            pct = round(index / self._total_frames * 100)
            self._lbl_frame.setText(self.tr(f"{index}/{self._total_frames} ({pct}%)"))
            if not self._slider_pressed:
                slider_val = round(index / self._total_frames * _SLIDER_MAX)
                self._slider.setValue(min(slider_val, _SLIDER_MAX))

    # ── 内部槽 ────────────────────────────────────────

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("选择 CSV 回放文件"), "", self.tr("CSV 文件 (*.csv)")
        )
        if path:
            self._path_edit.setText(path)
            self._btn_play_pause.setEnabled(True)
            self._btn_reset.setEnabled(True)
            self._btn_export_bvh.setEnabled(True)
            self.file_selected.emit(path)

    def _on_fps_changed(self, _index: int) -> None:
        self.fps_changed.emit(self.fps)

    def _on_slider_pressed(self) -> None:
        """用户按下滑块：通知主窗口停止定时器，标记拖动中。"""
        self._slider_pressed = True
        self.seek_started.emit()

    def _on_slider_released(self) -> None:
        """用户松开滑块：计算目标帧并发出 seek 信号。"""
        self._slider_pressed = False
        if self._total_frames <= 0:
            return
        val = self._slider.value()
        target = round(val / _SLIDER_MAX * (self._total_frames - 1))
        target = max(0, min(target, self._total_frames - 1))
        self.seek_requested.emit(target)

    def _on_export_bvh(self) -> None:
        """将当前选中的 CSV 文件转换为 BVH，存放在同目录下。"""
        csv_path = self._path_edit.text()
        if not csv_path:
            return

        _root = str(Path(__file__).parent.parent)
        if _root not in sys.path:
            sys.path.insert(0, _root)

        from src.csv_to_bvh import convert_csv_to_bvh

        self._btn_export_bvh.setEnabled(False)
        self._btn_export_bvh.setText(self.tr("转换中…"))
        try:
            out_path = convert_csv_to_bvh(csv_path)
            QMessageBox.information(
                self, self.tr("导出成功"),
                self.tr(f"BVH 文件已保存至：\n{out_path}"),
            )
        except Exception as e:
            QMessageBox.critical(
                self, self.tr("导出失败"),
                self.tr(f"转换过程中发生错误：\n{e}"),
            )
        finally:
            self._btn_export_bvh.setEnabled(True)
            self._btn_export_bvh.setText(self.tr("导出 BVH…"))
