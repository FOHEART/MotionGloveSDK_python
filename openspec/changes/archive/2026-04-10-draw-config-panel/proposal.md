## Why

当前 3D 骨架查看器的关节球大小、颜色、连线粗细、坐标轴长度均为硬编码常量，用户无法在运行时调整。增加右侧绘图配置面板，让用户可以实时调整视觉效果，并将配置持久化保存/加载。

## What Changes

- 界面右侧新增 `DrawConfigWidget`（固定宽度约 220px），包含：
  - 关节球半径滑块（Slider）+ 颜色选择按钮（取色板）
  - 骨骼连线宽度滑块 + 颜色选择按钮
  - 关节坐标轴长度滑块（三轴同步缩放）
  - 左右手使用相同设置（不分开配置）
- 新增 `draw_config_io.py`：负责将配置序列化为 JSON 文件及从文件加载
- 菜单栏新增"窗口"菜单，含两个子菜单项：
  - 切换左侧数据面板显示/隐藏
  - 切换右侧绘图配置面板显示/隐藏

## Capabilities

### New Capabilities

- `draw-config-panel`: 右侧绘图属性配置面板（Slider + 取色板），实时更新 VTK 场景中的关节球、连线、坐标轴属性
- `draw-config-io`: 绘图配置的 JSON 导入/导出功能（独立 py 文件）
- `window-visibility-menu`: 菜单栏"窗口"菜单，控制左右面板的显示/隐藏

### Modified Capabilities

（无现有 spec 级行为变更）

## Impact

- `motionGloveSDK_example3_3dView.py`：主窗口布局从 左面板+VTK 改为 左面板+VTK+右面板；菜单栏增加"窗口"菜单；`_on_timer` 可能需要读取配置面板当前值以刷新 VTK 属性
- `python_draw3d/bone_joint_actor.py`：需要暴露 set_radius / set_color / set_axes_length 之类的运行时接口
- `python_draw3d/bone_link_actor.py`：需要暴露 set_width / set_color 运行时接口
- 新文件：`ui/draw_config_widget.py`、`ui/draw_config_io.py`（或 `python_draw3d/draw_config_io.py`）
- 依赖：PySide6 `QColorDialog`（已在 PySide6 中，无需额外安装）
