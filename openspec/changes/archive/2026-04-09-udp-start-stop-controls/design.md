## Context

当前 `MotionGloveMainWindow` 在启动时调用 `MotionGloveSDK_ListenUDPPort(RX_PORT)`，此后 UDP 接收持续运行直到窗口关闭。左侧面板（`LeftPanelWidget`，由 `ui/left_panel.ui` + `ui/left_panel_widget.py` 构成）仅展示来源 IP/端口和错误信息，无任何控制入口。

## Goals / Non-Goals

**Goals:**
- 在左侧面板添加"开始"/"停止"两个按钮，控制 UDP 接收的启停
- 启动时默认已接收，"开始"禁用、"停止"可用
- 停止后清空 IP/端口显示，重启后重新填充
- 端口绑定失败时"开始"可用（允许用户重试），"停止"禁用

**Non-Goals:**
- 不支持更改监听端口（端口仍由 `RX_PORT` 常量决定）
- 不持久化接收状态到磁盘

## Decisions

**1. 按钮放在 `left_panel.ui` 中，逻辑在主窗口**

按钮 widget 定义在 `.ui` 文件（Qt Designer 可编辑），`LeftPanelWidget` 仅暴露 `btn_start`/`btn_stop` 引用和 `set_receiving(bool)` 状态切换方法。信号连接（`clicked` → SDK 调用）在 `MotionGloveMainWindow` 完成，保持 UI 控制器与业务逻辑分离。

替代方案：将 SDK 调用写入 `LeftPanelWidget` — 拒绝，因为 widget 不应直接依赖 SDK 模块。

**2. 重新启动接收复用 `MotionGloveSDK_ListenUDPPort`**

`MotionGloveSDK_CloseUDPPort()` 停止后台线程并释放 socket；再次调用 `MotionGloveSDK_ListenUDPPort(RX_PORT)` 可重新绑定并启动新线程。无需新增 SDK 接口。

**3. 停止时清空面板 IP/端口显示**

`_on_timer` 轮询 `MotionGloveSDK_GetLastRemoteAddr()`；停止接收后该值不再更新但也不清零。需在点击停止时主动将 `lbl_ip`/`lbl_port` 重置为初始占位符，避免显示过期地址。

## Risks / Trade-offs

- [快速连点开始/停止] → SDK 内部使用 RLock 保护状态，连续调用安全；按钮在操作期间短暂禁用可进一步防止竞态（本次不做，风险低）
- [端口仍被占用时点击开始] → `ListenUDPPort` 返回 `-1`，已有错误显示逻辑，复用即可，无需额外处理
