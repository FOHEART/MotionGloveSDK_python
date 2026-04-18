## 1. 数据层：扩展 DrawConfig

- [x] 1.1 在 `python_draw3d/draw_config_io.py` 的 `DrawConfig` dataclass 中新增 `blender_exe: str = ""` 字段
- [x] 1.2 在 `save_config` 中将 `blender_exe` 写入 JSON 输出字典
- [x] 1.3 在 `load_config` 中读取 `blender_exe`，键缺失时回退为 `""`

## 2. UI 文件：新增 GroupBox

- [x] 2.1 在 `ui/csv_import_panel.ui` 的 `bottom_spacer` 之前插入 `group_bvh_to_fbx`（QGroupBox，标题"BVH → FBX"）
- [x] 2.2 在 GroupBox 内添加 Blender 路径行：`bvh2fbx_blender_edit`（QLineEdit 只读）+ `bvh2fbx_blender_btn`（QPushButton "选择 Blender…"）
- [x] 2.3 添加 BVH 文件行：`bvh2fbx_bvh_edit`（QLineEdit 只读）+ `bvh2fbx_bvh_btn`（QPushButton "选择 BVH…"）
- [x] 2.4 添加 `bvh2fbx_convert_btn`（QPushButton "转换为 FBX"，初始 `enabled=false`）
- [x] 2.5 添加 `bvh2fbx_open_btn`（QPushButton "打开输出路径"，初始 `enabled=false`）

## 3. Widget：初始化与槽函数

- [x] 3.1 在 `CsvImportWidget.__init__` 添加 `config_path: str = ""` 参数，缺省指向工程根目录的 `config.json`
- [x] 3.2 使用 `_find` 获取五个新控件的引用，存为实例变量
- [x] 3.3 构造时调用 `load_config`（若文件存在）读取 `blender_exe`，填入 `bvh2fbx_blender_edit`，并调用 `_update_convert_btn_state`
- [x] 3.4 实现 `_on_blender_browse`：弹出 `QFileDialog` 过滤 `blender.exe`，选中后更新 edit、调用 `save_config` 写回、调用 `_update_convert_btn_state`
- [x] 3.5 实现 `_on_bvh_browse`：弹出 `QFileDialog` 过滤 `*.bvh`，选中后更新 edit、调用 `_update_convert_btn_state`
- [x] 3.6 实现 `_update_convert_btn_state`：两个 edit 均非空时启用 `bvh2fbx_convert_btn`，否则禁用
- [x] 3.7 实现 `_BvhConvertThread`（`QThread` 子类）：接收 blender_exe、bvh_path、script_path，`run()` 中执行 `subprocess.run`，emit `finished(int, str)` 信号（exit_code, stderr）
- [x] 3.8 实现 `_on_convert`：禁用转换按钮、启动 `_BvhConvertThread`，连接 `finished` 信号到 `_on_convert_finished`
- [x] 3.9 实现 `_on_convert_finished`：退出码 0 时弹出成功提示并启用 `bvh2fbx_open_btn`；非 0 时弹出含 stderr 的错误对话框；恢复转换按钮可用
- [x] 3.10 实现 `_on_open_output`：根据平台调用 `explorer /select,<fbx>`（Windows）或 `open -R`（macOS）或 `xdg-open <dir>`（Linux）
- [x] 3.11 在 `__init__` 中连接所有新信号槽

## 4. 验证

- [ ] 4.1 启动程序，确认 GroupBox 正常显示，转换和打开按钮初始禁用
- [ ] 4.2 选择 Blender 路径，确认 `config.json` 写入 `blender_exe` 字段，重启后路径自动恢复
- [ ] 4.3 选择 BVH 文件，确认转换按钮启用
- [ ] 4.4 点击转换，确认 `csvfile/stance4.bvh` 生成对应 `stance4.fbx`，弹出成功提示
- [ ] 4.5 点击打开路径，确认文件管理器打开并定位到 FBX 文件
