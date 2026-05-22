# CSV 文件加载、回放与转换指南

本文档介绍如何在 MotionGloveSDK 中加载、回放和转换 MotionGlove 导出的 CSV 文件。

---

## CSV 回放模式（CSV_PLAYBACK）

MotionGlove 软件可将录制的动作导出为 CSV 文件。3D 查看器的 CSV 回放模式加载该文件并按选定帧率逐帧回放，无需连接手套硬件。

### 启用 CSV 回放模式

编辑 `motionGloveSDK_example3_3dView.py`，将脚本顶部的 `APP_MODE` 常量改为：

```python
APP_MODE = AppMode.CSV_PLAYBACK  # 回放已保存的 CSV 文件
```

然后运行脚本：

```bash
python motionGloveSDK_example3_3dView.py
```

### CSV 回放界面说明

#### 左侧面板（CsvImportWidget）功能

| 控件 / 字段 | 说明 |
|---|---|
| **选择文件…** 按钮 | 打开文件对话框，选择 MotionGlove 导出的 `.csv` 文件；选中后立即预加载全部帧到内存并显示第一帧 |
| **文件路径框** | 显示当前已加载文件的完整路径（只读） |
| **帧率下拉框** | 选择回放帧率：10 / 24 / 30 / 60 Hz（默认 60 Hz）；播放中切换立即生效 |
| **帧号标签** | 显示当前帧号和总帧数（格式：`当前帧/总帧数 (百分比%)`） |
| **进度条** | 拖动可跳转到任意位置；按下时暂停推进，松开时跳转到目标帧 |
| **开始播放 / 暂停播放** 按钮 | 切换播放和暂停状态；播放到末帧后自动停止 |
| **重置** 按钮 | 停止播放并回到第一帧 |
| **导出 BVH…** 按钮 | 将当前加载的 CSV 文件转换为 BVH 格式，转换完成后弹窗提示保存路径 |

#### CSV 回放操作流程

1. **加载文件：** 点击 **选择文件…**，选择 MotionGlove 导出的 CSV 文件
   - 加载完成后状态栏显示总帧数
   - 3D 场景显示第一帧

2. **配置回放参数：** 在帧率下拉框中选择所需回放速度（10 / 24 / 30 / 60 Hz）

3. **开始回放：** 点击 **开始播放** 开始逐帧回放
   - 可随时点击 **暂停播放** 暂停

4. **跳转帧数：** 拖动进度条可跳转到任意帧
   - 按下时暂停推进
   - 松开时跳转到目标帧
   - 场景立即更新到目标帧
   - 再次点击 **开始播放** 从该帧继续

5. **播放结束：** 播放到末帧后自动停止
   - 点击 **重置** 可回到第一帧重新播放

### 代码集成（CsvFrameReader）

如需在代码中直接加载和读取 CSV 文件，可使用 `src/csv_frame_reader.py` 中的 `CsvFrameReader` 类：

```python
from src.csv_frame_reader import CsvFrameReader

# 加载 CSV 文件
reader = CsvFrameReader("path/to/recording.csv")

# 逐帧读取
while True:
    frame = reader.next_frame()
    if frame is None:
        break
    # 处理 GloveFrame 对象...
    print(f"Frame {frame.fn}: {frame.skeletons}")
```

**CsvFrameReader 接口：**

| 方法 | 返回值 | 说明 |
|---|---|---|
| `CsvFrameReader(csv_path)` | CsvFrameReader 实例 | 初始化，立即加载整个 CSV 文件到内存 |
| `next_frame()` | GloveFrame 或 None | 返回下一帧；到末尾时返回 None |
| `reset()` | 无 | 重置帧指针到第一帧 |
| `frame_count()` | int | 返回总帧数 |

---

## CSV → BVH 转换

### 使用方式

#### 通过 3D 查看器界面（推荐）

1. 启动 3D 查看器并切换到 CSV 回放模式
2. 点击 **选择文件…** 加载 CSV 文件
3. 点击 **导出 BVH…**，转换完成后弹窗提示保存路径
4. BVH 文件自动保存在与 CSV 文件相同的目录下，文件名相同，扩展名改为 `.bvh`

