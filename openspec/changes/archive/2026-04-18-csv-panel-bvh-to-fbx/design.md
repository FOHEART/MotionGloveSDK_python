## Context

面板当前已有 CSV 文件选择、帧率设置、播放控制、BVH 导出四个 GroupBox。`csv_import_panel.ui` 由 `QUiLoader` 运行时加载，无编译步骤。`draw_config_io.py` 已管理 `config.json`（VTK 绘制属性），可扩展 `blender_exe` 字段。`scripts/bvh_to_fbx.py` 已实现 Blender 后台转换逻辑，接受命令行参数。

## Goals / Non-Goals

**Goals:**
- 在面板底部新增 `group_bvh_to_fbx` GroupBox，含 Blender 路径选择、BVH 文件选择、转换、打开输出目录四个功能
- Blender 路径持久化到 `config.json`（复用现有 `DrawConfig` / `draw_config_io` 机制）
- BVH 路径不持久化
- 转换通过 `subprocess` 后台调用 Blender，不阻塞 UI（使用 `QThread` 或 `subprocess.Popen` + 完成回调）
- 打开输出目录并选中 FBX 文件（Windows: `explorer /select,<path>`；Linux: `xdg-open <dir>`；macOS: `open -R <path>`）

**Non-Goals:**
- 批量转换多个 BVH（单文件即可）
- 转换进度条（只需转换中禁用按钮 + 完成弹窗）
- 修改 `scripts/bvh_to_fbx.py`

## Decisions

**1. Blender 路径存储位置：扩展 `DrawConfig` 而非新建配置文件**
- `DrawConfig` 已有完整 save/load 机制，且 `config.json` 已是持久化单一入口
- 替代方案：独立 `bvh_config.json` — 增加文件管理复杂度，不选
- `DrawConfig` 新增 `blender_exe: str = ""`，`save_config`/`load_config` 同步处理

**2. 转换调用方式：`subprocess.Popen` + `QThread` 包装**
- Blender 后台转换耗时数秒，必须非阻塞
- `QThread` 包装 `subprocess.run`，完成后 emit signal 回主线程弹窗
- 替代方案：`QProcess` — 与现有 subprocess 风格不一致，不选

**3. UI 结构：新 GroupBox 追加在 `bottom_spacer` 之前**
- 保持现有控件名称不变，新控件名称前缀 `bvh2fbx_`
- 控件名：`bvh2fbx_blender_edit`、`bvh2fbx_blender_btn`、`bvh2fbx_bvh_edit`、`bvh2fbx_bvh_btn`、`bvh2fbx_convert_btn`、`bvh2fbx_open_btn`

**4. `config.json` 读取时机：`CsvImportWidget.__init__` 初始化时**
- 若 `config.json` 不存在或 `blender_exe` 为空，`blender_edit` 留空
- 用户选择路径后立即调用 `save_config` 写回

## Risks / Trade-offs

- [转换失败无详细错误] → 捕获 `subprocess` 的 `stdout/stderr`，在错误弹窗中显示
- [config.json 路径] → 复用主窗口已确定的路径（`draw_config_io.py` 所在目录下的 `config.json`），`CsvImportWidget` 需要知道此路径；通过构造函数参数 `config_path: str` 传入，默认值指向工程根目录的 `config.json`
- [面板高度溢出] → GroupBox 内控件紧凑排列（间距 4px），预计新增高度约 130px，在 1080p 以上屏幕不成问题
