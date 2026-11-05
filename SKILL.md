---
name: cli-anything-motionglove
description: 控制 MotionGlove3DViewer / MotionGloveSDK 的命令行接口（CLI-Anything）。无头查询后端状态、打开或新建 CSV/UDP 工程、取 32/42 骨骼帧、端口诊断、导出 JSON/CSV/BVH。适用于 Agent 自动化与 CI，全程不创建 GUI 窗口。
---

# MotionGlove3DViewer CLI Skill

本 Skill 描述 MotionGloveSDK_python 的内置 CLI（`cli/` 包）。**业务逻辑只有一份**：
GUI 主程序 `motionGloveSDK_example3_3dView.py --cli ...`、独立入口
`python motionGloveSDK_cli.py ...`、`python -m cli ...` 三者共用同一实现，
均不 import VTK/PySide6，可用 `status` 的 `data.gui_loaded == false` 验证。

## 1. 调用方式

| 方式 | 命令形状 | 适用 |
|---|---|---|
| 独立入口（源码树/CI） | `python motionGloveSDK_cli.py --json <action> '<payload-json>'` | 最常用，无需打包 |
| 主程序内置分流 | `MotionGlove3DViewer.exe --cli --json <action> '<payload-json>'` | 分发包/单 exe |
| 子命令语法（人类） | `python motionGloveSDK_cli.py --json project open "C:\rec.csv"` | 交互式排查 |
| Python harness | `cli-anything-motionglove --raw status` | Agent，见第 6 节 |

- **机器协议**：`[cli_prefix, "--json", action, json.dumps(payload)]`；
  `<payload-json>` 必须是 JSON 对象（`{}` 可省略为无参数）。
- **子命令协议**：与机器协议最终归一到同一 `dispatch(action, payload)`。
- **REPL**：无参数启动、`--repl`、或只给 `--json` 时进入；
  `exit`/`quit`/EOF 退出，`help` 列命令，`json on`/`json off` 真正改变输出格式。
- 所有输出为 UTF-8；管道输入带 UTF-8 BOM 会被剥离，路径可用成对单/双引号。

## 2. 统一信封与 `--json`

所有命令都支持 `--json`（可放在任意位置）。**自动化一律加 `--json` 并只看
`ok`/`code`，不要解析人类文本。**

