# MotionGloveSDK Python

MotionGlove 动作手套的 Python SDK，通过 UDP 接收手套骨骼数据，接口与 C++ SDK（`motionGloveSDK.h`）保持一致。

---

## 工程结构

```
MotionGloveSDK_python/
│
├── motionGloveSDK_rawReceiver.py      # 原始 UDP 数据接收验证工具
├── motionGloveSDK_example1.py         # 示例1：帧接收计数
├── motionGloveSDK_example2.py         # 示例2：读取左右手掌欧拉角
├── motionGloveSDK_example3_3dView.py  # 示例3：3D 实时可视化（含 UDP_STREAM / CSV_PLAYBACK 双模式）
├── CSV_PLAYBACK_UserManual.md         # CSV 回放模式最终用户操作说明
│
├── src/                               # SDK 内部实现模块
│   ├── __init__.py
│   ├── motionGloveSDK.py              # SDK 主入口（公共接口）
│   ├── definitions.py                 # 数据结构与枚举定义（GloveFrame、BoneIndex 等）
│   ├── glove_frame_assembler.py       # UDP 分包拼帧逻辑
│   ├── decode_glove_csv.py            # CSV 格式骨骼数据解析
│   ├── csv_frame_reader.py            # CsvFrameReader：预加载 CSV 文件，逐帧提供 GloveFrame
│   ├── xsqeconverter.py               # 欧拉角 ↔ 四元数转换（移植自 Movella xsqeconverter.cpp）
│   └── port_occupier.py               # 端口占用诊断工具
│
├── python_draw3d/                     # 3D 渲染辅助模块（基于 VTK）
│   ├── bone_joint_actor.py            # 骨骼关节球体 + 坐标轴 Actor（支持运行时修改半径/颜色/轴长）
│   ├── bone_link_actor.py             # 骨骼连线 Actor（支持运行时修改粗细/颜色）
│   ├── box_actor.py                   # 箱体 Actor
│   ├── camera_control.py              # 摄像机控制（初始化、空格重置视角）
│   ├── draw_config_io.py              # DrawConfig dataclass + JSON 配置读写
│   ├── draw_lines.py                  # 线段绘制工具
│   ├── fps_counter.py                 # FpsCounter：整秒桶计数帧率统计
│   ├── ground_plane.py                # 地平面网格 Actor（灰色，5 cm 间距）
│   ├── overlay_text.py                # 屏幕叠加文字
│   ├── print_help_message.py          # 打印帮助信息
│   └── vtk_axes.py                    # 三坐标轴显示
│
├── libs/                              # 第三方运行时依赖（pip --target 安装到此目录）
│   ├── vtk/                           # VTK 3D 渲染库
│   ├── PIL/                           # Pillow 图像库
│   ├── pyparsing/                     # pyparsing 解析库
│   └── six.py                         # six 兼容库
│
├── triad_openvr/                      # OpenVR 追踪器集成模块（SteamVR 手部追踪支持）
│   ├── triad_openvr.py                # OpenVR 设备发现与控制主类
│   ├── hand_tracker_monitor.py        # 手部追踪器实时监控工具（显示位置/姿态）
│   ├── hand_tracker_config.json       # 手部追踪器序列号配置文件
│   ├── config.json                    # OpenVR 设备全局配置文件（HMD/控制器/追踪器）
│   ├── controller_test.py             # 控制器功能测试脚本
│   ├── tracker_test.py                # 追踪器功能测试脚本
│   ├── udp_emitter.py                 # UDP 数据广播工具
│   └── udp_receiver.cs                # C# 示例：UDP 数据接收程序
│
├── fonts/
│   └── HarmonyOS_Sans_SC_Regular.ttf  # 中文字体（3D 视图叠加文字使用）
│
├── ui/                                # Qt Designer UI 文件与控制器
│   ├── left_panel.ui                  # 左侧网络信息面板布局（Qt Designer 可编辑）
│   ├── left_panel_widget.py           # LeftPanelWidget 控制器（QUiLoader 运行时加载）
│   ├── csv_import_widget.py           # CsvImportWidget：CSV 回放模式左侧面板
│   ├── draw_config_widget.py          # DrawConfigWidget：右侧绘图配置面板（Slider + 取色板）
│   └── oss_licenses_dialog.py         # 开源声明对话框
│
├── scripts/                           # 实用脚本
│   ├── [Windows]setup_python_libs.cmd # Windows 一键安装依赖脚本
│   ├── [Linux]setup_python_libs.sh    # Linux 一键安装依赖脚本
│   ├── [Windows]build_dist.cmd        # Windows PyInstaller 打包脚本（--console 参数可选）
│   ├── [Linux]build_dist.sh           # Linux PyInstaller 打包脚本（--console 参数可选）
│   ├── [Windows]git_pull_latest.cmd   # Windows 拉取最新代码脚本
│   ├── [Linux]git_pull_latest.sh      # Linux 拉取最新代码脚本
│   ├── [Windows]open_in_vscode.bat    # Windows 用 VSCode 打开工程脚本
│   └── [Linux]open_in_vscode.sh       # Linux 用 VSCode 打开工程脚本
│
└── pyrightconfig.json                 # Pyright 类型检查配置
```

