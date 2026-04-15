## MODIFIED Requirements

### Requirement: 主窗口支持多启动模式
主窗口 SHALL 根据 `APP_MODE` 枚举值在启动时选择不同的左侧面板和数据驱动逻辑：`UDP_STREAM` 模式行为与现有规格完全一致；`CSV_PLAYBACK` 模式加载 `CsvImportWidget`、不启动 UDP 后台线程、改用 CSV 播放定时器驱动 `_latest_frame[0]`。

#### Scenario: UDP_STREAM 模式启动
- **WHEN** `APP_MODE == AppMode.UDP_STREAM`
- **THEN** 主窗口左侧加载 `LeftPanelWidget`，`_start_sdk_poll()` 被调用，`_start_render_timer()` 正常运行，行为与修改前完全一致

#### Scenario: CSV_PLAYBACK 模式启动
- **WHEN** `APP_MODE == AppMode.CSV_PLAYBACK`
- **THEN** 主窗口左侧加载 `CsvImportWidget`，`_start_sdk_poll()` 不被调用，主窗口持有 `CsvFrameReader` 引用，`_csv_timer` 在用户点击播放后启动

#### Scenario: 两种模式共用渲染逻辑
- **WHEN** `_latest_frame[0]` 被任何来源（UDP 轮询 或 CSV 定时器）更新
- **THEN** 16ms 渲染定时器 `_on_timer` 无差别地读取并渲染到 VTK 场景
