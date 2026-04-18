## ADDED Requirements

### Requirement: 文件选择与路径显示
`CsvImportWidget` SHALL 包含一个 `QLineEdit`（只读）显示当前选中文件的完整路径，以及一个"选择文件"按钮，点击后弹出 `QFileDialog` 过滤 `*.csv` 文件。

#### Scenario: 用户选择文件后路径更新
- **WHEN** 用户点击"选择文件"并在对话框中确认选择
- **THEN** `QLineEdit` 显示所选文件的完整绝对路径，`CsvFrameReader` 使用该文件预加载所有行

#### Scenario: 用户取消选择
- **WHEN** 用户点击"选择文件"后取消对话框
- **THEN** `QLineEdit` 内容不变，当前文件不变

### Requirement: 帧率选择器
`CsvImportWidget` SHALL 包含一个 `QComboBox`，选项为 10 Hz / 24 Hz / 30 Hz / 60 Hz，默认选中 60 Hz。

#### Scenario: 切换帧率
- **WHEN** 用户在下拉框中选择新帧率
- **THEN** 若当前正在播放，`_csv_timer` 间隔立即更新为 `round(1000 / fps)` ms

### Requirement: 播放/暂停按钮
`CsvImportWidget` SHALL 包含一个按钮，初始文字为"开始播放"，点击后文字变为"暂停播放"并开始播放；再次点击暂停播放，文字恢复为"开始播放"（继续）。

#### Scenario: 点击开始播放
- **WHEN** 按钮文字为"开始播放"，用户点击
- **THEN** 按钮文字变为"暂停播放"，`_csv_timer` 启动，开始按帧率推进

#### Scenario: 点击暂停播放
- **WHEN** 按钮文字为"暂停播放"，用户点击
- **THEN** 按钮文字变为"开始播放"，`_csv_timer` 停止，当前帧画面保持不变

### Requirement: 重置按钮
`CsvImportWidget` SHALL 包含一个"重置"按钮，点击后停止播放并跳回第一帧。

#### Scenario: 点击重置
- **WHEN** 用户点击"重置"（无论当前是否正在播放）
- **THEN** `_csv_timer` 停止，`CsvFrameReader.reset()` 被调用，第一帧渲染到 VTK 场景，播放按钮文字恢复为"开始播放"

### Requirement: 未选择文件时播放按钮禁用
`CsvImportWidget` SHALL 在未选择有效文件时，禁用播放/暂停和重置按钮（`setEnabled(False)`）。

#### Scenario: 首次启动无文件
- **WHEN** 程序启动，尚未选择文件
- **THEN** 播放/暂停按钮和重置按钮均为禁用状态

#### Scenario: 选择文件后按钮可用
- **WHEN** 用户成功选择并加载一个 CSV 文件
- **THEN** 播放/暂停按钮和重置按钮变为可用

### Requirement: CsvImportWidget 接受 config_path 构造参数
`CsvImportWidget.__init__` SHALL 接受可选参数 `config_path: str = ""`，用于定位 `config.json`；缺省时使用工程根目录下的 `config.json`（`Path(__file__).parent.parent / "config.json"`）。

#### Scenario: 未传入 config_path 时使用默认路径
- **WHEN** `CsvImportWidget()` 不传 `config_path`
- **THEN** 从工程根目录 `config.json` 读取 Blender 路径

#### Scenario: 传入 config_path 时使用指定路径
- **WHEN** `CsvImportWidget(config_path="/custom/config.json")` 实例化
- **THEN** 从指定路径读取和写入 Blender 路径
