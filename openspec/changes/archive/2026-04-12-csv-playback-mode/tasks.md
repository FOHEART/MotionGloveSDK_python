## 1. CsvFrameReader 解析模块

- [x] 1.1 新建 `src/csv_frame_reader.py`，定义 `CsvFrameReader` 类，构造时接受文件路径并预加载全部行到 `list[str]`
- [x] 1.2 实现 `next_frame() -> GloveFrame | None`：解析当前索引行（调用 `decode_glove_csv`），索引加 1；末帧返回 `None`
- [x] 1.3 实现 `reset()` 方法和 `at_end`、`total_frames`、`current_index` 属性
- [x] 1.4 第一行用 `parse_header_tokens` 解析为 header，后续行复用同一 header

## 2. AppMode 枚举与顶层常量

- [x] 2.1 在 `motionGloveSDK_example3_3dView.py` 顶部新增 `import enum`，定义 `AppMode(enum.Enum)` 含 `UDP_STREAM` 和 `CSV_PLAYBACK`
- [x] 2.2 在配置区添加 `APP_MODE = AppMode.UDP_STREAM`（顶层常量，用户修改此行切换模式）

## 3. CsvImportWidget 面板

- [x] 3.1 新建 `ui/csv_import_widget.py`，定义 `CsvImportWidget(QWidget)`，固定宽度 220px
- [x] 3.2 添加 `QLineEdit`（只读）显示文件路径 + "选择文件"按钮，点击弹出 `QFileDialog` 过滤 `*.csv`
- [x] 3.3 添加帧率 `QComboBox`（选项：10 / 24 / 30 / 60，单位 Hz，默认选中 60）
- [x] 3.4 添加"开始播放"按钮（文字随状态切换为"暂停播放"）和"重置"按钮
- [x] 3.5 未选择文件时禁用播放/重置按钮；选择文件成功后启用
- [x] 3.6 暴露信号/回调：`on_file_selected(path)`、`on_play_pause()`、`on_reset()`、`fps` 属性
- [x] 3.7 提供 `set_playing(is_playing: bool)` 方法，由主窗口驱动按钮文字和状态

## 4. 主窗口集成

- [x] 4.1 在 `_build_central` 中，根据 `APP_MODE` 选择加载 `LeftPanelWidget`（UDP）或 `CsvImportWidget`（CSV），两种模式均加载 `DrawConfigWidget`
- [x] 4.2 在 `__init__` 中，根据 `APP_MODE` 决定是否调用 `_start_sdk_poll()`；CSV 模式下跳过 UDP 初始化
- [x] 4.3 新增 `_start_csv_playback()` 方法：创建 `_csv_timer = QTimer()`，连接到 `_on_csv_tick()`；绑定 `CsvImportWidget` 的播放/暂停/重置信号
- [x] 4.4 实现 `_on_csv_tick()`：调用 `_reader.next_frame()`，写入 `_latest_frame[0]`；若 `_reader.at_end`，停止定时器并通知 `CsvImportWidget` 更新按钮状态
- [x] 4.5 实现帧率变更逻辑：用户改变 `QComboBox` 时，若正在播放则立即更新 `_csv_timer.setInterval(round(1000/fps))`
- [x] 4.6 在 `closeEvent` 中停止 `_csv_timer`（CSV 模式）

## 5. 验证

- [x] 5.1 修改 `APP_MODE = AppMode.UDP_STREAM`，验证程序行为与修改前完全一致
- [x] 5.2 修改 `APP_MODE = AppMode.CSV_PLAYBACK`，验证左侧面板切换，UDP 线程未启动
- [x] 5.3 选择一个 CSV 文件，点击"开始播放"，验证 VTK 场景按帧率播放
- [x] 5.4 播放中切换帧率，验证播放速度立即改变
- [x] 5.5 播放到末帧，验证自动停止，再点击"开始播放"从头重播
- [x] 5.6 点击"重置"，验证回到第一帧并停止
- [x] 5.7 CSV 模式下调整 DrawConfigWidget，验证 VTK 场景实时更新