#### 通过代码调用

```python
from src.csv_to_bvh import convert_csv_to_bvh

# 输出路径默认与 CSV 同目录同名，扩展名改为 .bvh
out_path = convert_csv_to_bvh("path/to/recording.csv")
print(f"BVH file saved to: {out_path}")

# 也可以指定输出路径
out_path = convert_csv_to_bvh("path/to/recording.csv", "path/to/output.bvh")
```

### 转换流程说明

```
CSV 文件
│
├─ 第 1 行（列名表头）         → 跳过
│
├─ 第 1 帧（T-pose）           → 用于计算 BVH HIERARCHY OFFSET
│   每根骨骼：pos(全局绝对, 米) + euler(ZXY, 度)
│   → 父子相对位移 × 100 → OFFSET(厘米)
│
├─ 前 10 帧时间戳              → 推算平均帧间隔 → BVH Frame Time
│
└─ 全部帧（含第 1 帧）
    每帧每骨骼：
      位置：(当前骨骼全局坐标 − 父骨骼全局坐标) × 100  [厘米]
      旋转：ZXY 欧拉 → 四元数 → ZYX 欧拉               [度]
    → 写入 BVH MOTION 段，每帧一行，258 个数值
         (43 关节 × 6 通道，含合成 ROOT)
```

### 坐标系与单位转换

| 项目 | CSV | BVH |
|---|---|---|
| **位置单位** | 米（m） | 厘米（cm，× 100） |
| **位置坐标性质** | 全局绝对坐标 | 父子相对偏移 |
| **旋转顺序** | ZXY（内旋） | ZYX（外旋，通道顺序 Zrot Yrot Xrot） |
| **坐标系朝向** | OpenGL 标准（Y 轴朝上，指尖朝 Y+） | 同左，无需轴变换 |

### 骨骼层级结构

BVH 文件包含 **43 个关节**，骨骼结构如下：

```
ROOT ROOT               ← 合成根节点，位置/旋转始终为零
├── RightHand
│   ├── RightHandThumb1 → Thumb2 → Thumb3 → Thumb4
│   ├── RightHandIndex1 → Index2 → Index3 → Index4
│   ├── RightHandMiddle1 → Middle2 → Middle3 → Middle4
│   ├── RightHandRing1  → Ring2  → Ring3  → Ring4
│   └── RightHandPinky1 → Pinky2 → Pinky3 → Pinky4
└── LeftHand
    ├── LeftHandThumb1 → Thumb2 → Thumb3 → Thumb4
    ├── LeftHandIndex1 → Index2 → Index3 → Index4
    ├── LeftHandMiddle1 → Middle2 → Middle3 → Middle4
    ├── LeftHandRing1  → Ring2  → Ring3  → Ring4
    └── LeftHandPinky1 → Pinky2 → Pinky3 → Pinky4
```

CSV 中的末端关节命名（`*3End`）在 BVH 中重命名为 `*4`：

| CSV 骨骼名 | BVH 关节名 |
|---|---|
| `RightHandThumb3End` | `RightHandThumb4` |
| `RightHandIndex3End` | `RightHandIndex4` |
| `RightHandMiddle3End` | `RightHandMiddle4` |
| `RightHandRing3End` | `RightHandRing4` |
| `RightHandPinky3End` | `RightHandPinky4` |
| `LeftHand*3End`（同上）| `LeftHand*4` |

每个关节均有 **6 通道**（`Xposition Yposition Zposition Zrotation Yrotation Xrotation`），包括末端的 `*4` 节点（在链末附加无通道的 `End Site`）。

### 重要注意事项

#### CSV 文件第一帧需为 T-pose

BVH 文件头（`HIERARCHY` 段）的 `OFFSET` 值取自 CSV 第一帧的骨骼位置，作为静止姿态的骨骼参考偏移。

- **如果第一帧不是 T-pose：** 骨骼的静止形态会发生偏移
- **对动画数据的影响：** 不影响动画数据的正确性（因为每帧都有完整的 position channels，OFFSET 在播放时被覆盖）

#### 帧率自动检测