---

## Python 版本要求

**最低要求：Python 3.10**

部分依赖（numpy 2.x、contourpy 1.3.x、kiwisolver 1.4.x）在 Linux 上需要 Python 3.10+；Windows 上建议使用 Python 3.10 或更高版本。

---

## 系统需求

### 硬件要求

运行本程序**需要至少 8 个 CPU 核心和 12 GB 内存**，特别是在需要同时运行 SteamVR 的场景下。这适用于：

- **真机部署**（Windows 或 Linux 物理机）
- **虚拟机运行**（VMware、VirtualBox、Hyper-V 等）

**最低配置：**

| 配置项 | 要求 |
|---|---|
| CPU 核心数 | ≥ 8 核 |
| 内存 | ≥ 12 GB |
| 存储 | ≥ 500 MB（用于依赖库和数据文件） |

**配置不足的影响：**

如果系统配置低于上述要求，特别是在同时运行 SteamVR + 本应用的场景下，会导致：
- 3D 可视化界面帧率过低（< 30 FPS）
- 明显的界面卡顿和响应延迟
- 实时数据处理延迟
- 系统整体运行不稳定

**虚拟机特别说明：**

如果在虚拟机中运行，建议：
- 为虚拟机分配 ≥ 8 个虚拟 CPU（映射到物理核心）
- 分配 ≥ 12 GB 虚拟内存
- 启用 3D 加速（如可用）
- 避免超分配资源（过度分配虚拟 CPU 或内存会导致性能下降）

---

## 安装 Python 依赖

运行时依赖统一安装到工程目录下的 `libs/` 文件夹，不污染系统 Python 环境。

### Windows

```cmd
scripts\[Windows]setup_python_libs.cmd
```

### Linux / macOS

```bash
bash scripts/[Linux]setup_python_libs.sh
```

脚本分两步执行：

**第一步** — 将运行时依赖安装到 `libs/` 目录：

| 包 | 版本（Windows） | 版本（Linux） | 用途 |
|---|---|---|---|
| vtk | 9.6.0 | 9.6.0 | 3D 渲染（示例3使用） |
| numpy | 2.4.2 | 2.2.6 | 数值计算 |
| matplotlib | 3.10.8 | 3.10.8 | 绘图（依赖项） |
| Pillow | 12.1.1 | 12.1.1 | 图像处理 |
| pyside6 | 6.5.3 | 6.5.3 | Qt6 GUI 框架（示例3主窗口） |
| pyparsing | 3.3.2 | 3.3.2 | 解析工具 |
| python-dateutil | 2.9.0.post0 | 2.9.0.post0 | 日期工具 |
| packaging | 26.0 | 26.0 | 包管理工具 |
| fonttools | 4.61.1 | 4.62.0 | 字体工具 |
| contourpy | 1.3.3 | 1.3.2 | 等高线（matplotlib 依赖） |
| cycler | 0.12.1 | 0.12.1 | 样式循环（matplotlib 依赖） |
| kiwisolver | 1.4.9 | 1.4.9 | 约束求解（matplotlib 依赖） |
| six | 1.17.0 | 1.17.0 | Python 2/3 兼容层 |

