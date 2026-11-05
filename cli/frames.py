"""
@file  frames.py
@brief 帧数据源与序列化：CSV 回放、UDP 采集、帧 → JSON / MotionGlove CSV。
@details
本模块只依赖标准库与 src/（纯 Python + ctypes），不 import vtk / PySide6 /
bpy，因此可在无头环境与 CI 中运行。CLI 命令与未来 GUI 复用同一套转换逻辑。
"""

from __future__ import annotations

import dataclasses
import enum
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src import motionGloveSDK as sdk
from src.csv_frame_reader import CsvFrameReader
from src.definitions import (
    BONE_INDEX_MAP_32_TO_42,
    BONE_NAMES,
    BONE_NAMES_SHORT,
    CHANNEL_ORDER_FROM_STR,
    ChannelOrder,
    GloveFrame,
    SkeletonAttitude,
    SkeletonCoordinate,
    SkeletonPosition,
    SingleSkeleton,
)

from .envelope import NativeError, ParseError, UdpError

CSV_HEADER_LINE = "column,header,line"
DEFAULT_ACTOR = "Glove1"
DEFAULT_PORT = 5001


# ── 帧 → JSON ────────────────────────────────────────────────────────────

def frame_to_dict(frame: GloveFrame) -> dict[str, Any]:
    """@brief 把 GloveFrame 转为可 JSON 序列化的字典。

    @details dataclass 递归展开；IntEnum 显式转 int，附加 bone_count
             让 Agent 不必自行 len(skeletons) 判断 32/42 段流。
    @param frame 一帧骨骼数据。
    @return 含 header / skeletons / remote_ip / remote_port / bone_count 的字典。
    """
    data = dataclasses.asdict(frame)
    header = data.get("header", {})
    for key, value in list(header.items()):
        if isinstance(value, enum.IntEnum):
            header[key] = int(value)
    data["bone_count"] = len(frame.skeletons)
    return data


def summarize(frame: GloveFrame) -> dict[str, Any]:
    """@brief 帧摘要（不含完整骨骼数组，适合批量输出）。

    @param frame 一帧骨骼数据。
    @return 含帧号/骨骼数/数据标志/首个关节位置的字典。
    """
    first = frame.skeletons[0] if frame.skeletons else None
    return {
        "frame_number": int(frame.header.frame_number),
        "avatar_name": frame.header.avatar_name,
        "bone_count": len(frame.skeletons),
        "contains_position": int(frame.header.skeleton_position),
        "contains_attitude": int(frame.header.skeleton_attitude),
        "remote": {"ip": frame.remote_ip, "port": frame.remote_port},
        "first_joint": (
            {
                "bone_index": first.bone_index,
                "bone_name": first.bone_name,
                "position": list(first.position),
            }
            if first is not None
            else None
        ),
    }


# ── 帧 → MotionGlove CSV ─────────────────────────────────────────────────

def _order_name(order: Any) -> str:
    """@brief ChannelOrder 枚举 → CSV header 中的三字母旋转序名。"""
    try:
        return next(
            k for k, v in CHANNEL_ORDER_FROM_STR.items() if int(v) == int(order)
        )
    except (StopIteration, TypeError, ValueError):
        return "ZXY"


