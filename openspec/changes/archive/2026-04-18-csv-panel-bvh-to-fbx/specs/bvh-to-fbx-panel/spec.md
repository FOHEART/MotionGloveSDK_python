## ADDED Requirements

### Requirement: BVH→FBX GroupBox 布局
`csv_import_panel.ui` SHALL 包含一个名为 `group_bvh_to_fbx` 的 `QGroupBox`（标题"BVH → FBX"），位于 `group_ctrl` 之后、`bottom_spacer` 之前，内含以下控件：`bvh2fbx_blender_edit`（QLineEdit 只读）、`bvh2fbx_blender_btn`（QPushButton）、`bvh2fbx_bvh_edit`（QLineEdit 只读）、`bvh2fbx_bvh_btn`（QPushButton）、`bvh2fbx_convert_btn`（QPushButton，初始禁用）、`bvh2fbx_open_btn`（QPushButton，初始禁用）。

#### Scenario: 面板初始状态
- **WHEN** 程序启动
- **THEN** `bvh2fbx_convert_btn` 和 `bvh2fbx_open_btn` 均为禁用状态

### Requirement: Blender 路径选择与持久化
`CsvImportWidget` SHALL 在构造时从 `config.json` 读取 `blender_exe` 字段并填入 `bvh2fbx_blender_edit`；用户点击 `bvh2fbx_blender_btn` 后弹出 `QFileDialog` 过滤 `blender.exe`，选择后立即写回 `config.json`。

#### Scenario: 启动时已有保存路径
- **WHEN** `config.json` 中 `blender_exe` 非空
- **THEN** `bvh2fbx_blender_edit` 显示该路径，`bvh2fbx_convert_btn` 若已选 BVH 则可用

#### Scenario: 用户选择 Blender 路径
- **WHEN** 用户点击 `bvh2fbx_blender_btn` 并确认选择 `blender.exe`
- **THEN** `bvh2fbx_blender_edit` 更新为所选路径，`config.json` 立即写入新路径

#### Scenario: 用户取消选择
- **WHEN** 用户点击 `bvh2fbx_blender_btn` 后取消对话框
- **THEN** `bvh2fbx_blender_edit` 内容不变，`config.json` 不写入

### Requirement: BVH 文件选择（不持久化）
用户点击 `bvh2fbx_bvh_btn` 后弹出 `QFileDialog` 过滤 `*.bvh`，选中路径填入 `bvh2fbx_bvh_edit`；该路径不写入 `config.json`。

#### Scenario: 用户选择 BVH 文件
- **WHEN** 用户选择一个 BVH 文件
- **THEN** `bvh2fbx_bvh_edit` 显示完整路径；若 `bvh2fbx_blender_edit` 亦非空，则 `bvh2fbx_convert_btn` 变为可用

#### Scenario: 两个路径均就绪时转换按钮启用
- **WHEN** `bvh2fbx_blender_edit` 和 `bvh2fbx_bvh_edit` 均非空
- **THEN** `bvh2fbx_convert_btn` 变为可用

### Requirement: 转换执行
点击 `bvh2fbx_convert_btn` 后，`CsvImportWidget` SHALL 在 `QThread` 中调用 `subprocess.run` 执行 Blender 后台转换，转换期间禁用 `bvh2fbx_convert_btn`；转换成功后启用 `bvh2fbx_open_btn` 并弹出成功提示，失败时弹出含 stderr 的错误对话框。

#### Scenario: 转换成功
- **WHEN** 用户点击"转换"且 Blender 进程退出码为 0
- **THEN** 弹出成功对话框，`bvh2fbx_open_btn` 变为可用，`bvh2fbx_convert_btn` 恢复可用

#### Scenario: 转换失败
- **WHEN** Blender 进程退出码非 0 或启动失败
- **THEN** 弹出含 stderr 内容的错误对话框，`bvh2fbx_convert_btn` 恢复可用，`bvh2fbx_open_btn` 保持原状

### Requirement: 打开输出目录并选中 FBX
点击 `bvh2fbx_open_btn` 后，系统文件管理器 SHALL 打开 FBX 所在目录并将焦点定位到该文件（Windows: `explorer /select,<fbx>`；macOS: `open -R <fbx>`；Linux: `xdg-open <dir>`）。

#### Scenario: Windows 打开并选中
- **WHEN** 用户在 Windows 上点击"打开路径"
- **THEN** 资源管理器打开并高亮显示目标 FBX 文件

#### Scenario: 非 Windows 打开目录
- **WHEN** 用户在 Linux/macOS 上点击"打开路径"
- **THEN** 系统文件管理器打开 FBX 所在目录
