## MODIFIED Requirements

### Requirement: Blender 路径选择与持久化
`CsvImportWidget` SHALL 在构造时从 `config.json` 读取 `blender_exe` 字段并填入 `bvh2fbx_blender_edit`；用户既可以点击 `bvh2fbx_blender_btn` 手动选择 `blender.exe`，也可以点击新增的 `bvh2fbx_blender_auto_btn` 自动检测 Blender 路径。自动检测逻辑 SHALL 从当前运行目录下的 `libs/` 目录开始，扫描名称包含 `blender` 的一级子目录，并检查候选目录根下是否存在 `blender.exe`；找到首个有效路径后立即写回 `config.json`。

#### Scenario: 用户手动选择 Blender 路径
- **WHEN** 用户点击 `bvh2fbx_blender_btn` 并确认选择 `blender.exe`
- **THEN** `bvh2fbx_blender_edit` 更新为所选路径，`config.json` 立即写入新路径

#### Scenario: 自动检测成功
- **WHEN** 用户点击 `bvh2fbx_blender_auto_btn`，且当前运行目录下的 `libs/` 中存在名称包含 `blender` 的子目录，并且该目录根下存在 `blender.exe`
- **THEN** `bvh2fbx_blender_edit` 更新为检测到的 `blender.exe` 路径，`config.json` 立即写入该路径

#### Scenario: 自动检测失败且保留现有值
- **WHEN** 用户点击 `bvh2fbx_blender_auto_btn`，但 `libs/` 不存在、没有任何目录名包含 `blender` 的候选目录，或所有候选目录中都不存在 `blender.exe`
- **THEN** 界面提示未找到 Blender 路径，且 `bvh2fbx_blender_edit` 保持原值不变，`config.json` 不被新的空值覆盖

### Requirement: BVH→FBX GroupBox 布局
`csv_import_panel.ui` SHALL 在 `group_bvh_to_fbx` 中包含 `bvh2fbx_blender_auto_btn`，并将其布局在 `bvh2fbx_blender_btn` 下方，作为 Blender 路径区域的一部分。

#### Scenario: 分组显示自动检测按钮
- **WHEN** CSV 回放面板加载 BVH→FBX 分组
- **THEN** 用户可以在“选择 Blender 路径”按钮下方看到“自动检查 Blender 路径”按钮
