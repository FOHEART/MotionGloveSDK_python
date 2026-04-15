## ADDED Requirements

### Requirement: AppMode 枚举与 APP_MODE 常量
主脚本 SHALL 在顶层定义 `AppMode` 枚举（`UDP_STREAM`、`CSV_PLAYBACK`）和 `APP_MODE: AppMode` 常量，修改该常量即可切换启动模式，无需命令行参数。

#### Scenario: 默认模式为 UDP_STREAM
- **WHEN** 用户未修改 `APP_MODE`
- **THEN** 程序以 UDP 接收模式启动，行为与修改前完全相同

#### Scenario: 切换为 CSV 回放模式
- **WHEN** 用户将 `APP_MODE = AppMode.CSV_PLAYBACK`
- **THEN** 程序启动后加载 CSV 导入面板，不启动 UDP 后台线程

### Requirement: CSV 播放定时器
CSV 回放模式 SHALL 使用专用 `QTimer _csv_timer`，按 `CsvImportWidget` 当前帧率设置触发，每次回调从 `CsvFrameReader` 取下一帧写入 `_latest_frame[0]`，由现有 16ms 渲染定时器负责渲染。

#### Scenario: 按帧率逐帧推进
- **WHEN** `_csv_timer` 触发
- **THEN** 调用 `CsvFrameReader.next_frame()`，将返回的 `GloveFrame` 写入 `_latest_frame[0]`，下一个 16ms 渲染周期即时生效

#### Scenario: 到达末帧后停止
- **WHEN** `CsvFrameReader.at_end` 为 `True`
- **THEN** `_csv_timer` 停止，播放按钮文字恢复为"开始播放"，停留在最后一帧画面

#### Scenario: 再次点击"开始播放"从头重播
- **WHEN** 播放已到末帧停止，用户点击"开始播放"
- **THEN** `CsvFrameReader.reset()` 被调用，`_csv_timer` 重新启动，从第 0 帧开始播放

### Requirement: DrawConfigWidget 在 CSV 模式下可用
两种模式下 SHALL 均加载右侧 `DrawConfigWidget`，绘图配置实时生效。

#### Scenario: CSV 模式下调整关节球颜色
- **WHEN** 用户在 CSV 回放模式下通过 DrawConfigWidget 修改关节球颜色
- **THEN** VTK 场景在下一渲染帧更新颜色，与 UDP 模式行为一致