def frame_to_csv_row(frame: GloveFrame, actor: str, row_index: int) -> str:
    """@brief 把一帧序列化为一行 MotionGlove CSV（可被 CsvFrameReader 读回）。

    @details 线上格式与 decode_glove_csv 一致：
             pos 存在 → 3 值；euler 存在 → 3 值；quat 存在 → 4 值（wxyz）。
             骨骼数由 len(skeletons) 决定，42/32 段均可 round-trip。
    @param frame 一帧骨骼数据。
    @param actor 数据流名称（写入 header 第一个 token）。
    @param row_index 行序号（帧号缺失时用作 fn）。
    @return 不含换行的 CSV 数据行文本。
    """
    hdr = frame.header
    has_pos = int(hdr.skeleton_position) == int(SkeletonPosition.METER)
    attitude = int(hdr.skeleton_attitude)
    has_euler = attitude == int(SkeletonAttitude.EULER)
    has_quat = attitude == int(SkeletonAttitude.QUAT)

    tokens = [actor, "time", datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]]
    if has_pos:
        tokens.append("pos")
    if has_quat:
        tokens.append("quat")
    elif has_euler:
        tokens += ["euler", _order_name(hdr.channel_order)]
    tokens.append(
        "global" if int(hdr.skeleton_coordinate) == int(SkeletonCoordinate.GLOBAL)
        else "relative"
    )
    fn = int(hdr.frame_number) if int(hdr.frame_number) > 0 else row_index
    tokens += ["fn", str(fn), "subpackage", "1/1"]
    header_text = " ".join(tokens)

    values: list[str] = []
    for skel in frame.skeletons:
        if has_pos:
            values += [f"{float(v):.6f}" for v in skel.position[:3]]
        if has_quat:
            values += [f"{float(v):.6f}" for v in skel.quat_wxyz[:4]]
        elif has_euler:
            values += [f"{float(v):.6f}" for v in skel.euler_degree[:3]]

    return f"{header_text}," + ",".join(values)


def frames_to_csv(frames: list[GloveFrame], actor: str | None = None) -> str:
    """@brief 把多帧序列化为完整 MotionGlove CSV 文本（含列名表头行）。

    @param frames 帧列表；空列表时只返回表头行。
    @param actor 数据流名称，缺省取首帧 header.avatar_name，再缺省 Glove1。
    @return 以换行结尾的 CSV 文本。
    """
    name = actor or (
        frames[0].header.avatar_name if frames else ""
    ) or DEFAULT_ACTOR
    lines = [CSV_HEADER_LINE]
    lines += [frame_to_csv_row(f, name, i) for i, f in enumerate(frames)]
    return "\n".join(lines) + "\n"


def synthetic_frames(count: int, actor: str) -> list[GloveFrame]:
    """@brief 生成 count 帧零位 T-pose 示例数据（project new 用）。

    @param count 帧数（非负）。
    @param actor 数据流名称。
    @return GloveFrame 列表，每帧 42 段骨骼。
    """
    frames: list[GloveFrame] = []
    for i in range(count):
        frame = GloveFrame()
        h = frame.header
        h.protocol_version = 1
        h.avatar_name = actor
        h.frame_number = i + 1
        h.body_skeleton_count = 2
        h.left_figure_skeleton_count = 15
        h.right_figure_skeleton_count = 15
        h.skeleton_position = SkeletonPosition.METER
        h.skeleton_attitude = SkeletonAttitude.EULER
        h.skeleton_coordinate = SkeletonCoordinate.RELATIVE
        h.channel_order = ChannelOrder.ZXY
        frame.skeletons = [
            SingleSkeleton(
                bone_index=j,
                bone_name=BONE_NAMES[j],
                contains_position=1,
                contains_quat_wxyz=1,
                contains_euler_degree=1,
            )
            for j in range(len(BONE_NAMES))
        ]
        frames.append(frame)
    return frames


# ── CSV 数据源 ───────────────────────────────────────────────────────────

def load_csv_frames(
    path: str, start: int = 0, count: int | None = None
) -> tuple[list[GloveFrame], int]:
    """@brief 从 CSV 文件加载 [start, start+count) 范围内的帧。

    @param path CSV 文件路径。
    @param start 起始帧索引（0-based）。
    @param count 最多取多少帧；None 表示取到末帧。
    @return (帧列表, 文件总帧数)。
    @exception ParseError 文件无可用帧或 start 越界。
    """
    reader = CsvFrameReader(str(path))
    total = reader.total_frames
    if total == 0:
        raise ParseError(f"CSV 文件中没有可用帧：{path}")
    if start < 0 or start >= total:
        raise ParseError(f"帧索引 {start} 越界，文件共 {total} 帧（有效范围 0~{total - 1}）")
    reader.seek(start)
    limit = total - start if count is None else max(0, min(count, total - start))
    frames: list[GloveFrame] = []
    for _ in range(limit):
        frame = reader.next_frame()
        if frame is None:
            break
        frames.append(frame)
    return frames, total


