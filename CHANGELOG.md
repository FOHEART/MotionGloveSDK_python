# Changelog

## [Unreleased]

### Added
- `python_draw3d/bone_link_actor.py`：新增 `BoneLinkActor` 类，封装父子骨骼关节间的 VTK 连线 Actor，支持运行时调节颜色（`set_color`）和线宽（`set_line_width`）。
- `motionGloveSDK_example3_3dView.py`：根据 `src/kinemHumanHandsSkeleton32Index_tree.md` 定义骨骼父子关系表（`_BONE_LINKS`，共 30 条边），在 3D 视图中实时绘制手部骨骼连线；新增顶部配置项 `BONE_LINK_COLOR_RIGHT`、`BONE_LINK_COLOR_LEFT`、`BONE_LINK_WIDTH` 用于调节连线外观。
- **PySide6 主窗口**：将 VTK 视口嵌入 `QMainWindow`，新增菜单栏（文件→退出、帮助→关于 Qt）、左侧网络信息面板（实时显示 UDP 来源 IP 与端口）、底部状态栏。
- `src/motionGloveSDK.py`：新增 `MotionGloveSDK_GetLastRemoteAddr()` 公共接口，返回最近一次收到 UDP 数据包的发送方 `(ip, port)`。
- `python_draw3d/ground_plane.py`：新增 `build_ground_plane_actor(extent, spacing)`，生成 X–Z 平面灰色网格 Actor（默认 ±30 cm，5 cm 间距）。
- **VTK 视口右键菜单**：短按右键弹出上下文菜单，支持切换坐标轴显示/隐藏和地平面显示/隐藏；拖拽缩放时不触发菜单。
- **左侧面板 UI 文件独立**：将左侧网络信息面板提取为 `ui/left_panel.ui`（Qt Designer 可编辑），配套控制器 `ui/left_panel_widget.py`；主脚本通过 `QUiLoader` 在运行时加载，无需编译步骤。
- **端口占用错误提示**：若 UDP 端口绑定失败（被其他程序占用），左侧面板以红色文字显示占用程序名称及 PID，窗口正常打开便于用户查看信息。

### Changed
- `README.md`：新增"Python 版本要求"章节，明确最低要求 Python 3.10。
- `CLAUDE.md`：新增 AI 协作上下文文件，描述项目结构、架构、常用命令及 CI 配置。
- `python_draw3d/vtk_axes.py`：`add_axes_to_renderer` 现在返回 `vtkAxesActor` 实例；参数类型由 `int` 改为 `float`。
- `[Windows]setup_python_libs.cmd` / `[Linux]setup_python_libs.sh`：运行时依赖新增 `pyside6==6.5.3`。
- 所有脚本（`setup_python_libs`、`git_pull_latest`、`open_in_vscode`）移至 `scripts/` 子文件夹；脚本内部路径引用已更新为相对于项目根目录。
- `.github/workflows/ci-3dview.yml`：Linux 作业新增 `QT_QPA_PLATFORM: offscreen` 环境变量及 Qt/EGL 系统包安装步骤。
