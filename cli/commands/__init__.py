"""
@file  commands/__init__.py
@brief CLI 命令包：仅存放命令元信息，不导入具体命令实现（避免循环导入）。
"""

from __future__ import annotations

# 机器调用协议（--json <action> '<payload-json>'）支持的全部 action。
# 与 cli_runner.HANDLERS、SKILL.md 的命令表保持一致。
ACTION_NAMES: tuple[str, ...] = (
    "status",
    "project.open",
    "project.new",
    "project.close",
    "project.status",
    "run.frame",
    "run.frames",
    "run.listen",
    "run.bones",
    "run.port-check",
    "export",
)

# 子命令语法 → action 的映射（(一级命令, 二级命令) → action）。
SUBCOMMAND_ACTIONS: dict[tuple[str, str], str] = {
    ("status", ""): "status",
    ("project", "open"): "project.open",
    ("project", "new"): "project.new",
    ("project", "close"): "project.close",
    ("project", "status"): "project.status",
    ("run", "frame"): "run.frame",
    ("run", "frames"): "run.frames",
    ("run", "listen"): "run.listen",
    ("run", "bones"): "run.bones",
    ("run", "port-check"): "run.port-check",
    ("export", ""): "export",
}

# 每个子命令允许的选项（value=单值 / multi=可重复 / flag=布尔开关）。
OPTION_SPECS: dict[tuple[str, str], dict[str, str]] = {
    ("status", ""): {},
    ("project", "open"): {
        "--file": "value", "--actor": "value", "--port": "value",
        "--udp": "flag", "--source": "value",
    },
    ("project", "new"): {
        "--file": "value", "--actor": "value", "--frames": "value",
        "--force": "flag",
    },
    ("project", "close"): {},
    ("project", "status"): {},
    ("run", "frame"): {
        "--file": "value", "--input": "value", "--source": "value",
        "--actor": "value", "--index": "value", "--port": "value",
        "--timeout": "value", "--summary": "flag", "--full": "flag",
    },
    ("run", "frames"): {
        "--file": "value", "--input": "value", "--source": "value",
        "--actor": "value", "--start": "value", "--count": "value",
        "--port": "value", "--timeout": "value", "--full": "flag",
    },
    ("run", "listen"): {
        "--port": "value", "--actor": "value", "--seconds": "value",
    },
    ("run", "bones"): {},
    ("run", "port-check"): {"--port": "value"},
    ("export", ""): {
        "--format": "value", "--input": "value", "--file": "value",
        "--source": "value", "--actor": "value", "--index": "value",
        "--count": "value", "--port": "value", "--timeout": "value",
        "--frame-rate": "value", "--all": "flag",
    },
}