```json
{"ok": true, "code": 0, "message": "状态查询成功", "data": {}}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `ok` | bool | 命令是否成功 |
| `code` | int | 细分错误码，见第 5 节；成功恒为 0 |
| `message` | str | 人类可读结果/错误原因 |
| `data` | object | **永远存在**，可为空对象；字段命名见第 4 节 |

不加 `--json` 时输出人类可读文本（`[OK] ...` / `[FAIL] ...` + `code:` + `data:`）。
**进程退出码只区分成败**：成功 0、失败 1；细分错误一律看信封 `code`
（Windows 的 ExitProcess 是 UINT，负数退出码会被读成 4294967294）。

## 3. 命令表（project / run / export / status）

`必填` 列的「—」表示可省略（省略时按优先级 `--file/--input` > `payload.source` > 会话文件）。
单位与取值范围为硬校验，越界返回 `code=1`。

### status — 探测运行状态（永不因缺原生库而失败）

| 项 | 内容 |
|---|---|
| 语法 | `status` / `--json status '{}'` |
| 参数 | 无 |
| 支持 `--json` | 是 |
| `data` | `app`, `cli_version`, `protocol`, `backend`, `native_available`, `native_library`, `native_version`, `python`, `platform`, `gui_loaded`, `project`(会话摘要), `udp_port`, `udp_port_in_use`, `session_file`, `actions` |

### project — 工程/数据源管理

| 命令 | 描述 | 参数（必填 / 可选） | 支持 `--json` | `data` 主要字段 |
|---|---|---|---|---|
| `project open <path>` | 打开 CSV 并写入会话 | `path` 必填（或 `--file`）；`--actor` | 是 | `source`, `path`, `actor`, `total_frames`, `session_file` |
| `project open --udp` | 切换到 UDP 数据源 | `--udp` 必填；`--port` 1–65535（默认 5001）、`--actor` | 是 | `source`, `port`, `actor`, `session_file` |
| `project new <path>` | 新建 CSV 工程并设为当前会话 | `path` 必填；`--frames` 0–100000（默认 0，生成零位 T-pose）、`--actor`、`--force` | 是 | `source`, `path`, `total_frames`, `bytes`, `synthetic`, `session_file` |
| `project close` | 清空当前工程（保留 actor/port 偏好） | 无 | 是 | `closed`, `source`, `actor`, `port`, `session_file` |
| `project status` | 跨进程探测当前会话 | 无 | 是 | `source`, `path`, `actor`, `port`, `total_frames`, `updated_at`, `exists`, `file_size`, `opened`, `session_file` |

### run — 取帧 / 采集 / 诊断

| 命令 | 描述 | 参数（必填 / 可选） | 支持 `--json` | `data` 主要字段 |
|---|---|---|---|---|
| `run frame` | 取一帧（CSV 按索引，UDP 等第一帧） | `--index` ≥0（默认 0）、`--timeout` 0.05–60 s（默认 2）、`--summary`、`--file`/`--input`、`--source`、`--actor`、`--port` | 是 | `source`, `path`, `index`, `total_frames`, `frame_number`, `bone_count`, `frame`（完整帧）或 `summary` |
| `run frames` | 连续取帧（默认摘要） | `--start` ≥0、`--count` 1–10000（默认 10）、`--full`、`--file`/`--input`、`--source`、`--actor`、`--port`、`--timeout` | 是 | `source`, `start`, `total_frames`, `returned`, `full`, `frames[]` |
| `run listen` | UDP 采集 N 秒（无数据仍成功） | `--seconds` 0.05–60（默认 1）、`--port` 1–65535、`--actor` | 是 | `port`, `actor`, `frames`, `bone_count`, `actors`, `seconds`, `remote` |
| `run bones` | 42/32 骨骼索引映射 | 无 | 是 | `format`, `bone_count`, `bone_names[42]`, `short_names[42]`, `map_32_to_42[32]` |
| `run port-check` | UDP 端口占用诊断 | `--port` 1–65535（默认 5001） | 是 | `port`, `in_use`, `occupier[]`, `hint` |

### export — 导出数据

| 项 | 内容 |
|---|---|
| 语法 | `export <output>` / `--json export '{"output":"out.json"}'` |
| 参数 | `output` **必填**；`--format` json\|csv\|bvh（**省略时按扩展名推断**）；`--input`/`--file` 源 CSV；`--source`、`--actor`、`--index` ≥0、`--count` ≥1、`--all`、`--frame-rate` 0–1000 Hz（0=按时间戳推算）、`--port`、`--timeout` |
| 支持 `--json` | 是 |
| `data` | `output`, `format`, `source`, `input`, `actor`, `frames`, `bytes`, `frame_rate` |
| 行为 | 默认导出全部帧（`--index` 可只导一帧）；`.bvh` 复用 `src/csv_to_bvh.py`，要求至少 1 帧 |

**单位/坐标系约定**：`position` 单位米（m），`euler_degree` 单位度（°），
`quat_wxyz` 为 `[w,x,y,z]`；`skeleton_coordinate` 为 `relative`（相对父骨骼）或
`global`；42 段流 `bone_index` 0–41，32 段流经 `map_32_to_42` 映射到 42 段索引。

## 4. `data` schema 要点

- **帧对象**（`run.frame.data.frame` / `export .json` 的 `frames[]`）：
  `header`（`frame_number`, `avatar_name`, `skeleton_position`, `skeleton_attitude`,
  `skeleton_coordinate`, `channel_order`, 三个 skeleton_count, 两个 hand_gesture）、
  `skeletons[]`（`bone_index`, `bone_name`, `contains_*`, `position`,
  `quat_wxyz`, `euler_degree`）、`remote_ip`, `remote_port`, `bone_count`。
- **会话摘要**（`status.data.project` / `project.status`）：见上表；
  `opened=false` 时所有取帧/导出命令必须先 `project open` 或显式传 `--file`。
- 同一概念在全套命令里命名一致：`path` 恒为 CSV 工程路径、
  `output` 恒为导出目标、`input`/`file` 恒为显式输入源、
  `frames` 恒为帧数（整数，不是帧数组）。

## 5. 错误处理与错误码对照表

失败时 `ok=false`、`code` 非 0、进程退出码 1。`message` 为可操作的原因。
下表 `message` 均为本机实测输出（路径依本机而异）：

| `code` | 含义 | Agent 动作 | 实测 `message` 样例 |
|---|---|---|---|
| 0 | 成功 | 使用 `data` | `"状态查询成功"` |
| 1 | 参数/用法错误 | **改命令重试**，勿原样重跑 | `"未知命令：no.such.command；可用命令：status, project.open, ..."`；`"payload 不是合法 JSON：Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"`；`"port 不能小于 1，当前值：0"` |
| 2 | 会话状态不满足 | 先 `project open` 或传 `--file` | `"未打开工程；请先执行 project open <csv路径> / project open --udp，或在本命令中显式传入 --file / --source udp"` |
| 3 | IO 错误 | 创建目录或修正路径 | `"CSV 文件不存在：C:\definitely_missing_123.csv"`；`"输出目录不存在：C:\definitely_missing_dir_123（请先创建目录）"` |
| 4 | 数据解析错误 | 换有效 CSV 或有效帧索引 | `"CSV 文件中没有可用帧：...\empty.csv"` |
| 5 | 原生库不可用 | 编译 C++ SDK 或设置 `MOTIONGLOVE_NATIVE_LIB` | `"MotionGloveSDK 原生库不可用，无法监听 UDP；请执行 scripts\build_mgsdk_cpp.bat 或设置 MOTIONGLOVE_NATIVE_LIB"` |
| 6 | UDP 错误 | 检查端口/设备/超时 | `"等待 0.1 秒内未收到数据帧（端口 55099，数据流 Glove1）"` |
| 7 | 导出格式/目标不支持 | 改用 json/csv/bvh | `"不支持的导出格式：obj；可选 json, csv, bvh，或把输出文件扩展名写成 .json/.csv/.bvh"` |
| 8 | 内部错误 | 报告 `message` 中的异常类型 | `"TypeName: ..."` |

Python harness 另有协议层异常：`CliProtocolError`（stdout 不是合法信封 =
底层 CLI 版本不匹配）、`CliError`（起不来/超时/异常退出码）；业务失败信封
默认原样返回、不抛异常，便于 Agent 判定。

## 6. 可运行示例（输出均经实测）

### 示例 1：探测状态，确认没有加载 GUI

```bash
python motionGloveSDK_cli.py --json status
```

```json
{"ok": true, "code": 0, "message": "状态查询成功", "data": {"app": "MotionGlove3DViewer", "cli_version": "1.0.0", "protocol": "1.0", "backend": "native", "native_available": true, "native_library": ".../build/mgsdk_cpp/install/bin/MotionGloveSDK.dll", "native_version": 9, "python": "3.10.11", "platform": "win32", "gui_loaded": false, "project": {"source": null, "path": null, "actor": "Glove1", "port": 5001, "total_frames": 0, "exists": false, "opened": false, "session_file": ".../Temp/motionglove-cli/session.json"}, "udp_port": 5001, "udp_port_in_use": false, "actions": ["status", "project.open", "...", "export"]}}
```

（长路径与 `actions` 数组在文档中做了省略；其余字段与实测一致。）

### 示例 2：新建工程 → 取帧 → 导出（子命令语法）

```bash
python motionGloveSDK_cli.py --json project new "<TEMP>/demo.csv" --frames 3
python motionGloveSDK_cli.py --json run frame --summary
python motionGloveSDK_cli.py --json export "<TEMP>/out.csv"
```

```json
{"ok": true, "code": 0, "message": "已新建 CSV 工程，写入 3 帧示例数据", "data": {"source": "csv", "path": ".../demo.csv", "actor": "Glove1", "total_frames": 3, "bytes": 7064, "synthetic": true, "session_file": ".../Temp/motionglove-cli/session.json"}}
{"ok": true, "code": 0, "message": "取帧成功", "data": {"source": "csv", "path": ".../demo.csv", "actor": "Glove1", "port": 5001, "index": 0, "total_frames": 3, "frame_number": 1, "bone_count": 42, "summary": {"frame_number": 1, "avatar_name": "Glove1", "bone_count": 42, "contains_position": 1, "contains_attitude": 1, "remote": {"ip": "", "port": 0}, "first_joint": {"bone_index": 0, "bone_name": "RightHand", "position": [0.0, 0.0, 0.0]}}}}
{"ok": true, "code": 0, "message": "已导出 3 帧到 .../out.csv", "data": {"output": ".../out.csv", "format": "csv", "source": "csv", "input": ".../demo.csv", "actor": "Glove1", "frames": 3, "bytes": 7064, "frame_rate": null}}
```

### 示例 3：机器协议（harness 使用的调用形式）

```bash
python motionGloveSDK_cli.py --json project.open "{\"path\":\"<TEMP>/demo.csv\"}"
python motionGloveSDK_cli.py --json export "{\"output\":\"<TEMP>/out.bvh\",\"frame_rate\":60}"
```

```json
{"ok": true, "code": 0, "message": "已打开 CSV 工程，共 3 帧", "data": {"source": "csv", "path": ".../demo.csv", "actor": "Glove1", "total_frames": 3, "session_file": ".../Temp/motionglove-cli/session.json"}}
{"ok": true, "code": 0, "message": "已导出 3 帧到 .../out.bvh", "data": {"output": ".../out.bvh", "format": "bvh", "source": "csv", "input": ".../demo.csv", "actor": "Glove1", "frames": 3, "bytes": 9835, "frame_rate": 60.0}}
```

### 示例 4：错误路径（改命令重试）

```bash
python motionGloveSDK_cli.py --json run.frame '{}'     # 先 project.close
```

```json
{"ok": false, "code": 2, "message": "未打开工程；请先执行 project open <csv路径> / project open --udp，或在本命令中显式传入 --file / --source udp", "data": {}}
```

进程退出码为 1；`code=2` 提示应先执行 `project open`。

### 示例 5：REPL（管道输入 + BOM + json 开关）

```bash
printf '\xef\xbb\xbfjson on\nstatus\nexit\n' | python motionGloveSDK_cli.py --repl
# 输出含 "json=on"、一行 JSON 信封，退出码 0
```

### 示例 6：Python harness

```bash
pip install -e agent-harness/cli_anything/motionglove
cli-anything-motionglove --raw status
cli-anything-motionglove --raw project open "<TEMP>/demo.csv"
cli-anything-motionglove --raw run frame --index 0 --summary
cli-anything-motionglove repl
```

`--raw` 输出原始信封；缺省输出 `OK status: 状态查询成功 (code=0)` 加字段摘要。

## 7. 部署目录布局

```
<install-dir>/
├── MotionGlove3DViewer.exe        # 主程序；加 --cli 进 CLI 模式
├── _internal/                     # PyInstaller 运行库
├── SKILL.md                       # 唯一一份（与 exe 同层）
└── agent-harness/
    └── cli_anything/motionglove/
        ├── _cli.py                # Click 入口
        ├── utils/backend.py       # subprocess 协议（纯函数 build_argv）
        ├── utils/repl_skin.py     # 薄 REPL
        ├── setup.py               # pip install -e
        └── tests/                 # mock 单测 + e2e
