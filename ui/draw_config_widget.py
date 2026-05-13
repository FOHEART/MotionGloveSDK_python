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
    QLabel,
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
    """右侧绘图属性配置面板（自动伸缩，填满父容器宽度）。"""

    def __init__(self, parent=None):
        super().__init__(parent)

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

        # 设置尺寸策略，使控件自动伸缩填充父容器
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._ui.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        def _find(typ, name):  # type: ignore[no-untyped-def]
            w = self._ui.findChild(typ, name)
            assert w is not None, f"UI 控件未找到：{name}"
            return w

        self._sld_joint_radius: QSlider = _find(QSlider, "sld_joint_radius")
        self._lbl_joint_radius_value: QLabel = _find(QLabel, "lbl_joint_radius_value")
        self._btn_joint_color: QPushButton = _find(QPushButton, "btn_joint_color")
        self._sld_link_width: QSlider = _find(QSlider, "sld_link_width")
        self._lbl_link_width_value: QLabel = _find(QLabel, "lbl_link_width_value")
        self._btn_link_color: QPushButton = _find(QPushButton, "btn_link_color")
        self._sld_axis_length: QSlider = _find(QSlider, "sld_axis_length")
        self._lbl_axis_length_value: QLabel = _find(QLabel, "lbl_axis_length_value")
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
        self._update_joint_radius_value(int(defaults.joint_radius * 1000))

        self._sld_link_width.setMinimum(1)
        self._sld_link_width.setMaximum(30)
        self._sld_link_width.setTickInterval(1)
        self._sld_link_width.setValue(int(defaults.link_width))
        self._update_link_width_value(int(defaults.link_width))

        self._sld_axis_length.setMinimum(1)
        self._sld_axis_length.setMaximum(30)
        self._sld_axis_length.setTickInterval(1)
        self._sld_axis_length.setValue(int(defaults.axis_length * 1000))
        self._update_axis_length_value(int(defaults.axis_length * 1000))

        _apply_btn_color(self._btn_joint_color, defaults.joint_color)
        _apply_btn_color(self._btn_link_color, defaults.link_color)

        # 连接滑块信号到槽函数，实时更新值显示
        self._sld_joint_radius.valueChanged.connect(self._update_joint_radius_value)
        self._sld_link_width.valueChanged.connect(self._update_link_width_value)
        self._sld_axis_length.valueChanged.connect(self._update_axis_length_value)

        self._btn_joint_color.clicked.connect(self._pick_joint_color)
        self._btn_link_color.clicked.connect(self._pick_link_color)
        btn_save.clicked.connect(self._on_save)
        btn_load.clicked.connect(self._on_load)

    # ── 内部工具 ──────────────────────────────────────

    def _update_joint_radius_value(self, value: int) -> None:
        """更新关节球半径值显示标签。"""
        radius = value * 0.001
        self._lbl_joint_radius_value.setText(f"{radius:.3f}")

    def _update_link_width_value(self, value: int) -> None:
        """更新骨骼连线粗细值显示标签。"""
        self._lbl_link_width_value.setText(f"{value}")

    def _update_axis_length_value(self, value: int) -> None:
        """更新坐标轴长度值显示标签。"""
        length = value * 0.001
        self._lbl_axis_length_value.setText(f"{length:.3f}")

    def _pick_joint_color(self) -> None:
        """选择关节球颜色（使用非原生对话框避免阻塞）。"""
        qc = QColor(*[int(c * 255) for c in self._joint_color])
        from PySide6.QtWidgets import QColorDialog
        # 使用 DontUseNativeDialog 选项避免主线程阻塞
        chosen = QColorDialog.getColor(
            qc, 
            self, 
            self.tr("选择关节球颜色"),
            options=QColorDialog.ColorDialogOption.DontUseNativeDialog
        )
        if chosen.isValid():
            self._joint_color = _qcolor_to_color(chosen)
            _apply_btn_color(self._btn_joint_color, self._joint_color)

    def _pick_link_color(self) -> None:
        """选择连线颜色（使用非原生对话框避免阻塞）。"""
        qc = QColor(*[int(c * 255) for c in self._link_color])
        from PySide6.QtWidgets import QColorDialog
        # 使用 DontUseNativeDialog 选项避免主线程阻塞
        chosen = QColorDialog.getColor(
            qc, 
            self, 
            self.tr("选择连线颜色"),
            options=QColorDialog.ColorDialogOption.DontUseNativeDialog
        )
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
        self._update_joint_radius_value(int(config.joint_radius * 1000))
        self._joint_color = config.joint_color
        _apply_btn_color(self._btn_joint_color, self._joint_color)

        self._sld_link_width.setValue(int(config.link_width))
        self._update_link_width_value(int(config.link_width))
        self._link_color = config.link_color
        _apply_btn_color(self._btn_link_color, self._link_color)

        self._sld_axis_length.setValue(int(config.axis_length * 1000))
        self._update_axis_length_value(int(config.axis_length * 1000))
