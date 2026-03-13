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
├── motionGloveSDK_example3_3dView.py  # 示例3：3D 实时可视化
│
├── src/                               # SDK 内部实现模块
│   ├── __init__.py
│   ├── motionGloveSDK.py              # SDK 主入口（公共接口）
│   ├── definitions.py                 # 数据结构与枚举定义（GloveFrame、BoneIndex 等）
│   ├── glove_frame_assembler.py       # UDP 分包拼帧逻辑
│   ├── decode_glove_csv.py            # CSV 格式骨骼数据解析
│   ├── euler_to_quat.py               # 欧拉角转四元数工具
│   └── port_occupier.py               # 端口占用诊断工具
│
├── python_draw3d/                     # 3D 渲染辅助模块（基于 VTK）
│   ├── bone_joint_actor.py            # 骨骼关节球体 + 坐标轴 Actor
│   ├── box_actor.py                   # 箱体 Actor
│   ├── camera_control.py              # 摄像机控制（初始化、空格重置视角）
│   ├── draw_lines.py                  # 线段绘制工具
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
├── fonts/
│   └── HarmonyOS_Sans_SC_Regular.ttf  # 中文字体（3D 视图叠加文字使用）
│
├── [Windows]setup_python_libs.cmd     # Windows 一键安装依赖脚本
├── [Linux]setup_python_libs.sh        # Linux 一键安装依赖脚本
├── [Windows]git_pull_latest.cmd       # Windows 拉取最新代码脚本
├── [Linux]git_pull_latest.sh          # Linux 拉取最新代码脚本
├── [Windows]open_in_vscode.bat        # Windows 用 VSCode 打开工程脚本
├── [Linux]open_in_vscode.sh           # Linux 用 VSCode 打开工程脚本
└── pyrightconfig.json                 # Pyright 类型检查配置
```

---

## 安装 Python 依赖

运行时依赖统一安装到工程目录下的 `libs/` 文件夹，不污染系统 Python 环境。

### Windows

```cmd
[Windows]setup_python_libs.cmd
```

### Linux / macOS

```bash
bash [Linux]setup_python_libs.sh
```

脚本分两步执行：

**第一步** — 将运行时依赖安装到 `libs/` 目录：

| 包 | 版本（Windows） | 版本（Linux） | 用途 |
|---|---|---|---|
| vtk | 9.6.0 | 9.6.0 | 3D 渲染（示例3使用） |
| numpy | 2.4.2 | 2.2.6 | 数值计算 |
| matplotlib | 3.10.8 | 3.10.8 | 绘图（依赖项） |
| Pillow | 12.1.1 | 12.1.1 | 图像处理 |
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

将左右手所有骨骼关节的位置和姿态实时渲染为 3D 场景。

- 监听本机 UDP 5001 端口
- 每个骨骼关节显示为彩色小球：右手为青蓝色，左手为橙色
- 每个关节叠加三坐标轴线段，直观表示旋转姿态
- 约 60fps 实时刷新
- 鼠标操作：左键旋转、右键缩放、中键平移、**空格键** 重置视角
- 按 **Enter** 退出

```bash
python motionGloveSDK_example3_3dView.py
```

> 运行此示例需要先安装 VTK：执行 `[Windows]setup_python_libs.cmd` 或 `[Linux]setup_python_libs.sh`。

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
