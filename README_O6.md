# LinkerHand O6 — 右手灵巧手配置说明

> 本文档记录 **O6 右手** 的硬件配置、关节映射、控制项及与 L10 左手的区别。
> 适用于当前分支 `LinkerHandO6`（原 L10 左手已切换为 O6 右手）。

---

## 硬件概览

| 项目 | 值 |
|------|-----|
| 手型 | **O6** |
| 手别 | **右手**（`hand_type="right"`） |
| 自由度 | **6 DOF** |
| 通讯协议 | CAN（默认） / RS485（Modbus-RTU） |
| CAN ID | `0x27` |
| 默认 CAN 通道 | `can0`（Linux）/ `PCAN_USBBUS1`（Windows） |
| CAN 波特率 | 1 Mbps |
| RS485 波特率 | 115200 bps |
| 压力传感器 | ✅ 支持（法向力 + 切向力 + 接近感应） |

---

## 配置设定

在 `linkerhand-python-sdk/LinkerHand/config/setting.yaml` 中：

```yaml
LEFT_HAND:
  EXISTS: False        # 当前无左手
RIGHT_HAND:
  EXISTS: True         # 仅右手 O6
  TOUCH: True          # 带压力传感器
  CAN: "can0"          # CAN 通道
  MODBUS: "None"       # 使用 CAN（设为串口路径则启用 RS485）
  JOINT: O6            # 手型型号
```

---

## 6 个关节映射

O6 右手有 **6 个关节**，拇指 2 自由度（弯曲 + 横摆），其余四指各 1 自由度（仅弯曲）：

| 索引 | 寄存器名 | 中文名 | 控制对象 | 范围 |
|------|---------|--------|---------|------|
| 0 | `THUMB_PITCH` | **大拇指弯曲** | 拇指弯曲/伸直 | 0–255 |
| 1 | `THUMB_YAW` | **大拇指横摆** | 拇指张合（靠掌心↔远离） | 0–255 |
| 2 | `INDEX_PITCH` | **食指弯曲** | 食指弯曲/伸直 | 0–255 |
| 3 | `MIDDLE_PITCH` | **中指弯曲** | 中指弯曲/伸直 | 0–255 |
| 4 | `RING_PITCH` | **无名指弯曲** | 无名指弯曲/伸直 | 0–255 |
| 5 | `LITTLE_PITCH` | **小拇指弯曲** | 小拇指弯曲/伸直 | 0–255 |

> **pose 数组结构**: `[thumb_pitch, thumb_yaw, index, middle, ring, little]`

### 弧度映射（`mapping.py`）

| 关节 | 最小值 (rad) | 最大值 (rad) | 方向 |
|------|-------------|-------------|------|
| 拇指弯曲 | 0 | 0.58 | -1 |
| 拇指横摆 | 0 | 1.36 | -1 |
| 食指弯曲 | 0 | 1.60 | -1 |
| 中指弯曲 | 0 | 1.60 | -1 |
| 无名指弯曲 | 0 | 1.60 | -1 |
| 小拇指弯曲 | 0 | 1.60 | -1 |

---

## 控制项

### 关节位置控制（`finger_move`）

```python
from LinkerHand.linker_hand_api import LinkerHandApi

hand = LinkerHandApi(hand_type="right", hand_joint="O6", can="can0")
hand.set_speed([100, 100, 100, 100, 100, 100])

# 右手张开
hand.finger_move([255, 70, 255, 255, 255, 255])
#               ↑拇指  ↑拇指  ↑食  ↑中  ↑无  ↑小
#               弯曲   横摆   指   指   名   指
```

### 示例姿势

| 姿势 | pose 数组 | 说明 |
|------|-----------|------|
| **张开** | `[255, 70, 255, 255, 255, 255]` | 所有手指伸直 |
| **握拳** | `[67, 151, 0, 0, 0, 0]` | 拇指弯曲+横摆，其余握紧 |
| **拇指食指捏合** | `[180, 30, 180, 0, 0, 0]` | 仅拇指和食指弯曲 |

### 其他控制参数

```python
# 设置速度 (0-255)
hand.set_speed([100, 150, 120, 120, 120, 120])

# 设置最大转矩 (0-255)
hand.set_torque([180, 100, 80, 80, 80, 80])

# 读取当前关节位置
state = hand.get_state()  # 返回 6 个位置值

# 读取力传感器
force = hand.get_force()  # 法向力 + 切向力 + 方向 + 接近感应

# 读取速度
speed = hand.get_speed()
```

---

## O6 vs L10 对比

```
O6  (右手，6 DOF):  拇指(弯曲+横摆) + 食/中/无名/小(仅弯曲)
                    pose = [th_pitch, th_yaw, idx, mid, ring, ltl]
                    索引: [0]       [1]      [2]  [3]  [4]   [5]

L10 (左手，10 DOF): 拇指(弯曲+横摆) + 食/中/无名/小(每指:弯曲+横摆)
                    pose = [th_pitch, th_yaw, idx_p, idx_y, mid_p, mid_y, ring_p, ring_y, ltl_p, ltl_y]
                    索引: [0]       [1]      [2]   [3]    [4]   [5]    [6]    [7]     [8]    [9]
```

**关键差异：**
1. **自由度**: O6 仅 6 个关节，L10 有 10 个
2. **手别**: O6 为右手（CAN ID `0x27`），L10 为左手（CAN ID `0x28`）
3. **手指横摆**: O6 仅拇指有横摆，L10 全部五指都有弯曲+横摆
4. **右手张开拇指横摆**: O6 右手为 `70`（方向与左手相反）

---

## CAN 总线设置（Linux）

```bash
# 初始化 CAN 接口
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 up

# 验证
candump can0
```

详见 [`linkerhand-python-sdk/CAN_SETUP_GUIDE.md`](./linkerhand-python-sdk/CAN_SETUP_GUIDE.md)。

---

## 快速测试

```python
#!/usr/bin/env python3
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "linkerhand-python-sdk"))

from LinkerHand.linker_hand_api import LinkerHandApi

hand = LinkerHandApi(hand_type="right", hand_joint="O6", can="can0")

# 张开
hand.finger_move([255, 70, 255, 255, 255, 255])
input("Press Enter to close...")

# 握拳
hand.finger_move([67, 151, 0, 0, 0, 0])
```