**第二步** — 将开发工具安装到系统 Python：

| 包 | 版本 | 用途 |
|---|---|---|
| pyinstaller | 6.19.0 | 打包为可执行文件 |
| pybind11 | 2.13.6 | Python/C++ 混合编译 |

> **Linux 注意：** numpy 2.4.x、contourpy 1.3.3+、kiwisolver 1.5.0+ 需要 Python 3.11+，Linux 脚本使用了兼容 Python 3.10 的版本。

---

## 快速开始

### 前提条件

1. 打开 MotionGlove 软件，确保手套连接正常
2. 在软件菜单栏 **设置 → 选项 → 插件 → 数据转发** 中确认已添加转发地址 `127.0.0.1:5001`（软件默认已添加）

### 最简使用

```python
from src import motionGloveSDK

motionGloveSDK.MotionGloveSDK_ListenUDPPort(5001)

while True:
    if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending("Glove1"):
        frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame("Glove1")
        motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending("Glove1")
        # 处理 frame ...
```

---

## SDK 公共接口

| 接口 | 说明 |
|---|---|
| `MotionGloveSDK_getVersion()` | 返回 SDK 版本号（32 位整数） |
| `MotionGloveSDK_ListenUDPPort(nPort)` | 绑定本机 UDP 端口并启动后台接收线程，返回 0 成功 / -1 失败 |
| `MotionGloveSDK_CloseUDPPort()` | 关闭 UDP 连接并等待后台线程退出 |
| `MotionGloveSDK_isGloveNewFramePending(actorName)` | 查询指定数据流是否有新帧到达 |
| `MotionGloveSDK_resetGloveNewFramePending(actorName)` | 清除指定数据流的新帧标志 |
| `MotionGloveSDK_GetGloveSkeletonsFrame(actorName)` | 获取最新一帧 `GloveFrame` 骨骼数据 |
| `MotionGloveSDK_GetLastRemoteAddr()` | 返回最近一次收到 UDP 数据包的发送方 `(ip, port)`，未收到数据时返回 `None` |
| `MotionGloveSDK_GetActorNames()` | 返回当前已发现的所有套装名称列表（如 `["Glove1", "Glove2"]`） |

---

## 示例文件说明

### `motionGloveSDK_example1.py` — 帧接收计数

验证 SDK 能否正常接收数据。

- 监听本机 UDP 5001 端口
- 每收到一帧打印帧序号（`[N] New frame received`）
- 正常情况下每秒打印约 60 条记录
- 按 **Enter** 退出

```bash
python motionGloveSDK_example1.py
```

---

### `motionGloveSDK_example2.py` — 读取手掌欧拉角

实时打印左右手掌的三轴欧拉角（Roll/Pitch/Yaw，单位：度）。

- 监听本机 UDP 5001 端口
- 每帧打印左手掌和右手掌的欧拉角
- 按 **Enter** 退出

```bash
python motionGloveSDK_example2.py
```

输出示例：
```
Left Palm Euler Angle: [12.34, -5.67, 90.12]   Right Palm Euler Angle: [-3.21, 8.90, -45.67]
```

---

### `motionGloveSDK_example3_3dView.py` — 3D 实时可视化

将左右手所有骨骼关节的位置和姿态渲染为 3D 场景，基于 **PySide6 + VTK** 构建。支持两种运行模式，通过脚本顶部的 `APP_MODE` 常量切换：

```python
APP_MODE = AppMode.UDP_STREAM    # 实时接收手套数据（默认）
APP_MODE = AppMode.CSV_PLAYBACK  # 回放已保存的 CSV 文件
```

```bash
python motionGloveSDK_example3_3dView.py
```

> 运行此示例需要先安装依赖：执行 `[Windows]setup_python_libs.cmd` 或 `[Linux]setup_python_libs.sh`（包含 VTK 和 PySide6）。

