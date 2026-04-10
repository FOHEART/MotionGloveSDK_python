## Context

当前主窗口布局：`[左侧面板 220px | VTK 视口 (stretch)]`。所有绘制属性（关节球半径、颜色、连线粗细/颜色、坐标轴长度）均为构造时的硬编码常量，运行时无法修改。`BoneJointActor` 和 `BoneLinkActor` 已各自提供了运行时 setter 接口（`set_axis_length`、`set_color`、`set_line_width` 等），具备被外部驱动的条件。

## Goals / Non-Goals

**Goals:**
- 界面右侧新增 `DrawConfigWidget`，提供 Slider + 取色板控件，实时更新 VTK 场景
- 主窗口布局变为 `[左侧面板 | VTK (stretch) | 右侧配置面板 220px]`
- 新增 `draw_config_io.py` 独立处理 JSON 配置的读写
- 菜单栏"窗口"菜单，含两个子项控制左右面板的显示/隐藏
- 左右手使用统一设置（不分开）

**Non-Goals:**
- 不提供每根骨骼的独立颜色设置
- 不提供坐标轴 X/Y/Z 三轴独立颜色修改（保持固定 RGB）
- 不提供动画/关键帧配置

## Decisions

### D1：DrawConfigWidget 作为独立 QWidget 文件放在 `ui/`
与 `LeftPanelWidget` 一致，放 `ui/draw_config_widget.py`。不使用 `.ui` 文件（控件数量少、结构简单，纯代码构建比 Qt Designer 更易维护）。

**Alternative considered**: 使用 `.ui` + `QUiLoader`，与现有 `left_panel.ui` 风格一致 — 但 Slider + 颜色按钮的布局逻辑用代码表达更直接，避免 Qt Designer 文件的额外往返。

### D2：配置值以 `DrawConfig` dataclass 传递，不直接互通 widget 引用
主窗口持有 `DrawConfigWidget` 引用，在 `_on_timer`（16ms 渲染定时器）中读取 `DrawConfigWidget.current_config()` → `DrawConfig` → 逐帧推送给所有 actor。不使用信号连接，避免多线程竞态。

**Alternative considered**: 信号 `configChanged` 触发立即更新 — 会在主线程事件循环中立即触发 VTK Render，与 `_on_timer` 驱动的渲染节奏不一致，可能导致重复渲染。

### D3：`draw_config_io.py` 放在 `python_draw3d/`，与其他绘制辅助模块同级
导入路径与 `fps_counter.py` 等一致。`DrawConfigWidget` 调用 `io` 模块完成文件对话框 + 读写。

### D4：Slider 精度范围
| 属性 | Slider 范围 | 步进 | 实际值换算 |
|---|---|---|---|
| 关节球半径 | 1 – 30 | 1 | slider_value × 0.001 m（即 1–30 mm）|
| 连线宽度 | 1 – 10 | 1 | slider_value px（整数像素）|
| 坐标轴长度 | 1 – 60 | 1 | slider_value × 0.001 m（即 1–60 mm）|

### D5：菜单"窗口"控制面板可见性
`QAction` 设为 `checkable=True`，初始均勾选（面板可见）。`triggered` 信号直接调用对应 widget 的 `setVisible`。

## Risks / Trade-offs

- **每帧 16ms 读取 DrawConfig**: `current_config()` 返回 dataclass（轻量复制），32×3 次 setter 调用全在主线程，VTK 属性设置本身非常快。实测 60Hz 下 CPU 开销可忽略。
- **颜色存储为 `(r, g, b)` float 元组**: JSON 序列化直接用列表，与 VTK `SetColor` 接口匹配无需转换。
- **BoneJointActor 缺少 `set_radius` 和 `set_color`**: 当前 `BoneJointActor` 没有暴露运行时修改球体半径/颜色的接口，需补充这两个方法（`_sphere_src.SetRadius` + `_s_actor.GetProperty().SetColor`）。
