## 1. 精简 row_specs 与指关节标签

- [x] 1.1 修改 `_bind_labels()` 中的 `row_specs`：从 10 项精简为 6 项
  - 保留: 拇指弯曲、拇指侧摆、食指弯曲、中指弯曲、无名指弯曲、小指弯曲
  - 移除: 食指侧摆、无名指侧摆、小指侧摆、拇指旋转
- [x] 1.2 所有标签文本从 "左手" → "右手"
- [x] 1.3 所有骨骼名从 `LeftHand*` → `RightHand*`
- [x] 1.4 移除拇指侧摆的 `axis: "y"` 改为 `axis: "y"`（保持默认，无需显式声明）

## 2. 精简 motor_labels 绑定

- [x] 2.1 移除 `lbl_motor_index_adduction`、`lbl_motor_ring_adduction`、`lbl_motor_pinky_adduction` 的绑定代码（`_bind_labels` 末尾 3 组 `findChild` + RuntimeError）
- [x] 2.2 确认保留的 6 个 motor label 绑定正确：
  `lbl_motor_thumb`, `lbl_motor_thumb_adduction`, `lbl_motor_index`, `lbl_motor_middle`, `lbl_motor_ring`, `lbl_motor_pinky`

## 3. 修改连接参数

- [x] 3.1 `_on_connect()` → `_connect_worker()` 中:
  - `hand_type="left"` → `hand_type="right"`
  - `hand_joint="L10"` → `hand_joint="O6"`
  - 日志文本 "左手 L10" → "右手 O6"
- [x] 3.2 日志文本: `"正在连接灵巧手 (left L10) …"` → `"正在连接灵巧手 (right O6) …"`

## 4. 精简 _send_to_linker_hand() pose 数组

- [x] 4.1 `motor_values` 初始化从 `[255] * 10` → `[255] * 6`
- [x] 4.2 移除电机索引 6, 7, 8 的提取逻辑（index_adduction, ring_adduction, pinky_adduction）
- [x] 4.3 确保 6 元素 pose 数组传递给 `api.finger_move(pose=pose)`

## 5. 精简 _refresh_from_latest_frame() 电机值计算

- [x] 5.1 移除食指侧摆电机计算块（约 8 行: `index_adduction_text = ...`）
- [x] 5.2 移除无名指侧摆电机计算块（约 8 行: `ring_adduction_text = ...`）
- [x] 5.3 移除小指侧摆电机计算块（约 8 行: `pinky_adduction_text = ...`）
- [x] 5.4 保留拇指侧摆、拇指弯曲、食指、中指、无名指、小指的计算逻辑

## 6. 更新手指标签文本（_refresh_from_latest_frame 中的 key 引用）

- [x] 6.1 所有 `finger_labels["左手*"]` → `finger_labels["右手*"]`
- [x] 6.2 电机标签显示文本 "拇指根部" → "拇指弯曲"
  - `self.lbl_motor_thumb.setText(f"拇指根部：{motor_value:.1f}")` → `f"拇指弯曲：{motor_value:.1f}"`
- [x] 6.3 其余电机标签保持一致

## 7. 清理与验证

- [x] 7.1 运行 `pyright` 检查类型错误 — 无新增错误（仅预存 PySide6 QUiLoader 类型噪音）
- [x] 7.2 确认 `motionGloveSDK_example3_3dView.py` 中 `update_linker_angles` 调用无需修改
- [x] 7.3 在 3D 视图中测试：面板显示 6 行而非 10 行，连接日志显示 "右手 O6"
