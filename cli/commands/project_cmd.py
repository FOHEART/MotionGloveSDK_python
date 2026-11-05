"""
@file  project_cmd.py
@brief project 命令组：open / new / close / status。
@details 会话显式落盘到 %TEMP%\\motionglove-cli\\session.json，open/close
         只改这个文件；其余命令跨进程读取，Agent 可用 project status 探测状态。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.csv_frame_reader import CsvFrameReader

from .. import session
from ..envelope import IoError, ParseError, UsageError
from ..frames import DEFAULT_ACTOR, DEFAULT_PORT, frames_to_csv, synthetic_frames
from ..parser import as_bool, as_int

Result = tuple[dict[str, Any], str]


def _path_arg(payload: dict[str, Any], *, what: str) -> str:
    """@brief 取路径参数（兼容 path / file / output 等别名）。"""
    for key in ("path", "file", "output", "out"):
        value = payload.get(key)
        if value:
            return str(value)
    raise UsageError(f"缺少必填参数 path（{what}）")


def project_open(payload: dict[str, Any]) -> Result:
    """@brief 打开 CSV 工程或切换到 UDP 数据源。

    @param payload path/file=CSV 路径、udp=true 或 source=udp 切 UDP、
                   port=UDP 端口、actor=数据流名称。
    @return (data, message)。
    @exception UsageError 缺路径或参数非法。
    @exception IoError 文件不存在。
    @exception ParseError CSV 解析失败。
    """
    actor = str(payload.get("actor") or DEFAULT_ACTOR)
    is_udp = as_bool(payload.get("udp")) or str(payload.get("source") or "").lower() == "udp"

    if is_udp:
        port = as_int(payload.get("port"), DEFAULT_PORT, name="port", lo=1, hi=65535)
        session.save(source="udp", path=None, port=port, actor=actor, total_frames=0)
        data = {
            "source": "udp",
            "port": port,
            "actor": actor,
            "session_file": str(session.SESSION_FILE),
        }
        return data, f"已切换到 UDP 数据源（端口 {port}）"

    raw = _path_arg(payload, what="CSV 文件路径")
    path = Path(raw).expanduser().resolve()
    if not path.is_file():
        raise IoError(f"CSV 文件不存在：{path}")
    try:
        total = CsvFrameReader(str(path)).total_frames
    except FileNotFoundError:
        raise IoError(f"CSV 文件不存在：{path}") from None
    except Exception as exc:
        raise ParseError(f"CSV 解析失败：{exc}") from exc

    session.save(source="csv", path=str(path), actor=actor, total_frames=total)
    data = {
        "source": "csv",
        "path": str(path),
        "actor": actor,
        "total_frames": total,
        "session_file": str(session.SESSION_FILE),
    }
    return data, f"已打开 CSV 工程，共 {total} 帧"


def project_new(payload: dict[str, Any]) -> Result:
    """@brief 新建 CSV 工程（可生成零位 T-pose 示例帧）并设为当前会话。

    @param payload path/file=输出路径、frames=示例帧数（默认 0）、
                   actor=数据流名称、force=true 允许覆盖已有文件。
    @return (data, message)。
    @exception IoError 目录不存在、文件已存在或写出失败。
    """
    path = Path(_path_arg(payload, what="新建 CSV 文件路径")).expanduser().resolve()
    if not path.parent.is_dir():
        raise IoError(f"输出目录不存在：{path.parent}（请先创建目录）")
    if path.exists() and not as_bool(payload.get("force")):
        raise IoError(f"文件已存在：{path}；如要覆盖请加 --force")

    count = as_int(payload.get("frames"), 0, name="frames", lo=0, hi=100000)
    actor = str(payload.get("actor") or DEFAULT_ACTOR)
    frames = synthetic_frames(count, actor)
    try:
        path.write_text(frames_to_csv(frames, actor), encoding="utf-8")
    except OSError as exc:
        raise IoError(f"写出 CSV 失败：{exc}") from exc

    session.save(source="csv", path=str(path), actor=actor, total_frames=count)
    data = {
        "source": "csv",
        "path": str(path),
        "actor": actor,
        "total_frames": count,
        "bytes": path.stat().st_size,
        "synthetic": True,
        "session_file": str(session.SESSION_FILE),
    }
    return data, f"已新建 CSV 工程，写入 {count} 帧示例数据"


def project_close(payload: dict[str, Any]) -> Result:
    """@brief 关闭当前工程（清空 source/path，保留 actor/port 偏好）。

    @param payload 未使用。
    @return (data, message)。
    """
    state = session.close()
    data = {
        "closed": True,
        "source": None,
        "actor": state.get("actor", DEFAULT_ACTOR),
        "port": state.get("port", DEFAULT_PORT),
        "session_file": str(session.SESSION_FILE),
    }
    return data, "已关闭当前工程"


def project_status(payload: dict[str, Any]) -> Result:
    """@brief 返回当前会话摘要（跨进程可探测）。

    @param payload 未使用。
    @return (data, message)。
    """
    return session.summary(), "会话状态查询成功"
