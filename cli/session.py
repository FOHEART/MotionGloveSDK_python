"""
@file  session.py
@brief CLI 会话状态：固定路径 JSON 文件，跨进程共享「当前打开的工程」。
@details
每条命令默认是一个独立进程，因此状态必须落盘。会话文件位于
tempfile.gettempdir()/motionglove-cli/session.json
（Windows 即 %TEMP%\\motionglove-cli\\session.json）。
写入采用「临时文件 + os.replace」原子替换，避免并发命令读到半截 JSON。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

SESSION_DIR = Path(tempfile.gettempdir()) / "motionglove-cli"
SESSION_FILE = SESSION_DIR / "session.json"

DEFAULT_ACTOR = "Glove1"
DEFAULT_PORT = 5001

_DEFAULTS: dict[str, Any] = {
    "source": None,       # "csv" | "udp" | None
    "path": None,         # CSV 绝对路径（source=csv 时有效）
    "actor": DEFAULT_ACTOR,
    "port": DEFAULT_PORT,
    "total_frames": 0,
    "updated_at": "",
}


def _defaults() -> dict[str, Any]:
    return dict(_DEFAULTS)


def load() -> dict[str, Any]:
    """@brief 读取会话；文件缺失/损坏时返回默认会话（不抛异常）。

    @return 会话字典（字段恒齐全）。
    """
    session = _defaults()
    try:
        raw = json.loads(SESSION_FILE.read_text(encoding="utf-8-sig"))
        if isinstance(raw, dict):
            session.update({k: v for k, v in raw.items() if k in _DEFAULTS})
    except (OSError, ValueError):
        pass
    return session


def _atomic_write(session: dict[str, Any]) -> None:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SESSION_DIR / f"session.{os.getpid()}.tmp"
    tmp.write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, SESSION_FILE)


def save(**fields: Any) -> dict[str, Any]:
    """@brief 更新并持久化会话。

    @param fields 要写入的字段（未知字段忽略）。
    @return 更新后的会话字典。
    @exception OSError 会话目录不可写。
    """
    session = load()
    session.update({k: v for k, v in fields.items() if k in _DEFAULTS})
    session["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _atomic_write(session)
    return session


def close() -> dict[str, Any]:
    """@brief 关闭当前工程（保留 actor/port 偏好，清空 source/path）。

    @return 重置后的会话字典。
    """
    return save(source=None, path=None, total_frames=0)


def summary() -> dict[str, Any]:
    """@brief 返回供 status / project status 使用的会话摘要。

    @details 附加 exists / file_size / session_file 等派生字段，
             让 Agent 无需另行探测即可知道会话是否仍然有效。
    @return 会话摘要字典。
    """
    session = load()
    path = session.get("path")
    exists = bool(path) and Path(str(path)).is_file()
    size = Path(str(path)).stat().st_size if exists else 0
    return {
        "source": session.get("source"),
        "path": path,
        "actor": session.get("actor", DEFAULT_ACTOR),
        "port": session.get("port", DEFAULT_PORT),
        "total_frames": session.get("total_frames", 0),
        "updated_at": session.get("updated_at", ""),
        "exists": exists,
        "file_size": size,
        "session_file": str(SESSION_FILE),
        "opened": session.get("source") is not None,
    }
