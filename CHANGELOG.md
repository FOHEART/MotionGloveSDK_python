# Changelog

## [Unreleased]

### Added
- **右侧绘图配置面板**（`ui/draw_config_widget.py`）：新增 `DrawConfigWidget`，固定宽度 220px，提供三组配置：
  - 关节球：半径 Slider（1–10mm）+ 取色板
  - 骨骼连线：粗细 Slider（1–20px）+ 取色板
  - 坐标轴：长度 Slider（1–30mm）
  - 底部"导出配置"/"加载配置"按钮，配置持久化为 JSON
  - 左右手使用统一设置，调整实时生效（16ms 渲染帧内更新）
- `python_draw3d/draw_config_io.py`：新增 `DrawConfig` dataclass 及 `save_config` / `load_config`，负责绘图配置的 JSON 序列化与反序列化；字段缺失时自动用默认值填充（向前兼容）。
- **菜单栏"窗口"菜单**：新增"窗口(&W)"菜单，含两个可勾选子项"数据面板"和"配置面板"，分别控制左侧/右侧面板的显示/隐藏，隐藏后 VTK 视口自动扩展。
- `src/motionGloveSDK.py`：新增 `MotionGloveSDK_GetActorNames()` 接口，返回当前已发现的所有套装名称列表。
- **左侧面板套装名称显示**：接收到数据后，左侧面板实时显示当前数据包中的套装名称（如 Glove1、Glove2）。
- **FPS 抖动修复**（`python_draw3d/fps_counter.py`）：`snapshot()` 改用 `time.monotonic()` 测量实际经过时间做除法，消除定时器误差引起的 ±1fps 抖动。
- `python_draw3d/bone_joint_actor.py`：新增 `set_radius(radius)` 和 `set_sphere_color(r, g, b)` 运行时接口，支持动态修改关节球半径和颜色；同时已支持 `set_axis_length`、`set_axis_line_width` 接口。
- `python_draw3d/bone_link_actor.py`：新增 `BoneLinkActor`，封装父子骨骼关节间的 VTK 连线 Actor；支持 `set_color`、`set_line_width` 运行时接口（配合配置面板使用）。
- **左侧面板接收控制按钮**：新增"开始"/"停止"按钮控制 UDP 接收；左侧面板实时显示当前帧序号、总帧数、帧率（每秒统计一次）；重新开始接收时各计数重置。
- `python_draw3d/fps_counter.py`：新增 `FpsCounter` 类，提供 `tick()` / `snapshot()` / `fps()` / `reset()` 接口，用于整秒桶计数式帧率统计。
- **帧丢失检测与警告**：3D 查看器和 `motionGloveSDK_rawReceiver.py` 均新增帧序号连续性检测；检测到不连续时，前者在状态栏显示丢帧范围和累计丢失数，后者在终端打印警告。
- **丢帧根因修复**（`src/motionGloveSDK.py`）：将 `_actor_store` 单槽缓冲改为 `queue.Queue` per actor，`_poll` 线程消费完整队列，彻底消除单槽覆盖导致的每秒 2–3 帧丢失。
- **开源声明对话框**（`ui/oss_licenses_dialog.py`）：帮助菜单新增"开源声明"，弹出对话框列出所有第三方库的许可证信息。
- `scripts/` 子文件夹：新增所有平台实用脚本目录，移入原根目录下的 6 个脚本并修正内部路径引用。
- `ui/left_panel.ui` + `ui/left_panel_widget.py`：将左侧面板提取为独立 Qt Designer 布局文件 + 控制器，通过 `QUiLoader` 运行时加载。
- **端口占用错误提示**：UDP 端口绑定失败时，左侧面板以红色文字显示占用程序名称及 PID。
- `python_draw3d/ground_plane.py`：新增地平面网格 Actor（X–Z 平面，5 cm 间距，右键菜单切换）。
- **PySide6 主窗口**：将 VTK 视口嵌入 `QMainWindow`，含菜单栏（文件→退出、帮助→关于 Qt）、左侧面板、底部状态栏；右键短按弹出上下文菜单，可切换坐标轴和地平面显示。
- `src/motionGloveSDK.py`：新增 `MotionGloveSDK_GetLastRemoteAddr()` 公共接口，返回最近一次收到 UDP 数据包的发送方 `(ip, port)`。

### Changed
- `README.md`：更新 3D 查看器功能说明，新增绘图配置面板、窗口菜单、套装名称显示等特性描述；更新工程结构表格。
- `CLAUDE.md`：同步更新项目架构说明，补充新增模块和 UI 文件描述。
- `python_draw3d/vtk_axes.py`：`add_axes_to_renderer` 现在返回 `vtkAxesActor` 实例。
- 所有脚本移至 `scripts/` 子文件夹。
- `.github/workflows/ci-3dview.yml`：Linux CI 改用 `MOTIONGLOVE_CI_RENDER=0`（不构建 QApplication），解决 shiboken6 在 xvfb 下崩溃的问题。
