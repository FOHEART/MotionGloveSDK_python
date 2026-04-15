## Context

当前主窗口 `MotionGloveMainWindow` 的数据驱动层完全基于 UDP：后台线程 `_poll` 通过 `motionGloveSDK` 消费 `queue.Queue`，将最新 `GloveFrame` 写入 `_latest_frame[0]`，16ms 定时器 `_on_timer` 读取并渲染。

CSV 回放模式需要替换数据来源（文件逐行 → `GloveFrame`）但复用完全相同的 VTK 渲染管线（`_joint_actors`、`_link_actors`、`_on_timer` 中对 actor 的更新逻辑）。两种模式的差异仅在于：数据从哪里来、左侧面板展示什么、是否启动 UDP 后台线程。

## Goals / Non-Goals

**Goals:**
- 顶层 `AppMode` 枚举 + `APP_MODE` 常量切换启动模式（改常量即切换，无需命令行参数）
- CSV 回放模式：左侧 `CsvImportWidget`，文件选择 + 帧率选择 + 播放控制
- `src/csv_frame_reader.py`：独立解析模块，`CsvFrameReader` 类，按行读取 CSV → `GloveFrame`，供多种模式复用
- `_on_timer` 渲染逻辑在两种模式下完全共用（只写 `_latest_frame[0]`，定时器统一读取）
- 右侧 `DrawConfigWidget` 两种模式均存在且可用

**Non-Goals:**
- 不实现进度条 / 时间轴拖拽 scrubbing
- 不实现倒放
- 不实现 CSV 录制功能（仅回放）
- 不支持多文件拼接播放

## Decisions

### D1：`AppMode` 枚举放在主脚本顶层，`APP_MODE` 为全局常量
```python
class AppMode(enum.Enum):
    UDP_STREAM   = "udp"
    CSV_PLAYBACK = "csv"

APP_MODE = AppMode.UDP_STREAM   # ← 修改此行切换模式
```
**Alternative**: 命令行参数 `--mode csv` — 增加 argparse 复杂度，顶层常量对调试更直接。

### D2：`CsvFrameReader` 封装为迭代器类，不是生成器函数
`CsvFrameReader(path)` 持有文件内所有行（`list[str]`）+ 当前索引，支持 `next_frame() -> GloveFrame | None`、`reset()`、`at_end` 属性。  
**Why**: 回放需要随机重置到第 0 帧（重置按钮），生成器不支持 `reset()`；预加载全部行避免播放时 IO 抖动。  
**Alternative**: 每次重置重新打开文件 — 文件句柄管理更复杂，且大文件每次重新读取有延迟。

### D3：CSV 文件格式（已确认）
文件第 1 行为列名表头（跳过）。第 2 行起，每行格式为：

```
<header tokens（空格分隔）>,<骨骼数据（逗号分隔）>
```

示例：`Glove1 time 2026-04-06 22:10:04.298 pos euler ZXY relative fn 496  subpackage 1/1,0.1,0,...`

解析方式：以第一个逗号为分割点，左侧为 header 字符串（`.split()` 得到 tokens），右侧为 body CSV 字符串。header tokens 和 body 分别传给现有 `parse_header_tokens` 和 `decode_glove_csv`。每行 header 均独立解析（含 fn、timestamp），无需跨行复用。

### D4：播放引擎使用主线程 `QTimer`，不启动额外线程
CSV 回放无需后台 IO 线程（数据已预加载）。用专用 `QTimer _csv_timer` 按帧率触发，每次回调写 `_latest_frame[0]`，现有 `_on_timer`（16ms）负责渲染。`_csv_timer` 间隔 = `round(1000 / fps)`。

### D5：`CsvImportWidget` 纯代码构建（不用 `.ui` 文件）
控件结构简单（QLineEdit + 4个按钮 + QComboBox），与 `DrawConfigWidget` 保持一致风格。`.ui` 文件适合复杂布局，此处不必要。

### D6：帧率选择器使用 `QComboBox`（10 / 24 / 30 / 60 Hz）
显示人类可读的"60 Hz"文本，内部映射到 `round(1000/fps)` 毫秒。默认选中 60 Hz。

## Risks / Trade-offs

- **CSV 行数可能很大（>100k 行）**: 预加载全部行为 `list[str]`，每行约 200 字节，10 万行约 20 MB，可接受。
- **CSV header 格式与 UDP 包 header 不同**: UDP 包的 header 在 `GloveFrameAssembler` 里被单独提取；CSV 文件每行是 body only（不含分包头）还是完整 CSV 行（含 actor/fn/...）需在实现前确认。设计假设：CSV 每行 = UDP 完整 CSV 行（含 header tokens），与 `rawReceiver.py` 的录制格式一致。
- **`_on_timer` 在 CSV 模式下处理 `drop_event`**: `_drop_event` 只由 UDP 的 `_poll` 写入，CSV 模式下始终为 `None`，状态栏不会误显示丢帧警告 — 无需额外处理。
