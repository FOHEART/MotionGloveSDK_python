"""draw_config_widget.py
右侧绘图配置面板，提供 Slider + 取色板控件，实时调整 VTK 场景中的绘制属性。

公开接口
--------
DrawConfigWidget(parent)
    .current_config() -> DrawConfig      — 读取当前控件值，返回配置快照
    .load_from_config(config: DrawConfig) — 将配置反写回控件
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QSlider,
    QPushButton,
    QFileDialog,
)
from PySide6.QtGui import QColor
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice

# draw_config_io 与本文件同在 python_draw3d/（通过 sys.path 已包含）
from draw_config_io import DrawConfig, save_config, load_config


def _ui_path() -> Path:
    """返回 draw_config_panel.ui 的绝对路径，兼容源码运行和 PyInstaller 打包。"""
    candidates: list[Path] = []

    candidates.append(Path(__file__).parent / "draw_config_panel.ui")
    candidates.append(Path(__file__).parent.parent / "ui" / "draw_config_panel.ui")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "ui" / "draw_config_panel.ui")
        candidates.append(Path(meipass) / "_internal" / "ui" / "draw_config_panel.ui")

    try:
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "ui" / "draw_config_panel.ui")
        candidates.append(exe_dir / "_internal" / "ui" / "draw_config_panel.ui")
    except Exception:
        exe_dir = None

    candidates.append(Path.cwd() / "ui" / "draw_config_panel.ui")
    candidates.append(Path.cwd() / "_internal" / "ui" / "draw_config_panel.ui")

    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue

    search_roots = [Path(__file__).parent, Path(__file__).parent.parent]
    if exe_dir is not None:
        search_roots.append(exe_dir)
    search_roots.append(Path.cwd())

    for root in search_roots:
        try:
            for p in root.rglob("draw_config_panel.ui"):
                return p
        except Exception:
            continue

    return Path(__file__).parent / "draw_config_panel.ui"


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

        loader = QUiLoader()
        ui_file = QFile(str(_ui_path()))
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_ui_path()}")
        self._ui = loader.load(ui_file)
        ui_file.close()
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_ui_path()}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._ui)

        def _find(typ, name):  # type: ignore[no-untyped-def]
            w = self._ui.findChild(typ, name)
            assert w is not None, f"UI 控件未找到：{name}"
            return w

        self._sld_joint_radius: QSlider = _find(QSlider, "sld_joint_radius")
        self._btn_joint_color: QPushButton = _find(QPushButton, "btn_joint_color")
        self._sld_link_width: QSlider = _find(QSlider, "sld_link_width")
        self._btn_link_color: QPushButton = _find(QPushButton, "btn_link_color")
        self._sld_axis_length: QSlider = _find(QSlider, "sld_axis_length")
        btn_save: QPushButton = _find(QPushButton, "btn_save_config")
        btn_load: QPushButton = _find(QPushButton, "btn_load_config")

        defaults = DrawConfig.default()

        # 当前颜色状态（float tuple，避免每次从按钮 stylesheet 反解析）
        self._joint_color = defaults.joint_color
        self._link_color = defaults.link_color

        self._sld_joint_radius.setMinimum(1)
        self._sld_joint_radius.setMaximum(10)
        self._sld_joint_radius.setTickInterval(1)
        self._sld_joint_radius.setValue(int(defaults.joint_radius * 1000))

        self._sld_link_width.setMinimum(1)
        self._sld_link_width.setMaximum(30)
        self._sld_link_width.setTickInterval(1)
        self._sld_link_width.setValue(int(defaults.link_width))

        self._sld_axis_length.setMinimum(1)
        self._sld_axis_length.setMaximum(30)
        self._sld_axis_length.setTickInterval(1)
        self._sld_axis_length.setValue(int(defaults.axis_length * 1000))

        _apply_btn_color(self._btn_joint_color, defaults.joint_color)
        _apply_btn_color(self._btn_link_color, defaults.link_color)

        self._btn_joint_color.clicked.connect(self._pick_joint_color)
        self._btn_link_color.clicked.connect(self._pick_link_color)
        btn_save.clicked.connect(self._on_save)
        btn_load.clicked.connect(self._on_load)

    # ── 内部工具 ──────────────────────────────────────

    def _pick_joint_color(self) -> None:
        qc = QColor(*[int(c * 255) for c in self._joint_color])
        from PySide6.QtWidgets import QColorDialog
        chosen = QColorDialog.getColor(qc, self, self.tr("选择关节球颜色"))
        if chosen.isValid():
            self._joint_color = _qcolor_to_color(chosen)
            _apply_btn_color(self._btn_joint_color, self._joint_color)

    def _pick_link_color(self) -> None:
        qc = QColor(*[int(c * 255) for c in self._link_color])
        from PySide6.QtWidgets import QColorDialog
        chosen = QColorDialog.getColor(qc, self, self.tr("选择连线颜色"))
        if chosen.isValid():
            self._link_color = _qcolor_to_color(chosen)
            _apply_btn_color(self._btn_link_color, self._link_color)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出绘图配置"), "", self.tr("JSON 文件 (*.json)")
        )
        if path:
            save_config(self.current_config(), path)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("加载绘图配置"), "", self.tr("JSON 文件 (*.json)")
        )
        if path:
            try:
                cfg = load_config(path)
                self.load_from_config(cfg)
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, self.tr("加载失败"), str(e))

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
