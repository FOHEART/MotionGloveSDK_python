# ViveTrackerMgr 统一管理结构体使用指南

## 概述

`ViveTrackerMgr` 是一个为 VR Tracker 设计的统一管理结构体，集中管理 Tracker 的所有关键信息，包括位置、旋转欧拉角、旋转矩阵和四元数等。配合 `TrackerManager`，可以方便地管理多个 Tracker。

## 核心组件

### 1. ViveTrackerMgr 结构体

#### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | str | Tracker 名称（如 "left", "right"）|
| `position_x/y/z` | float | 位置坐标（单位：米）|
| `euler_yaw/pitch/roll` | float | 欧拉角（单位：度）|
| `quat_w/x/y/z` | float | 四元数（w, x, y, z）|
| `rotation_matrix` | np.ndarray | 3×3 旋转矩阵 |
| `is_online` | bool | 是否在线 |
| `valid` | bool | 数据是否有效 |
| `timestamp` | float | 最后更新时间 |
| `remarks` | str | 备注信息 |

#### 核心方法

```python
# 更新位置
tracker.update_position(x, y, z)

# 更新欧拉角（度）
tracker.update_euler(yaw, pitch, roll)

# 更新四元数
tracker.update_quat(w, x, y, z)

# 更新旋转矩阵
tracker.update_rotation_matrix(matrix_3x3)

# 获取信息
pos = tracker.get_position()           # 返回 (x, y, z)
euler = tracker.get_euler()            # 返回 (yaw, pitch, roll)
quat = tracker.get_quat()              # 返回 (w, x, y, z)
matrix = tracker.get_rotation_matrix() # 返回 3×3 np.ndarray
```

### 2. TrackerManager 管理器

#### 核心方法

```python
# 注册新 Tracker
tracker = manager.register_tracker("left")

# 获取指定 Tracker
tracker = manager.get_tracker("left")

# 获取所有 Tracker
trackers = manager.get_all_trackers()  # {name: ViveTrackerMgr, ...}

# 获取在线的 Tracker
online = manager.get_online_trackers()

# 移除 Tracker
manager.remove_tracker("left")

# 清空所有 Tracker
manager.clear()

# 打印摘要
manager.print_summary()
```

#### 检查和访问

```python
# 检查是否存在
if "left" in manager:
    print("左手 Tracker 已注册")

# 通过 [] 操作符访问
tracker = manager["left"]

# 获取 Tracker 总数
count = len(manager)
```

### 3. 全局管理器

```python
from triad_openvr.tracker_manager import get_global_tracker_manager

# 获取全局管理器（单例）
global_mgr = get_global_tracker_manager()

# 使用方式与 TrackerManager 相同
global_mgr.register_tracker("left")
```

## 在 ViveTrackerWidget 中使用

### 获取管理器

```python
# 在 ViveTrackerWidget 实例中
tracker_mgr = widget.get_tracker_manager()

# 或者获取全局管理器
from triad_openvr.tracker_manager import get_global_tracker_manager
global_mgr = get_global_tracker_manager()
```

### 访问 Tracker 信息

```python
# 方法 1：通过管理器获取
widget_mgr = widget.get_tracker_manager()
left_tracker = widget_mgr.get_tracker("left")

# 方法 2：直接从 widget 获取
left_tracker = widget.get_tracker("left")

# 方法 3：获取所有 Tracker
all_trackers = widget.get_all_trackers()
for name, tracker in all_trackers.items():
    print(f"{name}: {tracker.get_position()}")

# 方法 4：只获取在线的 Tracker
online = widget.get_online_trackers()
```

### 获取数据

```python
# 获取位置
x, y, z = tracker.get_position()

# 获取欧拉角
yaw, pitch, roll = tracker.get_euler()

# 获取四元数
w, x, y, z = tracker.get_quat()

# 获取旋转矩阵
rotation_matrix = tracker.get_rotation_matrix()  # numpy 3×3 数组

# 获取状态信息
print(f"在线: {tracker.is_online}")
print(f"有效: {tracker.valid}")
print(f"更新时间: {tracker.timestamp}")
print(f"备注: {tracker.remarks}")
```

## 数据流程

### 自动更新流程

```
OpenVR 追踪数据（60Hz）
    ↓
vive_tracker_widget._tracking_loop()
    ↓
解析为 TrackerData
    ↓
_on_update_timer()（60Hz）
    ↓
1. 更新 UI 标签
2. 更新 ViveTrackerMgr（通过 TrackerManager）
3. 更新模型位置和旋转
    ↓
应用程序可以随时访问 TrackerManager 获取最新数据
```

### 数据更新在 ViveTrackerWidget 中的实现

```python
# 在 _on_update_timer() 中
left_tracker = self._tracker_manager.get_tracker("left")
if left_tracker is None:
    left_tracker = self._tracker_manager.register_tracker("left")

# 更新所有信息
left_tracker.is_online = True
left_tracker.valid = True
left_tracker.update_position(x, y, z)
left_tracker.update_euler(yaw, pitch, roll)
left_tracker.update_quat(qw, qx, qy, qz)
left_tracker.timestamp = time.time()
```

## 实际使用示例

### 示例 1：显示所有 Tracker 信息

```python
from ui.vive_tracker_widget import ViveTrackerWidget

# 创建 widget
widget = ViveTrackerWidget()
widget.set_renderer_and_callbacks(renderer, ...)

# 启动追踪
widget._on_start_tracking_clicked()

# 获取信息
mgr = widget.get_tracker_manager()
widget.print_tracker_summary()

# 输出：
# ============================================================
# Tracker 管理器摘要
# ============================================================
# 
# ViveTrackerMgr: left
#   位置: (0.5000, -0.2000, 1.0000) m
#   欧拉角: Yaw=30.00° Pitch=45.00° Roll=15.00°
#   四元数: w=0.9000 x=0.1000 y=0.2000 z=0.3000
#   在线状态: 在线
#   数据有效: 是
#
# ViveTrackerMgr: right
#   位置: (-0.5000, 0.2000, 1.0000) m
#   ...
```

