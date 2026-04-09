## 1. UI 布局（left_panel.ui）

- [x] 1.1 在 `ui/left_panel.ui` 的 `lbl_error` 下方、垂直弹簧上方，新增一个水平布局（`btn_row`），包含 `btn_start`（文字"开始"）和 `btn_stop`（文字"停止"）两个 QPushButton

## 2. 面板控制器（left_panel_widget.py）

- [x] 2.1 在 `LeftPanelWidget.__init__` 中通过 `findChild(QPushButton, ...)` 获取 `self.btn_start` 和 `self.btn_stop` 引用
- [x] 2.2 添加 `set_receiving(active: bool)` 方法：`active=True` 时禁用 Start、启用 Stop；`active=False` 时启用 Start、禁用 Stop
- [x] 2.3 在 `QPushButton` 导入中补充 `from PySide6.QtWidgets import ... QPushButton`

## 3. 主窗口逻辑（motionGloveSDK_example3_3dView.py）

- [x] 3.1 在 `_build_central()` 或窗口初始化阶段，将 `btn_start.clicked` 连接到 `_on_start_clicked` 槽
- [x] 3.2 在 `_build_central()` 或窗口初始化阶段，将 `btn_stop.clicked` 连接到 `_on_stop_clicked` 槽
- [x] 3.3 实现 `_on_stop_clicked`：调用 `MotionGloveSDK_CloseUDPPort()`，调用 `self._left_panel.set_receiving(False)`，重置 `lbl_ip`/`lbl_port` 为占位符文字
- [x] 3.4 实现 `_on_start_clicked`：调用 `MotionGloveSDK_ListenUDPPort(RX_PORT)`；成功（返回 0）时调用 `self._left_panel.set_receiving(True)` 并调用 `self._left_panel.clear_error()`；失败（返回 -1）时查询占用信息并调用 `self._left_panel.show_port_error(...)`，保持 `set_receiving(False)` 状态
- [x] 3.5 在 `main()` 中，端口绑定成功后调用 `window._left_panel.set_receiving(True)`；绑定失败时调用 `window._left_panel.set_receiving(False)`（已有 `show_port_error`，补充 `set_receiving` 调用即可）
