"""
@file  export_cmd.py
@brief export 命令：把帧导出为 JSON / MotionGlove CSV / BVH。
@details --format 省略时按输出文件扩展名推断；BVH 复用
         src/csv_to_bvh.convert_csv_to_bvh()，不重复实现骨骼层级逻辑。
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from src.csv_frame_reader import CsvFrameReader
from src.csv_to_bvh import convert_csv_to_bvh

from ..envelope import ExportError, IoError, ParseError, UdpError, UsageError
from ..frames import (
    collect_udp_frames,
    frame_to_dict,
    frames_to_csv,
    load_csv_frames,
)
from ..parser import as_bool, as_float, as_int
from .run_cmd import resolve_source

Result = tuple[dict[str, Any], str]
FORMATS = ("json", "csv", "bvh")


def _frame_rate(payload: dict[str, Any]) -> float | None:
    """@brief 取 BVH 帧率（0/None 表示由 CSV 时间戳自动推算）。"""
    raw = payload.get("frame_rate", payload.get("frame-rate"))
    value = as_float(raw, 0.0, name="frame_rate", lo=0.0, hi=1000.0)
    return value if value > 0 else None


def _write_frames(
    fmt: str,
    out: Path,
    frames: list[Any],
    *,
    source: str,
    path: str | None,
    actor: str,
    frame_rate: float | None,
) -> None:
    """@brief 按格式写出帧数据（BVH 经临时 CSV 中转）。

    @param fmt 目标格式（json/csv/bvh）。
    @param out 输出路径。
    @param frames 帧列表。
    @param source 数据源类型。
    @param path 源 CSV 路径（可为 None）。
    @param actor 数据流名称。
    @param frame_rate BVH 帧率，None 表示自动推算。
    @exception ValueError CSV 无可用帧（BVH 转换要求至少一帧）。
    """
    if fmt == "json":
        body = {
            "source": source,
            "input": path,
            "actor": actor,
            "exported_at": datetime.now().isoformat(timespec="seconds"),
            "frames": [frame_to_dict(f) for f in frames],
        }
        out.write_text(
            json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    elif fmt == "csv":
        out.write_text(frames_to_csv(frames, actor), encoding="utf-8")
    else:
        if not frames:
            raise ValueError("BVH 导出要求至少一帧数据")
        with tempfile.TemporaryDirectory(prefix="motionglove-cli-") as tmp:
            tmp_csv = Path(tmp) / "frames.csv"
            tmp_csv.write_text(frames_to_csv(frames, actor), encoding="utf-8")
            convert_csv_to_bvh(str(tmp_csv), str(out), frame_rate)


def export(payload: dict[str, Any]) -> Result:
    """@brief 导出当前工程/指定源的帧数据。

    @param payload output=输出路径（必填）、format=json|csv|bvh（省略按扩展名）、
                   input/file=源 CSV、source、actor、index、count、all、
                   frame_rate、port、timeout。
    @return (data, message)。
    @exception UsageError 缺 output 或参数非法。
    @exception ExportError 格式不支持。
    @exception IoError 输出目录不存在或写出失败。
    @exception ParseError 源数据无可用帧。
    @exception UdpError UDP 源等待超时。
    """
    raw_out = payload.get("output") or payload.get("path") or payload.get("out")
    if not raw_out:
        raise UsageError("缺少必填参数 output（导出文件路径）")
    out = Path(str(raw_out)).expanduser().resolve()

    fmt = str(payload.get("format") or "").strip().lower().lstrip(".")
    if not fmt:
        fmt = out.suffix.lstrip(".").lower()
    if fmt not in FORMATS:
        raise ExportError(
            f"不支持的导出格式：{fmt or '(未指定)'}；"
            f"可选 {', '.join(FORMATS)}，或把输出文件扩展名写成 .json/.csv/.bvh",
            data={"format": fmt, "supported": list(FORMATS)},
        )
    if not out.parent.is_dir():
        raise IoError(f"输出目录不存在：{out.parent}（请先创建目录）")

    frame_rate = _frame_rate(payload)
    source, path, port, actor = resolve_source(payload)
    index = payload.get("index")
    count = payload.get("count")
    export_all = as_bool(payload.get("all")) or (index is None and count is None)

    # BVH 快路径：源就是 CSV 文件且导出整段，直接复用现成转换器
    if fmt == "bvh" and source == "csv" and export_all and path:
        total = CsvFrameReader(str(path)).total_frames
        if total == 0:
            raise ParseError(f"CSV 文件中没有可用帧：{path}")
        try:
            convert_csv_to_bvh(str(path), str(out), frame_rate)
        except (FileNotFoundError, ValueError) as exc:
            raise ParseError(f"BVH 转换失败：{exc}") from exc
        frames_count = total
    else:
        if source == "csv":
            assert path is not None
            start = as_int(index, 0, name="index", lo=0)
            limit = None if export_all else as_int(count, 1, name="count", lo=1, hi=100000)
            frames, _total = load_csv_frames(path, start, limit)
        else:
            seconds = as_float(payload.get("timeout"), 2.0, name="timeout", lo=0.05, hi=60.0)
            frames, udp_info = collect_udp_frames(port, actor, seconds, first_only=True)
            if not frames:
                raise UdpError(
                    f"等待 {seconds} 秒内未收到可导出的帧（端口 {port}）",
                    data={"port": port, "actor": actor, "udp": udp_info},
                )
        frames_count = len(frames)
        try:
            _write_frames(
                fmt, out, frames,
                source=source, path=path, actor=actor, frame_rate=frame_rate,
            )
        except ValueError as exc:
            raise ParseError(str(exc)) from exc
        except OSError as exc:
            raise IoError(f"写出文件失败：{exc}") from exc

    data = {
        "output": str(out),
        "format": fmt,
        "source": source,
        "input": path,
        "actor": actor,
        "frames": frames_count,
        "bytes": out.stat().st_size,
        "frame_rate": frame_rate,
    }
    return data, f"已导出 {frames_count} 帧到 {out}"
