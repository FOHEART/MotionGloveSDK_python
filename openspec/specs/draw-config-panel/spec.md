## ADDED Requirements

### Requirement: DrawConfigWidget 面板布局
界面右侧 SHALL 存在一个固定宽度（220px）的 `DrawConfigWidget`，包含以下分组控件：
- 关节球：半径 Slider（1–30，步进1，换算 ×0.001m）+ 颜色按钮
- 骨骼连线：宽度 Slider（1–10，步进1，单位 px）+ 颜色按钮
- 坐标轴：长度 Slider（1–60，步进1，换算 ×0.001m）
- 底部：导出配置按钮、加载配置按钮

#### Scenario: 初始默认值
- **WHEN** 软件启动
- **THEN** 关节球半径 Slider 值为 5（5mm），连线宽度 Slider 值为 2（2px），坐标轴长度 Slider 值为 10（10mm），各颜色按钮显示对应的默认颜色色块

#### Scenario: Slider 滑动实时生效
- **WHEN** 用户拖动任意 Slider
- **THEN** 下一个 16ms 渲染帧内，VTK 场景中所有关节球/连线/坐标轴的对应属性即时更新，无需额外确认

#### Scenario: 颜色按钮打开取色板
- **WHEN** 用户点击颜色按钮
- **THEN** 弹出 `QColorDialog`，用户选色后按钮背景色更新为所选颜色，VTK 场景在下一渲染帧应用新颜色

#### Scenario: 左右手使用相同设置
- **WHEN** 用户调整任意属性
- **THEN** 左右手（骨骼 0–15 和 16–31）的同类 actor 均使用相同配置，不区分左右手

### Requirement: current_config 接口
`DrawConfigWidget` SHALL 提供 `current_config() -> DrawConfig` 方法，返回当前所有控件值的 dataclass 快照。

#### Scenario: 读取配置快照
- **WHEN** 主窗口定时器调用 `current_config()`
- **THEN** 返回包含 `joint_radius`、`joint_color`、`link_width`、`link_color`、`axis_length` 字段的 `DrawConfig` 对象

### Requirement: BoneJointActor 运行时接口补充
`BoneJointActor` SHALL 提供 `set_radius(radius: float)` 和 `set_sphere_color(r, g, b)` 方法，支持运行时修改关节球半径和颜色。

#### Scenario: 运行时修改关节球半径
- **WHEN** 调用 `set_radius(0.008)`
- **THEN** 球体 vtkSphereSource 的半径更新为 0.008，下次渲染生效

#### Scenario: 运行时修改关节球颜色
- **WHEN** 调用 `set_sphere_color(1.0, 0.5, 0.0)`
- **THEN** 球体 actor 的颜色属性更新为橙色，下次渲染生效
