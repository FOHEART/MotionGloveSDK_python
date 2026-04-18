## ADDED Requirements

### Requirement: DrawConfig 包含 blender_exe 字段
`DrawConfig` dataclass SHALL 新增 `blender_exe: str = ""` 字段；`save_config` 将其写入 JSON；`load_config` 读取时若键缺失则返回空字符串。

#### Scenario: 保存含 blender_exe 的配置
- **WHEN** `save_config` 被调用且 `config.blender_exe` 非空
- **THEN** 输出的 JSON 文件包含 `"blender_exe"` 键及对应路径字符串

#### Scenario: 加载旧配置文件（无 blender_exe 键）
- **WHEN** `load_config` 读取一个不含 `blender_exe` 键的 JSON 文件
- **THEN** 返回的 `DrawConfig.blender_exe` 为空字符串 `""`
