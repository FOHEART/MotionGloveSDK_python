## Why

当前 3D 查看器只支持实时 UDP 数据流模式，无法回放已录制的动作数据。增加 CSV 文件回放模式，使开发者和用户能够在没有硬件设备的情况下重现、调试和展示已录制的手部动作序列。

## What Changes

- `motionGloveSDK_example3_3dView.py` 顶层新增 `AppMode` 枚举（`UDP_STREAM` / `CSV_PLAYBACK`），并以顶层常量 `APP_MODE` 控制启动行为；两种模式共用同一个 `MotionGloveMainWindow`，只在左侧面板和数据驱动逻辑上存在差异
- **模式一（UDP_STREAM）**：行为与现状完全相同，加载 `LeftPanelWidget`
- **模式二（CSV_PLAYBACK）**：
  - 左侧改为加载 `CsvImportWidget`（对应 `ui/csv_import.ui` + `ui/csv_import_widget.py`），含：
    - `QLineEdit` 显示当前文件路径
    - 文件选择按钮（`QFileDialog`）
    - 帧率选择器（`QComboBox`，选项：10 / 24 / 30 / 60 Hz，默认 60）
    - 开始/暂停播放按钮（文字随状态切换：开始播放 ↔ 暂停播放）
    - 重置按钮（回到第一帧并停止）
  - CSV 逐行解析逻辑提取到 `src/csv_frame_reader.py`（独立模块，供多种模式复用）
  - 播放引擎：`QTimer` 按选定帧率触发，逐帧渲染到 VTK；到达末帧后停止；再次点击"开始播放"从头重播
- 右侧 `DrawConfigWidget` 在两种模式下均加载，绘图配置始终可用

## Capabilities

### New Capabilities

- `csv-playback-mode`: CSV 文件回放模式：加载文件、按帧率播放、暂停/继续/重置，到末帧自动停止
- `csv-import-panel`: 左侧 CSV 导入面板（`CsvImportWidget`）：文件选择、帧率设置、播放控制按钮
- `csv-frame-reader`: `src/csv_frame_reader.py` — 从 CSV 文件按行读取并解析为 `GloveFrame`，供多模式复用

### Modified Capabilities

- `pyside6-main-window`: 主窗口新增 `AppMode` 枚举和模式分支逻辑，左侧面板根据模式动态切换

## Impact

- `motionGloveSDK_example3_3dView.py`：新增 `AppMode` 枚举、顶层 `APP_MODE` 常量；`_build_central` 根据模式选择左侧面板；`_start_sdk_poll` 仅在 UDP 模式下启动；新增 CSV 播放定时器逻辑
- 新文件：`src/csv_frame_reader.py`、`ui/csv_import.ui`、`ui/csv_import_widget.py`
- `src/decode_glove_csv.py`：可能需要暴露独立的单行解析入口（视 `csv_frame_reader.py` 实现而定）
- 无新的第三方依赖（`QFileDialog`、`QComboBox` 均属 PySide6 标准组件）