---

#### 通用界面

- 每个骨骼关节显示为彩色小球：右手青蓝色，左手橙色；父子关节间绘制骨骼连线；指尖末梢节点（`*3End`）以真实坐标位置渲染关节球，不显示局部坐标轴
- 每个关节叠加三坐标轴线段，直观表示全局旋转姿态
- 底部状态栏显示加载状态、丢帧警告、播放完毕等提示

**鼠标操作：**

| 操作 | 功能 |
|---|---|
| 左键拖拽 | 旋转场景 |
| 右键拖拽 | 缩放场景 |
| 中键拖拽 | 平移场景 |
| 空格键 | 重置视角 |
| 右键短按 | 弹出上下文菜单 |

**右键上下文菜单：**
- 显示 / 隐藏 世界坐标原点坐标轴
- 显示 / 隐藏 地平面网格（灰色，5 cm 间距，默认显示）
- 重置视角

**菜单栏：**
- 文件 → 退出
- 窗口 → 切换左侧面板 / 右侧配置面板的显示
- 帮助 → 关于 Qt / 开源声明

**右侧绘图配置面板（DrawConfigWidget）：**

| 控件 | 说明 |
|---|---|
| 关节球半径 Slider | 调整所有关节球大小（1–10 mm） |
| 关节球颜色 | 取色板，统一修改所有关节球颜色 |
| 骨骼连线粗细 Slider | 调整连线和末梢骨骼粗细（1–30 px，默认 10） |
| 骨骼连线颜色 | 取色板，统一修改所有骨骼连线颜色 |
| 坐标轴长度 Slider | 调整关节局部坐标轴线段长度（1–30 mm） |
| 导出配置 | 将当前参数保存为 JSON 文件 |
| 加载配置 | 从 JSON 文件恢复参数 |

---

#### 模式一：UDP_STREAM — 实时 UDP 数据流

**前提条件：**
1. 打开 MotionGlove 软件，确保手套连接正常
2. 菜单栏 **设置 → 选项 → 插件 → 数据转发** 中确认已添加转发地址 `127.0.0.1:5001`

**左侧面板（LeftPanelWidget）功能和操作流程：**

| 控件 / 字段 | 说明 |
|---|---|
| 开始接收 按钮 | 绑定 UDP 端口 5001，启动后台接收线程；若端口被占用则以红色显示占用程序名称和 PID |
| 停止接收 按钮 | 释放 UDP 端口，停止接收 |
| 套装名称 | 当前收到数据的套装标识（如 `Glove1`） |
| 来源 IP / 端口 | 最近一次 UDP 数据包的发送方地址 |
| 帧序号 | 最近消费的帧序号 |
| 总帧数 | 本次接收会话的累计帧数 |
| 帧率 | 实时接收帧率（每秒刷新一次） |

**操作流程：**
1. 运行脚本，点击 **开始接收**
2. 启动 MotionGlove 软件并连接手套，3D 场景自动开始实时渲染
3. 若端口 5001 被占用，面板以红色提示占用程序；关闭占用程序后重新点击 **开始接收**
4. 点击 **停止接收** 可暂停数据接收，场景保持最后一帧静止

---

#### 模式二：CSV_PLAYBACK — CSV 文件回放

MotionGlove 软件可将录制的动作导出为 CSV 文件。此模式加载该文件并按选定帧率逐帧回放，无需连接手套硬件。

**左侧面板（CsvImportWidget）功能和操作流程：**

| 控件 / 字段 | 说明 |
|---|---|
| 选择文件… 按钮 | 打开文件对话框，选择 MotionGlove 导出的 `.csv` 文件；选中后立即预加载全部帧到内存并显示第一帧 |
| 文件路径框 | 显示当前已加载文件的完整路径（只读） |
| 帧率下拉框 | 选择回放帧率：10 / 24 / 30 / 60 Hz（默认 60 Hz）；播放中切换立即生效 |
| 帧号标签 | 显示当前帧号和总帧数（格式：`当前帧/总帧数 (百分比%)`） |
| 进度条 | 拖动可跳转到任意位置；按下时暂停推进，松开时跳转到目标帧 |
| 开始播放 / 暂停播放 按钮 | 切换播放和暂停状态；播放到末帧后自动停止 |
| 重置 按钮 | 停止播放并回到第一帧 |

