## Context

`ui/linker_hand_widget.py` 是 3D 视图中显示手套骨骼角度并驱动灵巧手电机的面板。当前为 L10 左手硬编码，需要切换为 O6 右手。

### 当前 L10 状态

```
row_specs (10 项):
  ["左手拇指根部",         th_pitch   ] → 电机 0
  ["左手拇指侧摆",         th_yaw     ] → 电机 1
  ["左手食指根部",         idx_pitch  ] → 电机 2
  ["左手中指根部",         mid_pitch  ] → 电机 3
  ["左手无名指根部",       ring_pitch ] → 电机 4
  ["左手小指根部",         ltl_pitch  ] → 电机 5
  ["左手食指侧摆",         idx_yaw    ] → 电机 6  ← O6 不存在
  ["左手无名指侧摆",       ring_yaw   ] → 电机 7  ← O6 不存在
  ["左手小指侧摆",         ltl_yaw    ] → 电机 8  ← O6 不存在
  ["左手拇指旋转",         th_z       ] → (无电机) ← O6 不存在

motor_labels: thumb, thumb_adduction, index, middle, ring, pinky,
              index_adduction, ring_adduction, pinky_adduction
→ 移除后 3 个
```

### 目标 O6 状态

```
row_specs (6 项):
  ["右手拇指弯曲",         th_pitch   ] → 电机 0
  ["右手拇指侧摆",         th_yaw     ] → 电机 1
  ["右手食指弯曲",         idx_pitch  ] → 电机 2
  ["右手中指弯曲",         mid_pitch  ] → 电机 3
  ["右手无名指弯曲",       ring_pitch ] → 电机 4
  ["右手小指弯曲",         ltl_pitch  ] → 电机 5

motor_labels: thumb, thumb_adduction, index, middle, ring, pinky
→ 仅 6 个
```

## Goals / Non-Goals

**Goals:**
- row_specs 精简为 6 项（O6 对应关节）
- motor_labels 从 9 个 → 6 个
- 所有骨骼引用从 `LeftHand*` → `RightHand*`
- 所有标签文本从 "左手" → "右手"
- `_send_to_linker_hand()` pose 6 元素而非 10 元素
- 连接参数 `hand_type="right"`、`hand_joint="O6"`
- 拇指侧摆映射使用 O6 右手值
- 移除 `_refresh_from_latest_frame` 中 4 个多余关节的电机计算逻辑

**Non-Goals:**
- 不修改 `ui/linker_hand_widget.ui`（仅 .py 文件变更）
- 不修改 `motionGloveSDK_example3_3dView.py`（接口不变）
- 不修改 LinkerHand SDK 核心代码

## Decisions

### D1 — row_specs 精简为 6 项

```
索引  标签文本          骨骼名           轴向
 0    右手拇指弯曲       RightHandThumb1, RightHandThumb2, RightHandThumb3     y
 1    右手拇指侧摆       RightHandThumb1                                       y
 2    右手食指弯曲       RightHandIndex1, RightHandIndex2, RightHandIndex3     y
 3    右手中指弯曲       RightHandMiddle1, RightHandMiddle2, RightHandMiddle3  y
 4    右手无名指弯曲     RightHandRing1, RightHandRing2, RightHandRing3        y
 5    右手小指弯曲       RightHandPinky1, RightHandPinky2, RightHandPinky3     y
```

### D2 — motor_labels 精简为 6 项

移除: `lbl_motor_index_adduction`, `lbl_motor_ring_adduction`, `lbl_motor_pinky_adduction`

保留: `lbl_motor_thumb`, `lbl_motor_thumb_adduction`, `lbl_motor_index`, `lbl_motor_middle`, `lbl_motor_ring`, `lbl_motor_pinky`

### D3 — pose 数组从 10 → 6

```python
# 旧 L10: motor_values = [255] * 10
# 新 O6:  motor_values = [255] * 6

# 索引映射（O6）:
# [0] thumb pitch      ← lbl_motor_thumb
# [1] thumb yaw        ← lbl_motor_thumb_adduction
# [2] index pitch      ← lbl_motor_index
# [3] middle pitch     ← lbl_motor_middle
# [4] ring pitch       ← lbl_motor_ring
# [5] little pitch     ← lbl_motor_pinky
```

### D4 — 拇指侧摆映射适配 O6 右手

当前 L10 左手: `0~120° → 255~0` (反向)

O6 右手张开横摆值为 70（参考 README_O6.md），映射逻辑：`0~120° → 255~0` 保持不变，但角度范围可能需要调整。暂时保持相同映射逻辑，后续根据实际手套数据校准。

### D5 — 连接参数变更

```python
# 旧
self._linker_api = LinkerHandApi(
    hand_type="left", hand_joint="L10", can="can0", modbus="None")

# 新
self._linker_api = LinkerHandApi(
    hand_type="right", hand_joint="O6", can="can0", modbus="None")
```

## Risks / Trade-offs

- **UI 控件孤儿**: `.ui` 文件中可能包含已被移除控件的引用。如果 _bind_labels 中使用 `findChild` 找不到控件会报 `RuntimeError`。Mitigation: 仅删除 Python 侧引用，不加载不存在的 UI 控件时会静默跳过（改用 `try/except` 或先检查是否存在）。
- **校准值准确性**: O6 右手拇指侧摆张开值为 70（不同于左手 179），需实际测试确认。当前保留原有映射逻辑作为起点。
- **向后兼容**: 此分支仅用于 O6 右手，不需要向后兼容 L10。

## Open Questions

1. `ui/linker_hand_widget.ui` 中是否有需要同步移除的多余控件？（当前策略：仅改 .py，不改 .ui）
2. O6 拇指侧摆的映射范围是否与 L10 一致（0~120° → 255~0）？需实际测试校准。
