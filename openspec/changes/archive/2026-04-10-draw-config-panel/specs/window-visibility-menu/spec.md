## ADDED Requirements

### Requirement: 菜单栏"窗口"菜单
菜单栏 SHALL 新增"窗口(&W)"菜单，包含两个可勾选子菜单项，控制对应面板的显示/隐藏。

#### Scenario: 初始状态两项均勾选
- **WHEN** 软件启动
- **THEN** "数据面板"和"配置面板"两个菜单项均处于勾选（checked）状态，对应面板可见

#### Scenario: 点击"数据面板"隐藏左侧面板
- **WHEN** 用户点击已勾选的"数据面板"菜单项
- **THEN** 勾选状态取消，左侧 `LeftPanelWidget` 隐藏（`setVisible(False)`），VTK 视口水平扩展

#### Scenario: 再次点击"数据面板"恢复显示
- **WHEN** 用户点击未勾选的"数据面板"菜单项
- **THEN** 勾选状态恢复，左侧面板重新可见

#### Scenario: 点击"配置面板"隐藏右侧面板
- **WHEN** 用户点击已勾选的"配置面板"菜单项
- **THEN** 勾选状态取消，右侧 `DrawConfigWidget` 隐藏，VTK 视口水平扩展

#### Scenario: 再次点击"配置面板"恢复显示
- **WHEN** 用户点击未勾选的"配置面板"菜单项
- **THEN** 勾选状态恢复，右侧面板重新可见
