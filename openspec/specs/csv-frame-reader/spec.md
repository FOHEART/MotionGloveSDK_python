## ADDED Requirements

### Requirement: CsvFrameReader 类
`src/csv_frame_reader.py` SHALL 定义 `CsvFrameReader` 类，接受 CSV 文件路径，构造时预加载全部行到内存（`list[str]`），支持按索引顺序逐帧读取。

#### Scenario: 构造时预加载文件
- **WHEN** `CsvFrameReader("/path/to/file.csv")` 被实例化
- **THEN** 文件全部行读入内存，`total_frames` 属性返回总行数，当前索引为 0

#### Scenario: 文件不存在时抛出 FileNotFoundError
- **WHEN** 传入不存在的路径
- **THEN** 构造函数抛出 `FileNotFoundError`

### Requirement: next_frame 接口
`CsvFrameReader` SHALL 提供 `next_frame() -> GloveFrame | None`，返回当前索引对应的 `GloveFrame` 并将索引加 1；若已到末尾则返回 `None` 且 `at_end` 为 `True`。

#### Scenario: 正常读取帧
- **WHEN** 调用 `next_frame()` 且索引未超出范围
- **THEN** 返回解析后的 `GloveFrame`，`current_index` 加 1

#### Scenario: 已到末帧后调用
- **WHEN** `at_end` 为 `True` 时调用 `next_frame()`
- **THEN** 返回 `None`，`current_index` 不变

### Requirement: reset 与 at_end 接口
`CsvFrameReader` SHALL 提供 `reset()` 方法将索引归零，以及只读属性 `at_end: bool` 和 `total_frames: int`。

#### Scenario: 重置后可重新播放
- **WHEN** 调用 `reset()`
- **THEN** `current_index` 归 0，`at_end` 为 `False`，下次 `next_frame()` 返回第一帧

### Requirement: CSV 行解析使用现有 decode_glove_csv
`CsvFrameReader` SHALL 调用 `src.decode_glove_csv.decode_glove_csv()` 解析每一行；第一行解析为 header tokens（使用 `parse_header_tokens`），后续行复用同一 header。

#### Scenario: 解析结果类型正确
- **WHEN** CSV 文件由 MotionGlove 软件导出（每行格式与 UDP 包 CSV body 相同）
- **THEN** `next_frame()` 返回的对象类型为 `GloveFrame`，含 32 个 `SingleSkeleton`
