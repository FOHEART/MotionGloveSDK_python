## Why

当前 BVH→FBX 分组只支持手动选择 `blender.exe`。在常见使用场景里，Blender 会随项目一起放在当前运行目录下的 `libs/` 中，用户每次首次使用都要手动定位路径，步骤重复且容易选错。

增加一个“自动检查 Blender 路径”按钮后，面板可以按约定目录自动查找 Blender 安装目录，找到后自动回填到 `bvh2fbx_blender_edit` 并持久化到配置文件，减少首次配置成本。

## What Changes

- 在 `ui/csv_import_panel.ui` 的 BVH→FBX 分组中，于“选择Blender路径”按钮下方新增一个按钮，用于自动检查 Blender 路径
- 在 `ui/csv_import_widget.py` 中新增自动检测逻辑：从当前运行目录下的 `libs/` 开始，查找名称包含 `blender` 的子目录，并检查该目录下是否存在 `blender.exe`
- 找到有效路径后，自动更新 `bvh2fbx_blender_edit`，调用现有配置保存逻辑写回 `config.json`，并刷新转换按钮状态
- 未找到时给出明确提示，不覆盖用户已手动保存的 Blender 路径

## Capabilities

### Modified Capabilities
- `bvh-to-fbx-panel`: 扩展 Blender 路径输入区域，增加自动检测入口与基于 `libs/` 的自动定位逻辑

## Impact

- `ui/csv_import_panel.ui` — BVH→FBX 分组增加一个新的自动检测按钮
- `ui/csv_import_widget.py` — 新增按钮引用、自动检测槽函数与路径查找逻辑
- `config.json` — 继续复用已有 `blender_exe` 字段，无需新增配置键
