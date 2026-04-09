## Why

用户需要在运行时控制 UDP 数据接收的开启与关闭，而无需重启程序。当前版本在程序启动后自动开始接收并无法中途暂停，不便于调试和设备切换。

## What Changes

- 在左侧面板新增"开始"和"停止"两个按钮
- 程序启动时自动开始接收，"开始"按钮初始为禁用状态，"停止"按钮为可用状态
- 点击"停止"后调用 `MotionGloveSDK_CloseUDPPort()` 停止接收，"停止"禁用、"开始"可用
- 点击"开始"后重新调用 `MotionGloveSDK_ListenUDPPort(port)` 启动接收，按钮状态反转

## Capabilities

### New Capabilities

- `udp-receive-controls`: 左侧面板中的开始/停止 UDP 接收控制按钮，含状态联动逻辑

### Modified Capabilities

- `network-info-panel`: 面板新增两个控制按钮，布局需在现有 IP/端口信息区域下方追加

## Impact

- `ui/left_panel.ui`：新增两个 QPushButton（开始/停止）
- `ui/left_panel_widget.py`：暴露按钮引用，添加按钮状态切换方法
- `motionGloveSDK_example3_3dView.py`：连接按钮信号到 SDK 的启动/停止逻辑
- `src/motionGloveSDK.py`：无变更，使用现有 `MotionGloveSDK_ListenUDPPort` 和 `MotionGloveSDK_CloseUDPPort`