**操作流程：**
1. 将 `APP_MODE` 改为 `AppMode.CSV_PLAYBACK` 后运行脚本
2. 点击 **选择文件…**，选择 MotionGlove 导出的 CSV 文件；加载完成后状态栏显示总帧数，3D 场景显示第一帧
3. 在帧率下拉框中选择所需回放速度
4. 点击 **开始播放** 开始逐帧回放；可随时点击 **暂停播放** 暂停
5. 拖动进度条可跳转到任意帧，松手后场景立即更新到目标帧，再次点击 **开始播放** 从该帧继续
6. 播放到末帧后自动停止，点击 **重置** 可回到第一帧重新播放

---

### `motionGloveSDK_rawReceiver.py` — 原始 UDP 数据接收验证工具

底层调试工具，用于验证能否收到来自 MotionGlove 软件的原始 UDP 数据，并打印解析后的骨骼帧信息。

- 监听指定 UDP 端口（默认 5001）
- 打印每个完整帧的 actor 名称、帧号及右手掌骨骼数据
- 可选 `--print-raw` 参数打印每个原始 UDP 包的详细信息
- 程序退出时显示收包统计（UDP 包数 / 完整帧数）
- 按 **Enter** 或 **Ctrl+C** 退出

```bash
# 默认端口 5001，只打印完整帧
python motionGloveSDK_rawReceiver.py

# 指定端口
python motionGloveSDK_rawReceiver.py --port 5002

# 同时打印每个原始 UDP 包
python motionGloveSDK_rawReceiver.py --print-raw

# 组合使用
python motionGloveSDK_rawReceiver.py --port 5001 --print-raw
```

---

## Triad OpenVR 模块 — SteamVR 手部追踪支持

`triad_openvr/` 目录包含 OpenVR（SteamVR）集成工具，用于与 HTC Vive 等 OpenVR 设备（如手部追踪器）交互。

### 模块文件说明

| 文件 | 功能说明 |
|---|---|
| `triad_openvr.py` | OpenVR 核心类：设备发现、序列号映射、姿态读取 |
| `hand_tracker_monitor.py` | 手部追踪器实时监控工具 |
| `hand_tracker_config.json` | 手部追踪器配置（序列号 → 设备映射） |
| `config.json` | OpenVR 全局设备配置（HMD/控制器/追踪器） |
| `controller_test.py` | 控制器测试脚本 |
| `tracker_test.py` | 追踪器测试脚本 |
| `udp_emitter.py` | UDP 广播工具 |
| `udp_receiver.cs` | C# 示例：UDP 接收程序 |

### 快速开始

#### 1. 配置文件：`hand_tracker_config.json`

用于将追踪器序列号映射到逻辑名称。格式如下：

```json
{
  "LeftHandTracker": {
    "SerialNumber": "LHR-29E6074C"
  },
  "RightHandTracker": {
    "SerialNumber": "LHR-D5301C8B"
  }
}
```

**获取序列号的方法：**

1. 启动 SteamVR 并连接手部追踪器
2. 运行 `hand_tracker_monitor.py`，程序会自动列出所有发现的设备及其序列号：

   ```
   Serial to Device Mapping:
     LHR-29E6074C -> tracker_1
     LHR-D5301C8B -> tracker_2
   ```

3. 将这些序列号复制到 `hand_tracker_config.json` 中对应的字段

#### 2. 手部追踪器监控工具：`hand_tracker_monitor.py`

实时显示配置文件中的所有手部追踪器的位置和旋转数据。

**使用方法：**

```bash
# 默认 60 Hz 采样率
python triad_openvr/hand_tracker_monitor.py

# 指定采样频率（例如 30 Hz）
python triad_openvr/hand_tracker_monitor.py 30
```

**功能：**

