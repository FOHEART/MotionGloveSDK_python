## Why

用户完成 CSV→BVH 转换后，需要额外手动执行命令行才能将 BVH 转为 FBX，工作流割裂。在 CSV 回放面板中直接提供 BVH→FBX 转换入口，可让整个导出流程在一个界面内完成。

## What Changes

- 在 `ui/csv_import_panel.ui` 中新增 `QGroupBox`（标题"BVH → FBX"），包含 Blender 路径选择、BVH 文件选择、转换按钮、打开输出目录按钮
- `ui/csv_import_widget.py` 中新增对应槽函数：读写 Blender 路径到 `config.json`、调用 Blender 后台模式执行 `scripts/bvh_to_fbx.py`、转换完成后用系统文件管理器打开并选中 FBX 文件
- `config.json`（由 `python_draw3d/draw_config_io.py` 管理）扩展一个 `blender_exe` 字段，持久化 Blender 安装路径

## Capabilities

### New Capabilities
- `bvh-to-fbx-panel`: CSV 回放面板内的 BVH→FBX 转换 UI，含 Blender 路径持久化、BVH 文件选择、后台转换调用、输出目录定位

### Modified Capabilities
- `csv-import-panel`: 在现有面板 UI 文件中追加新 GroupBox，扩展面板功能
- `draw-config-io`: `DrawConfig` 新增 `blender_exe: str` 字段，`save_config`/`load_config` 同步支持

## Impact

- `ui/csv_import_panel.ui` — Qt Designer 文件，新增 GroupBox 及子控件
- `ui/csv_import_widget.py` — 新增槽函数与初始化逻辑
- `python_draw3d/draw_config_io.py` — `DrawConfig` dataclass 扩展字段
- `scripts/bvh_to_fbx.py` — 已存在，无需修改
- 依赖：`subprocess`（标准库）、`os`（标准库）、PySide6（已有）