```

源码树对应：`SKILL.md`（根，唯一一份）、`cli/`（CLI 实现）、
`motionGloveSDK_cli.py`（独立入口）、`agent-harness/`、
`scripts/lib/sync_agent_harness.py` 与 `scripts/sync_agent_harness.bat`。
`buildDeploy.bat` 在 PyInstaller 成功后自动调用同步脚本；也可手动执行
`scripts\sync_agent_harness.bat [目标目录]` 或
`python scripts/lib/sync_agent_harness.py --dist <目录> [--check]`。
同步会排除 `__pycache__/`、`.pytest_cache/`、`*.egg-info/`、`*.pyc`。

harness 的二进制定位顺序：`MOTIONGLOVE_CLI_BIN` > 安装目录同级 exe >
仓库 `dist/` 构建产物 > PATH > 源码树 `python motionGloveSDK_cli.py`。
exe 候选会先跑一次 `--json status` 探测，旧版 GUI exe（无 `--cli` 分流）
被自动跳过。部署目录里 harness 靠相对位置自动找到 exe，无需配置。

## 8. 注意事项

1. **导出目录必须已存在**，CLI 不会自动创建；不存在的目录返回 `code=3`。
2. `project open/new` 只改会话文件 `%TEMP%\motionglove-cli\session.json`
   （POSIX 为 `$TMPDIR/motionglove-cli/session.json`），跨进程共享；
   用 `project status` 探测，`project close` 清理。
3. **UDP 监听不跨进程保持**：`run.listen` / `run.frame --source udp` 在单条
   命令进程内完成「监听 → 取帧 → 关闭」；`project open --udp` 只是记录端口偏好。
4. **CSV 路径完全不依赖 C++ 原生库**，可在无硬件/无原生库的 CI 中跑通；
   UDP 路径需要 `MotionGloveSDK.dll` / `libMotionGloveSDK.so`。
5. BVH 需要至少一帧数据；`--frame-rate` 省略时按 CSV 时间戳推算，失败回退 60 Hz。
6. WIN32 子系统 exe 从控制台启动时，CLI 自动 `AttachConsole` 接管父控制台、
   代码页切 UTF-8；标准输出已被重定向（`>file`、管道）时按 OS 标准句柄
   重建流，因此 subprocess 管道与文件重定向都能拿到信封。
   需要直观控制台输出可用 `buildDeploy.bat --console` 打包。
   若分发目录里仍是**旧版 exe**（未含 `--cli` 分流），harness 探测会失败并
   抛 `CliProtocolError`（stdout 不是合法信封）；重新执行 `buildDeploy.bat` 生成新
   exe，或改用源码树 `python motionGloveSDK_cli.py`。
7. `--cli` 分流位于主程序所有 VTK/PySide6 导入之前；普通启动行为不变。
8. 底层 SDK/解析器的诊断输出被重定向到 stderr，**stdout 永远只有一行信封**。