转换器从 CSV 行头的时间戳字段（`time YYYY-MM-DD HH:MM:SS.mmm`）自动推算帧率，取前 10 帧时间戳的平均间隔作为 BVH 的 `Frame Time`。

- **若 CSV 中无时间戳或无法解析：** 默认使用 60 Hz（`Frame Time: 0.016667`）

#### 第三方软件兼容性

生成的 BVH 文件符合标准 BVH 格式（BioVision Hierarchy），可在以下软件中打开：

- **BVHacker** — 专用 BVH 编辑工具
- **Blender** — 3D 建模与动画软件
- **MotionBuilder** — 专业动捕处理工具
- **Unity** — 游戏引擎
- **Unreal Engine** — 游戏引擎

> **注意：** BVH 规范要求 `MOTION` 段前不能有空行，本转换器已正确处理此细节。

#### 在线 BVH 查看器

可使用以下在线工具快速预览转换后的 BVH 文件：

- [Motion Viewer](https://renkunzhao.github.io/motion_viewer/)
- [BVHView](https://theorangeduck.com/media/uploads/BVHView/bvhview.html)

---

## CSV 文件格式说明

### CSV 列结构

MotionGlove 导出的 CSV 文件包含以下列：

| 列索引 | 列名 | 说明 |
|---|---|---|
| 0 | `time` | 时间戳（格式：`YYYY-MM-DD HH:MM:SS.mmm`） |
| 1 | `actor` | 套装标识（如 `Glove1`） |
| 2–129 | 骨骼数据 | 32 根骨骼（左手 16 根 + 右手 16 根）各 4 列：`<bone>_x`, `<bone>_y`, `<bone>_z`, `<bone>_euler` |
|  | | 共 128 列 (32 × 4) |
| 130 | （可选附加列） | 其他数据 |

### 骨骼名称映射

| 索引 | 骨骼名 | 分类 |
|---|---|---|
| 0 | `RightHand` | 右手根 |
| 1–4 | `RightHandThumb1/2/3/3End` | 右手拇指 |
| 5–8 | `RightHandIndex1/2/3/3End` | 右手食指 |
| 9–12 | `RightHandMiddle1/2/3/3End` | 右手中指 |
| 13–16 | `RightHandRing1/2/3/3End` | 右手无名指 |
| 17–20 | `RightHandPinky1/2/3/3End` | 右手小指 |
| 21 | `LeftHand` | 左手根 |
| 22–25 | `LeftHandThumb1/2/3/3End` | 左手拇指 |
| 26–29 | `LeftHandIndex1/2/3/3End` | 左手食指 |
| 30–33 | `LeftHandMiddle1/2/3/3End` | 左手中指 |
| 34–37 | `LeftHandRing1/2/3/3End` | 左手无名指 |
| 38–41 | `LeftHandPinky1/2/3/3End` | 左手小指 |

---

## 常见问题

**Q: 加载 CSV 文件时内存占用过高？**

A: CSV 回放模式在加载时会将全部帧预加载到内存。对于大型文件（例如 10 分钟的录制，帧率 60Hz），可能占用 500MB~1GB 内存。可通过以下方式缓解：
- 在回放前关闭其他应用
- 分割 CSV 文件为多个较小的片段后再加载

**Q: 转换后的 BVH 文件在某些软件中显示不正确？**

A: 可能的原因：
- 第一帧不是 T-pose — 调整 CSV 第一帧使所有关节旋转为零
- 坐标系差异 — 在导入软件中切换坐标轴映射或应用变换
- 单位差异 — 确认软件的默认单位（BVH 使用厘米）

**Q: CSV 中缺少帧率信息如何处理？**

A: 转换器会自动推算：取前 10 帧的时间戳平均间隔；若无法解析则默认 60Hz（Frame Time: 0.016667）。

---

## 相关文件

- `src/csv_frame_reader.py` — CSV 文件加载器（CsvFrameReader 类）
- `src/csv_to_bvh.py` — CSV → BVH 转换模块
- `src/decode_glove_csv.py` — CSV 格式解析模块
- `CSV_PLAYBACK_UserManual.md` — CSV 回放最终用户操作说明
- `motionGloveSDK_example3_3dView.py` — 3D 查看器主程序（包含 CSV 回放模式）
