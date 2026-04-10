"""draw_config_widget.py
右侧绘图配置面板，提供 Slider + 取色板控件，实时调整 VTK 场景中的绘制属性。

公开接口
--------
DrawConfigWidget(parent)
    .current_config() -> DrawConfig      — 读取当前控件值，返回配置快照
    .load_from_config(config: DrawConfig) — 将配置反写回控件
"""

import os
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QGroupBox, QFileDialog, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

# draw_config_io 与本文件同在 python_draw3d/（通过 sys.path 已包含）
from draw_config_io import DrawConfig, save_config, load_config


def _color_to_qcolor(color: tuple[float, float, float]) -> QColor:
    return QColor(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))


def _qcolor_to_color(qc: QColor) -> tuple[float, float, float]:
    return (qc.red() / 255.0, qc.green() / 255.0, qc.blue() / 255.0)


def _apply_btn_color(btn: QPushButton, color: tuple[float, float, float]) -> None:
    r, g, b = (int(c * 255) for c in color)
    # 根据亮度选择文字颜色，保证可读性
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    text_color = "black" if luma > 128 else "white"
    btn.setStyleSheet(
        f"background-color: rgb({r},{g},{b}); color: {text_color};"
    )


class DrawConfigWidget(QWidget):
    """右侧绘图属性配置面板（固定宽度 220px）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)

        defaults = DrawConfig.default()

        # 当前颜色状态（float tuple，避免每次从按钮 stylesheet 反解析）
        self._joint_color = defaults.joint_color
        self._link_color = defaults.link_color

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 12, 8, 12)
        root.setSpacing(8)

        # ── 关节球 ──
        joint_group = QGroupBox("关节球")
        joint_layout = QVBoxLayout(joint_group)
        joint_layout.setSpacing(4)

        joint_layout.addWidget(QLabel("半径"))
        self._sld_joint_radius = self._make_slider(1, 10, int(defaults.joint_radius * 1000))
        joint_layout.addWidget(self._sld_joint_radius)

        joint_layout.addWidget(QLabel("颜色"))
        self._btn_joint_color = QPushButton("选择颜色")
        _apply_btn_color(self._btn_joint_color, defaults.joint_color)
        self._btn_joint_color.clicked.connect(self._pick_joint_color)
        joint_layout.addWidget(self._btn_joint_color)

        root.addWidget(joint_group)

        # ── 骨骼连线 ──
        link_group = QGroupBox("骨骼连线")
        link_layout = QVBoxLayout(link_group)
        link_layout.setSpacing(4)

        link_layout.addWidget(QLabel("粗细"))
        self._sld_link_width = self._make_slider(1, 20, int(defaults.link_width))
        link_layout.addWidget(self._sld_link_width)

        link_layout.addWidget(QLabel("颜色"))
        self._btn_link_color = QPushButton("选择颜色")
        _apply_btn_color(self._btn_link_color, defaults.link_color)
        self._btn_link_color.clicked.connect(self._pick_link_color)
        link_layout.addWidget(self._btn_link_color)

        root.addWidget(link_group)

        # ── 坐标轴 ──
        axis_group = QGroupBox("坐标轴")
        axis_layout = QVBoxLayout(axis_group)
        axis_layout.setSpacing(4)

        axis_layout.addWidget(QLabel("长度"))
        self._sld_axis_length = self._make_slider(1, 30, int(defaults.axis_length * 1000))
        axis_layout.addWidget(self._sld_axis_length)

        root.addWidget(axis_group)

        # ── 配置 IO ──
        io_group = QGroupBox("配置文件")
        io_layout = QVBoxLayout(io_group)
        io_layout.setSpacing(4)

        btn_save = QPushButton("导出配置")
        btn_save.clicked.connect(self._on_save)
        io_layout.addWidget(btn_save)

        btn_load = QPushButton("加载配置")
        btn_load.clicked.connect(self._on_load)
        io_layout.addWidget(btn_load)

        root.addWidget(io_group)

        root.addStretch()

    # ── 内部工具 ──────────────────────────────────────

    @staticmethod
    def _make_slider(min_val: int, max_val: int, value: int) -> QSlider:
        s = QSlider(Qt.Orientation.Horizontal)
        s.setMinimum(min_val)
        s.setMaximum(max_val)
        s.setValue(value)
        s.setTickInterval(1)
        return s

    def _pick_joint_color(self) -> None:
        qc = QColor(*[int(c * 255) for c in self._joint_color])
        from PySide6.QtWidgets import QColorDialog
        chosen = QColorDialog.getColor(qc, self, "选择关节球颜色")
        if chosen.isValid():
            self._joint_color = _qcolor_to_color(chosen)
            _apply_btn_color(self._btn_joint_color, self._joint_color)

    def _pick_link_color(self) -> None:
        qc = QColor(*[int(c * 255) for c in self._link_color])
        from PySide6.QtWidgets import QColorDialog
        chosen = QColorDialog.getColor(qc, self, "选择连线颜色")
        if chosen.isValid():
            self._link_color = _qcolor_to_color(chosen)
            _apply_btn_color(self._btn_link_color, self._link_color)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "导出绘图配置", "", "JSON 文件 (*.json)"
        )
        if path:
            save_config(self.current_config(), path)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "加载绘图配置", "", "JSON 文件 (*.json)"
        )
        if path:
            try:
                cfg = load_config(path)
                self.load_from_config(cfg)
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "加载失败", str(e))

    # ── 公开接口 ──────────────────────────────────────

    def current_config(self) -> DrawConfig:
        """返回当前所有控件值的 DrawConfig 快照。"""
        return DrawConfig(
            joint_radius=self._sld_joint_radius.value() * 0.001,
            joint_color=self._joint_color,
            link_width=float(self._sld_link_width.value()),
            link_color=self._link_color,
            axis_length=self._sld_axis_length.value() * 0.001,
        )

    def load_from_config(self, config: DrawConfig) -> None:
        """将外部配置同步回控件状态。"""
        self._sld_joint_radius.setValue(int(config.joint_radius * 1000))
        self._joint_color = config.joint_color
        _apply_btn_color(self._btn_joint_color, self._joint_color)

        self._sld_link_width.setValue(int(config.link_width))
        self._link_color = config.link_color
        _apply_btn_color(self._btn_link_color, self._link_color)

        self._sld_axis_length.setValue(int(config.axis_length * 1000))
