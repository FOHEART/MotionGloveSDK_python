"""
@file  run_cmd.py
@brief run 命令组：frame / frames / listen / bones / port-check。
@details 源解析规则（优先级）：显式 --file/--input > payload.source > 会话。
         CSV 路径完全不依赖原生库；UDP 路径在单进程内闭环监听/取帧/关闭。
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from .. import session
from ..envelope import IoError, StateError, UdpError
from ..frames import (
    DEFAULT_ACTOR,
    DEFAULT_PORT,
    bone_layout,
    collect_udp_frames,
    frame_to_dict,
    load_csv_frames,
    summarize,
)
from ..parser import as_bool, as_float, as_int

Result = tuple[dict[str, Any], str]


def resolve_source(payload: dict[str, Any]) -> tuple[str, str | None, int, str]:
    """@brief 解析本次命令的数据源（CSV 文件 / UDP 端口）。

    @param payload 命令参数字典。
    @return (source, csv_path, port, actor)；source 为 "csv" 或 "udp"。
    @exception StateError 既未打开工程也未显式指定源。
    @exception IoError 会话指向的 CSV 文件已不存在。
    @exception UsageError source 值非法或端口越界。
    """
    state = session.load()
    explicit_file = payload.get("file") or payload.get("input")
    raw_source = str(payload.get("source") or "").strip().lower()

    if raw_source == "udp":
        source = "udp"
    elif raw_source == "csv" or explicit_file:
        source = "csv"
    elif state.get("source") in ("csv", "udp"):
        source = str(state["source"])
    else:
        raise StateError(
            "未打开工程；请先执行 project open <csv路径> / project open --udp，"
            "或在本命令中显式传入 --file / --source udp"
        )

    actor = str(payload.get("actor") or state.get("actor") or DEFAULT_ACTOR)
    port = as_int(payload.get("port"), int(state.get("port") or DEFAULT_PORT),
                  name="port", lo=1, hi=65535)

    if source == "udp":
        return "udp", None, port, actor

    path = str(explicit_file or state.get("path") or "")
    if not path:
        raise StateError("当前会话不是 CSV 工程；请用 project open 打开 CSV 或传 --file")
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise IoError(f"CSV 文件不存在：{resolved}")
    return "csv", str(resolved), port, actor


def _udp_seconds(payload: dict[str, Any], default: float) -> float:
    """@brief 取 UDP 等待时长（兼容 timeout / seconds 两种键名）。"""
    value = payload.get("timeout", payload.get("seconds"))
    return as_float(value, default, name="timeout", lo=0.05, hi=60.0)


def run_frame(payload: dict[str, Any]) -> Result:
    """@brief 取一帧：CSV 按 --index 定位，UDP 等待 --timeout 秒内的第一帧。

    @param payload index=帧索引、timeout/seconds=等待秒数、summary=true 只回摘要、
                   file/source/actor/port 见 resolve_source()。
    @return (data, message)。
    @exception UdpError UDP 等待超时未收到帧。
    """
    source, path, port, actor = resolve_source(payload)
    index = as_int(payload.get("index"), 0, name="index", lo=0)

    if source == "csv":
        assert path is not None
        frames, total = load_csv_frames(path, index, 1)
        info: dict[str, Any] = {"index": index, "total_frames": total}
    else:
        seconds = _udp_seconds(payload, 2.0)
        frames, udp_info = collect_udp_frames(port, actor, seconds, first_only=True)
        if not frames:
            raise UdpError(
                f"等待 {seconds} 秒内未收到数据帧（端口 {port}，数据流 {actor}）",
                data={"port": port, "actor": actor, "timeout": seconds},
            )
        info = {"index": 0, "total_frames": len(frames), "udp": udp_info}

    frame = frames[0]
    data: dict[str, Any] = {
        "source": source,
        "path": path,
        "actor": actor,
        "port": port,
        **info,
        "frame_number": int(frame.header.frame_number),
        "bone_count": len(frame.skeletons),
    }
    if as_bool(payload.get("summary")):
        data["summary"] = summarize(frame)
    else:
        data["frame"] = frame_to_dict(frame)
    return data, "取帧成功"


def run_frames(payload: dict[str, Any]) -> Result:
    """@brief 连续取多帧（默认输出摘要，--full 输出完整骨骼数组）。

    @param payload start=起始索引、count=帧数（默认 10）、full=true 输出完整帧。
    @return (data, message)。
    """
    source, path, port, actor = resolve_source(payload)
    start = as_int(payload.get("start", payload.get("index")), 0, name="start", lo=0)
    count = as_int(payload.get("count"), 10, name="count", lo=1, hi=10000)
    full = as_bool(payload.get("full"))

    if source == "csv":
        assert path is not None
        frames, total = load_csv_frames(path, start, count)
        extra: dict[str, Any] = {"start": start, "total_frames": total}
    else:
        seconds = _udp_seconds(payload, 1.0)
        frames, udp_info = collect_udp_frames(port, actor, seconds)
        extra = {"start": 0, "total_frames": len(frames), "udp": udp_info}
        frames = frames[:count]

    data = {
        "source": source,
        "path": path,
        "actor": actor,
        "port": port,
        **extra,
        "returned": len(frames),
        "full": full,
        "frames": [frame_to_dict(f) if full else summarize(f) for f in frames],
    }
    return data, f"取回 {len(frames)} 帧"


def run_listen(payload: dict[str, Any]) -> Result:
    """@brief UDP 采集若干秒（无数据不算错误，frames=0 仍为成功信封）。

    @param payload port=UDP 端口、seconds=采集秒数、actor=数据流名称。
    @return (data, message)。
    """
    state = session.load()
    port = as_int(payload.get("port"), int(state.get("port") or DEFAULT_PORT),
                  name="port", lo=1, hi=65535)
    actor = str(payload.get("actor") or state.get("actor") or DEFAULT_ACTOR)
    raw_seconds = payload.get("seconds", payload.get("timeout"))
    seconds = as_float(raw_seconds, 1.0, name="seconds", lo=0.05, hi=60.0)

    frames, info = collect_udp_frames(port, actor, seconds)
    data = {
        "source": "udp",
        "port": port,
        "actor": actor,
        "frames": len(frames),
        "bone_count": len(frames[0].skeletons) if frames else 0,
        **info,
    }
    message = (
        f"UDP 采集完成，收到 {len(frames)} 帧"
        if frames else "UDP 采集完成，未收到数据帧（设备未发送或端口无数据）"
    )
    return data, message


def run_bones(payload: dict[str, Any]) -> Result:
    """@brief 查询 42/32 骨骼名称与索引映射表。

    @param payload 未使用。
    @return (data, message)。
    """
    return bone_layout(), "骨骼索引映射查询成功"


def _port_in_use(port: int) -> bool:
    """@brief 用 UDP bind 试探端口是否已被占用。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", port))
        return False
    except OSError:
        return True
    finally:
        sock.close()


def run_port_check(payload: dict[str, Any]) -> Result:
    """@brief 诊断 UDP 端口占用（不启动 SDK 监听）。

    @param payload port=UDP 端口。
    @return (data, message)。
    """
    state = session.load()
    port = as_int(payload.get("port"), int(state.get("port") or DEFAULT_PORT),
                  name="port", lo=1, hi=65535)
    occupier: list[str] = []
    try:
        from src.port_occupier import find_udp_port_occupier

        occupier = find_udp_port_occupier(port)
    except Exception as exc:  # 诊断失败不应让命令整体失败
        occupier = [f"占用查询不可用：{exc}"]
    in_use = _port_in_use(port)
    data = {
        "port": port,
        "in_use": in_use,
        "occupier": occupier,
        "hint": "端口被占用时请更换 --port 或停止占用程序后再 run listen",
    }
    return data, f"端口 {port} {'已被占用' if in_use else '可用'}"
