from __future__ import annotations

from typing import TypeVar

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


T = TypeVar("T")


def show_boot_mode_dialog(udp_value: T, csv_value: T) -> T | None:
    """Show the startup mode dialog and return the selected value.

    The caller provides the concrete values to return for UDP and CSV mode,
    which keeps this module independent from the main application's enum type.
    """
    chosen: list[T | None] = [None]

    dlg = QDialog()
    dlg.setWindowTitle(QCoreApplication.translate("BootDialog", "选择启动模式"))
    dlg.setFixedSize(320, 140)
    dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

    layout = QVBoxLayout(dlg)
    layout.setSpacing(12)
    layout.setContentsMargins(20, 20, 20, 20)

    label = QLabel(QCoreApplication.translate("BootDialog", "请选择启动模式："))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label)

    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(16)

    btn_udp = QPushButton(QCoreApplication.translate("BootDialog", "实时 UDP 流"))
    btn_csv = QPushButton(QCoreApplication.translate("BootDialog", "CSV 文件回放"))
    btn_udp.setFixedHeight(36)
    btn_csv.setFixedHeight(36)

    def _pick_udp() -> None:
        chosen[0] = udp_value
        dlg.accept()

    def _pick_csv() -> None:
        chosen[0] = csv_value
        dlg.accept()

    btn_udp.clicked.connect(_pick_udp)
    btn_csv.clicked.connect(_pick_csv)

    btn_layout.addWidget(btn_udp)
    btn_layout.addWidget(btn_csv)
    layout.addLayout(btn_layout)

    dlg.exec()
    return chosen[0]
