"""@file  boot_mode_dialog.py
@brief 应用启动模式选择对话框（PySide6）。
@details
弹出「实时 UDP 流 / CSV 文件回放」二选一对话框。返回值由调用方注入
（泛型参数），使本模块不依赖主应用的枚举类型。仅 UI 层使用，
不做单元测试（需 Qt 事件循环）。
"""

from __future__ import annotations

from typing import TypeVar

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


T = TypeVar("T")


def show_boot_mode_dialog(udp_value: T, csv_value: T) -> T | None:
    """@brief 显示启动模式对话框并返回用户选择。

    @details 调用方提供 UDP / CSV 两种模式各自要返回的具体值，
             本模块与主应用的枚举类型解耦。用户关闭对话框（未选择）时返回 None。
    @param udp_value 选择「实时 UDP 流」时返回的值。
    @param csv_value 选择「CSV 文件回放」时返回的值。
    @return 所选值（T）；用户直接关闭对话框返回 None。
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