- 自动初始化 OpenVR 系统并发现设备
- 根据 `hand_tracker_config.json` 匹配追踪器
- 实时打印每个追踪器的位置（X/Y/Z，单位：米）和旋转欧拉角（Yaw/Pitch/Roll，单位：度）
- **支持三种退出方式：**
  - **Ctrl+C** — 中断信号
  - **ESC** — 按下 ESC 键
  - **Q** — 按下 Q 或 q 键

**输出示例：**

```
===============================================================================
Hand Tracker Position and Rotation Data
Press Ctrl+C, ESC, or Q to exit
===============================================================================

[14:32:45.123]

LeftHandTracker:
  Position:  X=   0.1234m  Y=   1.5678m  Z=  -0.8901m
  Rotation:  Yaw= 45.23°  Pitch=-10.56°  Roll= 123.45°

RightHandTracker:
  Position:  X=  -0.0543m  Y=   1.6234m  Z=  -0.7654m
  Rotation:  Yaw=-30.12°  Pitch=  5.34°  Roll= -98.76°
```

### 核心类：`triad_openvr` 类

```python
import triad_openvr

# 初始化 OpenVR 系统
v = triad_openvr.triad_openvr()

# 列出所有发现的设备
print("Available devices:")
v.print_discovered_objects()

# 获取指定设备的姿态数据
device = v.devices["tracker_1"]

# 欧拉角 (x, y, z, yaw, pitch, roll)
pose_euler = device.get_pose_euler()
if pose_euler:
    x, y, z, yaw, pitch, roll = pose_euler
    print(f"Position: {x}, {y}, {z}")
    print(f"Rotation (Euler): {yaw}, {pitch}, {roll}")

# 四元数 (x, y, z, w) + 位置
pose_quat = device.get_pose_quaternion()
if pose_quat:
    x_pos, y_pos, z_pos, x_quat, y_quat, z_quat, w_quat = pose_quat
    print(f"Position: {x_pos}, {y_pos}, {z_pos}")
    print(f"Quaternion: {x_quat}, {y_quat}, {z_quat}, {w_quat}")

# 获取设备序列号
serial = device.get_serial()
if isinstance(serial, bytes):
    serial = serial.decode('utf-8')
print(f"Serial Number: {serial}")
```

### 集成 MotionGlove 和 OpenVR 数据

可以同时使用 MotionGlove SDK 接收手套骨骼数据，并通过 Triad OpenVR 获取外部追踪器位置：

```python
from src import motionGloveSDK
import triad_openvr

# 初始化 MotionGlove SDK
motionGloveSDK.MotionGloveSDK_ListenUDPPort(5001)

# 初始化 OpenVR
v = triad_openvr.triad_openvr()

while True:
    # 获取 MotionGlove 数据
    if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending("Glove1"):
        frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame("Glove1")
        motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending("Glove1")
        # 处理手套骨骼数据...
    
    # 获取 OpenVR 追踪器数据
    tracker = v.devices.get("tracker_1")
    if tracker:
        pose = tracker.get_pose_euler()
        if pose:
            x, y, z, yaw, pitch, roll = pose
            # 处理追踪器位置和旋转...
```

---

## CSV → BVH 转换

`src/csv_to_bvh.py` 提供将 MotionGlove 导出 CSV 文件转换为标准 BVH 动捕文件的功能，可在 3D 查看器的 CSV 回放模式中通过 **"导出 BVH…"** 按钮一键调用，也可以作为模块在代码中直接使用。

### 使用方式

**通过 3D 查看器界面：**

1. 启动 3D 查看器并切换到 CSV 回放模式（启动时选择 **CSV 文件回放**）
2. 点击 **"选择文件…"** 加载 CSV 文件
3. 点击 **"导出 BVH…"**，转换完成后弹窗提示保存路径
4. BVH 文件自动保存在与 CSV 文件相同的目录下，文件名相同，扩展名改为 `.bvh`

**通过代码调用：**

