"""csv_to_bvh.py
将 MotionGlove CSV 导出文件转换为 BVH 动作捕捉文件。

位置单位：CSV 米  →  BVH 厘米（× 100）
旋转顺序：CSV ZXY  →  BVH 通道 ZYX（Zrotation Yrotation Xrotation）
骨骼映射：*3End → *4（拇指/食指等末端关节重命名）

公开接口
--------
convert_csv_to_bvh(csv_path, bvh_path=None, frame_rate=None) -> str
    转换并写出 BVH 文件，返回实际写出路径。
    bvh_path   缺省时与 csv_path 同目录同文件名，扩展名改为 .bvh。
    frame_rate 缺省时从 CSV 时间戳自动推算；无法推算时回退到 60 Hz。

命令行用法（独立运行）
----------------------
python -m src.csv_to_bvh --input recording.csv
python src/csv_to_bvh.py --input recording.csv --framerate 30 --outputdir ./out --output my_anim.bvh
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

# ── 兼容包内导入和直接运行两种方式 ───────────────────────────────────────────
if __name__ == "__main__":
    # 直接执行：将工程根目录加入路径，使用绝对导入
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.csv_frame_reader import CsvFrameReader          # type: ignore[import]
    from src.definitions import ChannelOrder, GloveFrame     # type: ignore[import]
    from src.xsqeconverter import euler_degree_to_quat_wxyz, quat_to_euler_degree  # type: ignore[import]
else:
    from .csv_frame_reader import CsvFrameReader
    from .definitions import ChannelOrder, GloveFrame
    from .xsqeconverter import euler_degree_to_quat_wxyz, quat_to_euler_degree

# ── 常量 ─────────────────────────────────────────────────────────────────────

_ZYX = int(ChannelOrder.ZYX)   # 5

_CHANNELS = "CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation"

# CSV BoneIndex (0-41) → BVH 关节名（*3End → *4）
_BVH_NAMES: list[str] = [
    "RightHand",
    "RightHandThumb1",  "RightHandThumb2",  "RightHandThumb3",  "RightHandThumb4",
    "RightHandIndex1",  "RightHandIndex2",  "RightHandIndex3",  "RightHandIndex4",
    "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3", "RightHandMiddle4",
    "RightHandRing1",   "RightHandRing2",   "RightHandRing3",   "RightHandRing4",
    "RightHandPinky1",  "RightHandPinky2",  "RightHandPinky3",  "RightHandPinky4",
    "LeftHand",
    "LeftHandThumb1",   "LeftHandThumb2",   "LeftHandThumb3",   "LeftHandThumb4",
    "LeftHandIndex1",   "LeftHandIndex2",   "LeftHandIndex3",   "LeftHandIndex4",
    "LeftHandMiddle1",  "LeftHandMiddle2",  "LeftHandMiddle3",  "LeftHandMiddle4",
    "LeftHandRing1",    "LeftHandRing2",    "LeftHandRing3",    "LeftHandRing4",
    "LeftHandPinky1",   "LeftHandPinky2",   "LeftHandPinky3",   "LeftHandPinky4",
]

# 时间戳正则：匹配 CSV 行头中 "time YYYY-MM-DD HH:MM:SS.mmm"
_TIME_RE = re.compile(r"time (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)")

# CSV BoneIndex → 父节点 BoneIndex（-1 表示无父，由合成 ROOT 直接挂载）
# 层级来自 kinemHumanHandsSkeleton42Index_tree.md
_PARENT: list[int] = [
    -1,                          # 0  RightHand       → ROOT
     0,  1,  2,  3,             # 1-4  右拇指链
     0,  5,  6,  7,             # 5-8  右食指链
     0,  9, 10, 11,             # 9-12 右中指链
     0, 13, 14, 15,             # 13-16 右无名指链
     0, 17, 18, 19,             # 17-20 右小指链
    -1,                          # 21 LeftHand        → ROOT
    21, 22, 23, 24,             # 22-25 左拇指链
    21, 26, 27, 28,             # 26-29 左食指链
    21, 30, 31, 32,             # 30-33 左中指链
    21, 34, 35, 36,             # 34-37 左无名指链
    21, 38, 39, 40,             # 38-41 左小指链
]


# ── 帧率检测 ─────────────────────────────────────────────────────────────────

def _detect_frame_time(raw_data_lines: list[str]) -> float:
    """从数据行列表推算帧间隔（秒），取前 10 行时间戳均值。"""
    timestamps: list[float] = []
    for line in raw_data_lines:
        comma = line.find(",")
        if comma == -1:
            continue
        m = _TIME_RE.search(line[:comma])
        if not m:
            continue
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S.%f")
            timestamps.append(dt.timestamp())
        except ValueError:
            pass
        if len(timestamps) >= 10:
            break

    if len(timestamps) >= 2:
        avg = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
        if avg > 0:
            return avg
    return 1.0 / 60.0


# ── BVH HIERARCHY 生成 ───────────────────────────────────────────────────────

def _write_chain(first: int, count: int, offsets: list[list[float]], indent: str) -> list[str]:
    """递归写一段连续骨骼链（最末节附加 End Site）。"""
    name = _BVH_NAMES[first]
    ox, oy, oz = offsets[first]
    lines = [
        f"{indent}JOINT {name}",
        f"{indent}{{",
        f"{indent}\tOFFSET {ox:.6f} {oy:.6f} {oz:.6f}",
        f"{indent}\t{_CHANNELS}",
    ]
    if count > 1:
        lines += _write_chain(first + 1, count - 1, offsets, indent + "\t")
    else:
        lines += [
            f"{indent}\tEnd Site",
            f"{indent}\t{{",
            f"{indent}\t\tOFFSET 0 0 0",
            f"{indent}\t}}",
        ]
    lines.append(f"{indent}}}")
    return lines


def _write_hand(hand_base: int, offsets: list[list[float]], indent: str) -> list[str]:
    """写一只手（含 5 根手指）的 JOINT 块。"""
    name = _BVH_NAMES[hand_base]
    ox, oy, oz = offsets[hand_base]
    lines = [
        f"{indent}JOINT {name}",
        f"{indent}{{",
        f"{indent}\tOFFSET {ox:.6f} {oy:.6f} {oz:.6f}",
        f"{indent}\t{_CHANNELS}",
    ]
    # 5 根手指，每根 4 节，相对 hand_base 的偏移：1,5,9,13,17
    for finger_offset in (1, 5, 9, 13, 17):
        lines += _write_chain(hand_base + finger_offset, 4, offsets, indent + "\t")
    lines.append(f"{indent}}}")
    return lines


def _build_hierarchy(offsets: list[list[float]]) -> str:
    """
    构建 BVH HIERARCHY 字符串。
    offsets: 42 项列表，每项 [x, y, z]（厘米），对应 CSV BoneIndex 0-41。
    """
    lines = [
        "HIERARCHY",
        "ROOT ROOT",
        "{",
        "\tOFFSET 0 0 0",
        f"\t{_CHANNELS}",
    ]
    lines += _write_hand(0,  offsets, "\t")   # 右手
    lines += _write_hand(21, offsets, "\t")   # 左手
    lines.append("}")
    return "\n".join(lines)


# ── 帧数据转换 ───────────────────────────────────────────────────────────────

def _frame_to_bvh_row(frame: GloveFrame) -> str:
    """将一帧 GloveFrame 转换为 BVH 帧数据行（258 个空格分隔的数值）。

    CSV position 是全局绝对坐标，BVH position channels 需要父子相对坐标，
    因此每个骨骼位置减去其父骨骼位置（ROOT 骨骼保持原始全局坐标）。
    """
    rot_order = int(frame.header.channel_order)
    values: list[float] = [0.0] * 6   # 合成 ROOT：全零

    pos = [sk.position for sk in frame.skeletons]   # 全局绝对位置（米）

    for i in range(42):
        sk = frame.skeletons[i]
        p = _PARENT[i]

        # 位置：减去父节点全局坐标，得父子相对偏移，再米→厘米
        if p == -1:
            # RightHand / LeftHand 直接挂在合成 ROOT 下，保留全局坐标
            px = sk.position[0] * 100.0
            py = sk.position[1] * 100.0
            pz = sk.position[2] * 100.0
        else:
            px = (sk.position[0] - pos[p][0]) * 100.0
            py = (sk.position[1] - pos[p][1]) * 100.0
            pz = (sk.position[2] - pos[p][2]) * 100.0

        # 旋转：CSV ZXY → BVH ZYX
        if sk.contains_euler_degree:
            ex, ey, ez = sk.euler_degree
            if rot_order != _ZYX:
                qw = euler_degree_to_quat_wxyz(ex, ey, ez, rot_order)
                ex, ey, ez = quat_to_euler_degree(qw, _ZYX)
        elif sk.contains_quat_wxyz:
            ex, ey, ez = quat_to_euler_degree(sk.quat_wxyz, _ZYX)
        else:
            ex, ey, ez = 0.0, 0.0, 0.0

        # BVH 通道顺序：Xpos Ypos Zpos Zrot Yrot Xrot
        values += [px, py, pz, ez, ey, ex]

    return " ".join(f"{v:.6f}" for v in values)


# ── 公开接口 ─────────────────────────────────────────────────────────────────

def convert_csv_to_bvh(
    csv_path: str,
    bvh_path: str | None = None,
    frame_rate: float | None = None,
) -> str:
    """
    将 MotionGlove CSV 文件转换为 BVH 文件。

    参数
    ----
    csv_path   : 输入 CSV 文件路径
    bvh_path   : 输出 BVH 路径；缺省时与 csv_path 同目录同名，扩展名改为 .bvh
    frame_rate : 强制指定帧率（Hz）；缺省时从 CSV 时间戳自动推算，无法推算时回退到 60 Hz

    返回
    ----
    实际写出的 BVH 文件路径（字符串）

    异常
    ----
    FileNotFoundError — CSV 文件不存在
    ValueError        — CSV 无可用帧
    """
    csv_p = Path(csv_path)
    out_p = Path(bvh_path) if bvh_path else csv_p.with_suffix(".bvh")

    # ── 帧率：优先使用调用方传入值，否则从时间戳自动推算 ──
    if frame_rate is not None and frame_rate > 0:
        frame_time = 1.0 / frame_rate
    else:
        with open(csv_p, "r", encoding="utf-8-sig") as f:
            raw_lines = f.readlines()
        data_lines = [ln.rstrip("\n\r") for ln in raw_lines[1:] if ln.strip()]
        frame_time = _detect_frame_time(data_lines)

    # ── 加载全部帧 ──────────────────────────────────
    reader = CsvFrameReader(csv_path)
    if reader.total_frames == 0:
        raise ValueError(f"CSV 文件中没有可用帧：{csv_path}")

    # ── 用第 1 帧（T-pose，所有骨骼角度为 0）位置作为 OFFSET（厘米）──
    first_frame = reader.next_frame()
    assert first_frame is not None
    pos0 = [sk.position for sk in first_frame.skeletons[:42]]
    offsets: list[list[float]] = []
    for i in range(42):
        p = _PARENT[i]
        if p == -1:
            ox = pos0[i][0] * 100.0
            oy = pos0[i][1] * 100.0
            oz = pos0[i][2] * 100.0
        else:
            ox = (pos0[i][0] - pos0[p][0]) * 100.0
            oy = (pos0[i][1] - pos0[p][1]) * 100.0
            oz = (pos0[i][2] - pos0[p][2]) * 100.0
        offsets.append([ox, oy, oz])

    # ── 构建 HIERARCHY ──────────────────────────────
    hierarchy = _build_hierarchy(offsets)

    # ── 构建 MOTION（从第 1 帧起全部输出）────────────
    reader.reset()
    motion_rows: list[str] = []
    while not reader.at_end:
        frame = reader.next_frame()
        if frame is not None:
            motion_rows.append(_frame_to_bvh_row(frame))

    motion = "\n".join([
        "MOTION",
        f"Frames: {len(motion_rows)}",
        f"Frame Time: {frame_time:.6f}",
        *motion_rows,
    ])

    # ── 写出文件 ────────────────────────────────────
    out_p.write_text(hierarchy + "\n" + motion + "\n", encoding="utf-8")
    return str(out_p)


# ── 命令行入口 ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="csv_to_bvh.py",
        description=(
            "将 MotionGlove CSV 导出文件转换为 BVH 动作捕捉文件。\n\n"
            "注意：CSV 文件的第一帧应为 T-pose（所有骨骼角度为零），\n"
            "其位置数据将作为 BVH HIERARCHY 段的 OFFSET 参考值。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python src/csv_to_bvh.py --input recording.csv\n"
            "  python src/csv_to_bvh.py --input recording.csv --framerate 30\n"
            "  python src/csv_to_bvh.py --input recording.csv --outputdir ./out\n"
            "  python src/csv_to_bvh.py --input recording.csv --outputdir ./out --output my_anim.bvh\n"
        ),
    )
    parser.add_argument(
        "--input",
        metavar="CSV_FILE",
        required=True,
        help="输入 CSV 文件路径（MotionGlove 导出格式）",
    )
    parser.add_argument(
        "--framerate",
        metavar="FPS",
        type=float,
        default=None,
        help="输出帧率（Hz）。不设置时从 CSV 时间戳自动推算，无法推算时默认 60 Hz",
    )
    parser.add_argument(
        "--outputdir",
        metavar="DIR",
        default=None,
        help="输出目录。不设置时与输入 CSV 文件相同目录",
    )
    parser.add_argument(
        "--output",
        metavar="FILENAME",
        default=None,
        help="输出文件名（含扩展名，如 my_anim.bvh）。不设置时与输入 CSV 同名，扩展名改为 .bvh",
    )

    args = parser.parse_args()

    csv_p = Path(args.input)

    # 确定输出目录
    out_dir = Path(args.outputdir) if args.outputdir else csv_p.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # 确定输出文件名
    out_name = args.output if args.output else csv_p.with_suffix(".bvh").name
    bvh_p = out_dir / out_name

    print(f"[csv_to_bvh] 输入：{csv_p}")
    if args.framerate:
        print(f"[csv_to_bvh] 帧率：{args.framerate} Hz（手动指定）")
    else:
        print("[csv_to_bvh] 帧率：自动推算（不足时回退到 60 Hz）")

    try:
        result = convert_csv_to_bvh(str(csv_p), str(bvh_p), frame_rate=args.framerate)
        print(f"[csv_to_bvh] 完成：{result}")
    except (FileNotFoundError, ValueError) as e:
        print(f"[csv_to_bvh] 错误：{e}", file=sys.stderr)
        sys.exit(1)
