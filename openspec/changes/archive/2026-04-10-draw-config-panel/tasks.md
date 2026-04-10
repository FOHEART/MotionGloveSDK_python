## 1. 数据结构与 IO 模块

- [x] 1.1 在 `python_draw3d/draw_config_io.py` 中定义 `DrawConfig` dataclass，包含 `joint_radius`、`joint_color`、`link_width`、`link_color`、`axis_length` 字段及 `default()` 类方法
- [x] 1.2 实现 `save_config(config: DrawConfig, path: str) -> None`，序列化为 JSON
- [x] 1.3 实现 `load_config(path: str) -> DrawConfig`，从 JSON 反序列化，字段缺失时用 `default()` 填充

## 2. Actor 运行时接口补充

- [x] 2.1 在 `python_draw3d/bone_joint_actor.py` 中为 `BoneJointActor` 添加 `set_radius(radius: float)` 方法
- [x] 2.2 在 `python_draw3d/bone_joint_actor.py` 中为 `BoneJointActor` 添加 `set_sphere_color(r, g, b)` 方法

## 3. DrawConfigWidget 面板

- [x] 3.1 新建 `ui/draw_config_widget.py`，定义 `DrawConfigWidget(QWidget)`，固定宽度 220px
- [x] 3.2 添加"关节球"分组：半径 Slider（1–30）+ 颜色按钮，颜色按钮点击弹出 `QColorDialog`，按钮背景色同步更新
- [x] 3.3 添加"骨骼连线"分组：宽度 Slider（1–10）+ 颜色按钮
- [x] 3.4 添加"坐标轴"分组：长度 Slider（1–60）
- [x] 3.5 添加底部"导出配置"和"加载配置"按钮，调用 `draw_config_io` + `QFileDialog`
- [x] 3.6 实现 `current_config() -> DrawConfig`，返回当前所有控件值的快照（Slider 值换算为实际单位）
- [x] 3.7 实现 `load_from_config(config: DrawConfig)`，将外部配置同步回控件状态（用于加载文件后刷新 UI）

## 4. 主窗口集成

- [x] 4.1 在 `motionGloveSDK_example3_3dView.py` 的主布局中，将 `DrawConfigWidget` 添加到 VTK 视口右侧（`QHBoxLayout`：左面板 + VTK + 右面板）
- [x] 4.2 在 `_on_timer` 中，调用 `_draw_config_widget.current_config()` 并将配置推送给所有 32 个 `BoneJointActor` 和 30 个 `BoneLinkActor`（仅在配置发生变化时推送，避免每帧无谓调用）
- [x] 4.3 菜单栏新增"窗口(&W)"菜单，添加"数据面板"和"配置面板"两个 `checkable` `QAction`，`triggered` 连接对应 widget 的 `setVisible`

## 5. 验证

- [x] 5.1 启动程序，验证三组 Slider 滑动后 VTK 场景实时更新
- [x] 5.2 点击颜色按钮，选色，验证 VTK 颜色变化
- [x] 5.3 导出配置为 JSON，检查文件内容；重新加载，验证控件恢复
- [x] 5.4 通过"窗口"菜单切换左/右面板显示，验证 VTK 视口自动扩展
