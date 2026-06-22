## Why

当前 `ui/linker_hand_widget.py` 是为 **L10 左手（10 DOF）** 硬编码的控件。工程已切换到 `LinkerHandO6` 分支，实际硬件是 **O6 右手（6 DOF）**。现有控件包含 4 个 O6 不存在的关节（食指侧摆、无名指侧摆、小指侧摆、拇指旋转），连接时使用 `hand_type="left"` 和 `hand_joint="L10"`，导致与实际硬件不匹配。

详见 [`README_O6.md`](../../README_O6.md) 中 O6 关节映射。

## What Changes

- 将 `LinkerHandWidget` 从 L10 左手配置切换为 O6 右手配置
- 移除不存在的 4 个手指关节控件：食指侧摆、无名指侧摆、小指侧摆、拇指旋转
- 精简 `row_specs`：从 10 项 → 6 项（仅保留 O6 的 6 个关节）
- 精简电机标签：从 9 个 → 6 个
- `_send_to_linker_hand()` pose 数组：从 10 元素 → 6 元素
- 连接参数：`hand_type="right"`、`hand_joint="O6"`
- 骨骼名称：从 `LeftHand*` → `RightHand*`
- 标签文本：从 "左手" → "右手"
- O6 拇指侧摆映射：右手张开横摆值 `70`（不同于左手 `179`）

## Capabilities

### Modified Capabilities

- `linker-hand-widget`: 从 L10 左手 → O6 右手

### Removed Capabilities

- 食指侧摆角度显示 & 电机值计算
- 无名指侧摆角度显示 & 电机值计算
- 小指侧摆角度显示 & 电机值计算
- 拇指旋转角度显示（O6 拇指仅弯曲+横摆，无旋转）

## Impact

- `ui/linker_hand_widget.py` — 主要修改文件
- `motionGloveSDK_example3_3dView.py` — 集成点无需修改（`update_linker_angles` 接口不变）
- `ui/linker_hand_widget.ui` — 可能需要移除多余的 UI 控件（如果 .ui 中有独立控件）
- `README_O6.md` — 已存在，作为参考文档
