## ADDED Requirements

### Requirement: DrawConfig dataclass
系统 SHALL 定义 `DrawConfig` dataclass，包含字段：`joint_radius: float`、`joint_color: tuple[float,float,float]`、`link_width: float`、`link_color: tuple[float,float,float]`、`axis_length: float`，并提供 `default()` 类方法返回默认值。

#### Scenario: 默认值
- **WHEN** 调用 `DrawConfig.default()`
- **THEN** 返回 `joint_radius=0.005`、`joint_color=(1.0,1.0,1.0)`、`link_width=2.0`、`link_color=(0.7,0.7,0.7)`、`axis_length=0.010`

### Requirement: 配置导出为 JSON
系统 SHALL 提供 `save_config(config: DrawConfig, path: str) -> None`，将配置序列化为 JSON 文件。

#### Scenario: 成功保存
- **WHEN** 调用 `save_config(cfg, "/path/to/config.json")`
- **THEN** 目标文件被创建/覆盖，内容为合法 JSON，包含所有 DrawConfig 字段

#### Scenario: 路径无效时抛出异常
- **WHEN** 传入无效路径（如权限不足目录）
- **THEN** 函数抛出 `OSError`，不静默失败

### Requirement: 从 JSON 加载配置
系统 SHALL 提供 `load_config(path: str) -> DrawConfig`，从 JSON 文件反序列化为 `DrawConfig`。

#### Scenario: 成功加载
- **WHEN** 调用 `load_config("/path/to/config.json")`（文件由 `save_config` 生成）
- **THEN** 返回与保存时相同字段值的 `DrawConfig`

#### Scenario: 文件不存在时抛出异常
- **WHEN** 传入不存在的路径
- **THEN** 函数抛出 `FileNotFoundError`

#### Scenario: JSON 字段缺失时使用默认值填充
- **WHEN** JSON 文件缺少部分字段（旧版本兼容）
- **THEN** 缺失字段使用 `DrawConfig.default()` 对应值填充，不抛出异常
