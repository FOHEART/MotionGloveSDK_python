## ADDED Requirements

### Requirement: CsvImportWidget 接受 config_path 构造参数
`CsvImportWidget.__init__` SHALL 接受可选参数 `config_path: str = ""`，用于定位 `config.json`；缺省时使用工程根目录下的 `config.json`（`Path(__file__).parent.parent / "config.json"`）。

#### Scenario: 未传入 config_path 时使用默认路径
- **WHEN** `CsvImportWidget()` 不传 `config_path`
- **THEN** 从工程根目录 `config.json` 读取 Blender 路径

#### Scenario: 传入 config_path 时使用指定路径
- **WHEN** `CsvImportWidget(config_path="/custom/config.json")` 实例化
- **THEN** 从指定路径读取和写入 Blender 路径