### 示例 2：监控特定 Tracker

```python
mgr = widget.get_tracker_manager()
left = mgr.get_tracker("left")

if left and left.is_online:
    # 获取位置信息
    x, y, z = left.get_position()
    print(f"左手位置: ({x:.2f}, {y:.2f}, {z:.2f})")
    
    # 获取旋转信息
    yaw, pitch, roll = left.get_euler()
    print(f"旋转: Yaw={yaw:.1f}° Pitch={pitch:.1f}° Roll={roll:.1f}°")
```

### 示例 3：检查所有在线 Tracker

```python
mgr = widget.get_tracker_manager()
online = mgr.get_online_trackers()

if len(online) == 2:
    print("✓ 两个 Tracker 都在线")
    for name, tracker in online.items():
        print(f"  {name}: {tracker.get_position()}")
elif len(online) == 1:
    print("⚠ 只有一个 Tracker 在线")
else:
    print("✗ 没有 Tracker 在线")
```

### 示例 4：导出数据

```python
import json

mgr = widget.get_tracker_manager()

# 导出所有 Tracker 数据为 dict
data = {}
for name, tracker in mgr.get_all_trackers().items():
    data[name] = {
        "position": tracker.get_position(),
        "euler": tracker.get_euler(),
        "quat": tracker.get_quat(),
        "online": tracker.is_online,
        "valid": tracker.valid,
    }

# 保存为 JSON
with open("tracker_data.json", "w") as f:
    json.dump(data, f, indent=2)
```

## 性能特性

- **线程安全**：ViveTrackerWidget 的数据更新使用 RLock 保护
- **实时性**：60Hz UI 更新频率，与 ViveTrackerWidget 同步
- **低开销**：仅添加数据结构开销，不影响追踪性能
- **灵活访问**：支持多种方式访问追踪器信息

## 文件位置

| 文件 | 位置 |
|------|------|
| ViveTrackerMgr 定义 | `triad_openvr/tracker_manager.py` |
| 集成到 ViveTrackerWidget | `ui/vive_tracker_widget.py` |
| 测试脚本 | `test_tracker_manager.py` |
| 此文档 | `VIVE_TRACKER_MGR_GUIDE.md` |

## API 总结

### ViveTrackerMgr

```python
class ViveTrackerMgr:
    # 属性
    name: str
    position_x/y/z: float
    euler_yaw/pitch/roll: float
    quat_w/x/y/z: float
    rotation_matrix: np.ndarray
    is_online: bool
    valid: bool
    timestamp: float
    remarks: str
    
    # 方法
    update_position(x, y, z)
    update_euler(yaw, pitch, roll)
    update_quat(w, x, y, z)
    update_rotation_matrix(matrix)
    get_position() -> tuple
    get_euler() -> tuple
    get_quat() -> tuple
    get_rotation_matrix() -> np.ndarray
```

### TrackerManager

```python
class TrackerManager:
    # 方法
    register_tracker(name) -> ViveTrackerMgr
    get_tracker(name) -> Optional[ViveTrackerMgr]
    remove_tracker(name) -> bool
    get_all_trackers() -> Dict[str, ViveTrackerMgr]
    get_online_trackers() -> Dict[str, ViveTrackerMgr]
    clear()
    print_summary()
    
    # 特殊方法
    __len__() -> int
    __contains__(name) -> bool
    __getitem__(name) -> ViveTrackerMgr
```

### ViveTrackerWidget（新增方法）

```python
class ViveTrackerWidget:
    # 获取管理器
    get_tracker_manager() -> TrackerManager
    
    # 获取 Tracker
    get_tracker(name) -> Optional[ViveTrackerMgr]
    get_all_trackers() -> Dict[str, ViveTrackerMgr]
    get_online_trackers() -> Dict[str, ViveTrackerMgr]
    
    # 打印摘要
    print_tracker_summary()
```

## 常见问题

**Q: 如何区分 TrackerManager 和 ViveTrackerWidget 中的数据？**

A: ViveTrackerWidget 的 TrackerManager 是全局的（通过 `get_global_tracker_manager()` 获取），所以在应用程序中访问 `widget.get_tracker_manager()` 和 `get_global_tracker_manager()` 会得到同一个实例。

**Q: 数据更新频率是多少？**

A: ViveTrackerMgr 中的数据在 ViveTrackerWidget 的 `_on_update_timer()` 中更新，频率为 60Hz（与 UI 刷新频率相同）。OpenVR 原始数据采集频率为 60Hz。

**Q: 如何获取历史数据？**

A: `ViveTrackerMgr` 中的数据总是最新的。如果需要历史数据，可以在应用程序中自行记录 `timestamp` 和数据快照。

**Q: 可以添加自定义数据吗？**

A: 可以。`ViveTrackerMgr` 的 `remarks` 字段可用于存储备注。如果需要更多自定义字段，可以继承 `ViveTrackerMgr` 或在应用程序中创建装饰对象。

## 更新日志

- **2026-05-13**: 首次发布
  - 实现 `ViveTrackerMgr` 结构体
  - 实现 `TrackerManager` 管理器
  - 集成到 `ViveTrackerWidget`
  - 添加全局管理器支持
  - 添加完整的测试脚本和文档