# ── UDP 数据源 ───────────────────────────────────────────────────────────

def collect_udp_frames(
    port: int,
    actor: str,
    seconds: float,
    *,
    first_only: bool = False,
) -> tuple[list[GloveFrame], dict[str, Any]]:
    """@brief 在一条命令的进程内完成「监听 → 取帧 → 关闭」。

    @details 每条命令一个进程，UDP 监听无法跨进程保持；因此 run.frame /
             run.listen 都在本函数内闭环。底层 SDK 的中文 print 由
             cli_runner.dispatch 的 stdout 捕获统一处理，不污染 JSON 信封。
    @param port UDP 端口。
    @param actor 数据流名称。
    @param seconds 最长等待秒数。
    @param first_only 取到第一帧即返回。
    @return (帧列表, 采集信息字典)。
    @exception NativeError 原生库不可用。
    @exception UdpError 端口绑定失败或底层调用异常。
    """
    if not sdk.MotionGloveSDK_IsAvailable():
        raise NativeError(
            "MotionGloveSDK 原生库不可用，无法监听 UDP；"
            "请执行 scripts\\build_mgsdk_cpp.cmd 或设置 MOTIONGLOVE_NATIVE_LIB"
        )

    ret = sdk.MotionGloveSDK_ListenUDPPort(port)
    if ret != 0:
        detail: list[str] = []
        try:
            from src.port_occupier import find_udp_port_occupier

            detail = find_udp_port_occupier(port)
        except Exception:
            pass
        raise UdpError(
            f"UDP 端口 {port} 绑定失败", data={"port": port, "occupier": detail}
        )

    frames: list[GloveFrame] = []
    actors: list[str] = []
    started = time.monotonic()
    try:
        while time.monotonic() - started < seconds:
            if sdk.MotionGloveSDK_isGloveNewFramePending(actor):
                frame = sdk.MotionGloveSDK_GetGloveSkeletonsFrame(actor)
                if frame is not None:
                    frames.append(frame)
                sdk.MotionGloveSDK_resetGloveNewFramePending(actor)
                if first_only:
                    break
            else:
                time.sleep(0.01)
        actors = list(sdk.MotionGloveSDK_GetActorNames())
    except Exception as exc:  # 底层 SDK 异常统一映射为 ERR_UDP
        raise UdpError(f"UDP 取帧失败：{exc}") from exc
    finally:
        sdk.MotionGloveSDK_CloseUDPPort()

    remote = sdk.MotionGloveSDK_GetLastRemoteAddr()
    info: dict[str, Any] = {
        "port": port,
        "actor": actor,
        "actors": actors,
        "seconds": round(time.monotonic() - started, 3),
        "remote": (
            {"ip": remote[0], "port": remote[1]} if remote is not None else None
        ),
    }
    return frames, info


def bone_layout() -> dict[str, Any]:
    """@brief 返回 42/32 骨骼索引映射表（run bones 用）。

    @return 含骨骼名、短名、32→42 映射与计数的字典。
    """
    return {
        "format": "42",
        "bone_count": len(BONE_NAMES),
        "bone_names": list(BONE_NAMES),
        "short_names": list(BONE_NAMES_SHORT),
        "legacy_32_bone_count": len(BONE_INDEX_MAP_32_TO_42),
        "map_32_to_42": list(BONE_INDEX_MAP_32_TO_42),
        "path": str(Path(__file__).resolve().parent.parent / "src" / "definitions.py"),
    }