```python
from src.csv_to_bvh import convert_csv_to_bvh

# 输出路径默认与 CSV 同目录同名，扩展名改为 .bvh
out_path = convert_csv_to_bvh("path/to/recording.csv")

# 也可以指定输出路径
out_path = convert_csv_to_bvh("path/to/recording.csv", "path/to/output.bvh")
```

### 转换流程

```
CSV 文件
│
├─ 第 1 行（列名表头）         跳过
│
├─ 第 1 帧（T-pose）           用于计算 BVH HIERARCHY OFFSET
│   每根骨骼：pos(全局绝对, 米) + euler(ZXY, 度)
│   → 父子相对位移 × 100 → OFFSET(厘米)
│
├─ 前 10 帧时间戳              推算平均帧间隔 → BVH Frame Time
│
└─ 全部帧（含第 1 帧）
    每帧每骨骼：
      位置：(当前骨骼全局坐标 − 父骨骼全局坐标) × 100  [厘米]
      旋转：ZXY 欧拉 → 四元数 → ZYX 欧拉               [度]
    → 写入 BVH MOTION 段，每帧一行，258 个数值
         (43 关节 × 6 通道，含合成 ROOT)
```

### 坐标系与单位

| 项目 | CSV | BVH |
|---|---|---|
| 位置单位 | 米 | 厘米（× 100） |
| 位置坐标性质 | 全局绝对坐标 | 父子相对偏移 |
| 旋转顺序 | ZXY（内旋） | ZYX（外旋，通道顺序 Zrot Yrot Xrot） |
| 坐标系朝向 | OpenGL 标准（Y 轴朝上，指尖朝 Y+） | 同左，无需轴变换 |

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
    └── （同右手，对称结构）
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

### 注意事项

**CSV 文件第一帧需为 T-pose：**
BVH 文件头（`HIERARCHY` 段）的 `OFFSET` 值取自 CSV 第一帧的骨骼位置，作为静止姿态的骨骼参考偏移。如果第一帧不是 T-pose（所有关节旋转角为零的标准站姿），骨骼的静止形态会发生偏移，但不影响动画数据的正确性（因为每帧都有完整的 position channels，OFFSET 在播放时被覆盖）。

**帧率自动检测：**
转换器从 CSV 行头的时间戳字段（`time YYYY-MM-DD HH:MM:SS.mmm`）自动推算帧率，取前 10 帧时间戳的平均间隔作为 BVH 的 `Frame Time`。若 CSV 中无时间戳或无法解析，默认使用 60 Hz（`Frame Time: 0.016667`）。

**第三方软件兼容性：**
生成的 BVH 文件符合标准 BVH 格式（BioVision Hierarchy），可在 BVHacker、Blender、MotionBuilder、Unity、Unreal Engine 等软件中打开。注意 BVH 规范要求 `MOTION` 段前不能有空行，本转换器已处理此细节。

BVH在线查看器：

https://renkunzhao.github.io/motion_viewer/

https://theorangeduck.com/media/uploads/BVHView/bvhview.html

---

## 已知问题和故障排查

### SteamVR 虚拟机睡眠唤醒问题

**问题描述：**
在 Ubuntu 虚拟机中运行 SteamVR 时，如果虚拟机进入暂停/睡眠状态后被唤醒，SteamVR 将无法重新连接 ViveTracker 设备。症状表现为：
- 手部追踪器显示已连接，但无法接收到位置和旋转数据
- `hand_tracker_monitor.py` 或 3D 查看器中追踪器数据为零

**解决方案：**
重启 SteamVR 进程即可恢复连接：
```bash
# Linux / macOS：关闭 SteamVR
killall vrserver

# 或者进入 SteamVR 设置菜单（从 SteamVR 桌面应用）进行重启

# 之后重新启动追踪应用即可正常使用
```

**根本原因：**
虚拟机睡眠时，USB 设备和 SteamVR 守护进程的状态变得不同步，SteamVR 无法自动恢复与已连接设备的通信状态。

**建议：**
- 在虚拟机设置中禁用自动睡眠/暂停功能
- 或者在使用前手动检查 SteamVR 和追踪器是否正常连接

