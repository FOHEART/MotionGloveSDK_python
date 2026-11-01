"""
@file  decode_glove_csv.py
@brief 将拼接完成的 CSV body 字符串解析为 GloveFrame 数据容器。
@details
对应 C++ 实现：
  MotionGloveSDK/src/decodeAsGloveCSV.cpp    - GloveSplitFrameMgr::parseFrame()
  MotionGloveSDK/src/motionGloveSdkHelper.cpp - isFrameCSV_Glove()

说明：SDK 的数据流路径已改为调用 C++ 原生库（见 src/native/），
UDP 数据流的解析在库内部完成。本模块现在仅供
csv_frame_reader.py（CSV 文件回放）与 motionGloveSDK_rawReceiver.py
（原始数据调试工具）使用。

数值按骨骼（每骨 group_item_count 个）排列：
  - pos（米）占 3 个：x y z；
  - EULER 帧占 3 个：roll pitch yaw（按 header 的旋转顺序）；
  - QUAT  帧占 4 个：w x y z（线上顺序为 wxyz，与 C++
    decodeAsGloveCSV.cpp 的读取顺序一致）。

骨骼数量按值总数自动识别：42 骨（KHHS42）或 32 骨（KHHS32，经
BONE_INDEX_MAP_32_TO_42 映射回 42 骨索引）。总数不匹配 / 含非数值时
返回 None 并记录调试日志（MOTIONGLOVE_DEBUG=1 开启）。

调用方：
  from decode_glove_csv import decode_glove_csv

  def on_frame(actor, fn, body_csv):
      frame = decode_glove_csv(actor, fn, body_csv, header_tokens)
"""

import os

from .definitions import (
    KHHS42_SKELETON_COUNT,
    KHHS32_SKELETON_COUNT,
    BONE_NAMES,
    BONE_NAMES_32,
    BONE_INDEX_MAP_32_TO_42,
    SkeletonPosition,
    SkeletonAttitude,
    SkeletonCoordinate,
    ChannelOrder,
    HandGesture,
    CHANNEL_ORDER_FROM_STR,
    StreamHeader,
    SingleSkeleton,
    GloveFrame,
)
from .xsqeconverter import euler_degree_to_quat_xyzw


_DEBUG = os.getenv("MOTIONGLOVE_DEBUG", "0") == "1"
_decode_drop_count = 0


def _debug_log(msg: str) -> None:
    """@brief 调试日志输出（受环境变量 MOTIONGLOVE_DEBUG=1 控制）。

    @param msg 日志内容字符串，UTF-8 文本。
    @return 无（None）。
    """
    if _DEBUG:
        print(f"[MOTIONGLOVE_DEBUG][decode] {msg}")


def parse_header_tokens(tokens: list[str]) -> StreamHeader:
    """@brief 从 header token 列表中解析 StreamHeader。

    对应 C++ decodeAsGloveCSV_Func() 中对 splitHeaderVec 的逐项解析。
    缺失字段保留默认值，非法数值（IndexError/ValueError）静默跳过。

    tokens 示例：
      ["Glove1", "pos", "euler", "ZXY", "relative", "fn", "340772",
       "gesture", "0", "0", "subpackage", "1/1"]

    @param tokens header 行按空格分割后的 token 列表；空列表返回默认 StreamHeader。
    @return 填充后的 StreamHeader（avatar_name、姿态类型、旋转顺序、
            坐标系、帧序号、手势等字段）。
    """
    hdr = StreamHeader()

    if not tokens:
        return hdr

    # avatar name（第一个 token）
    hdr.avatar_name = tokens[0]

    # 固定字段，对应 C++ sh->bodySkeletonCount = 2 等
    hdr.body_skeleton_count          = 2
    hdr.left_figure_skeleton_count   = 15
    hdr.right_figure_skeleton_count  = 15

    # pos
    if "pos" in tokens:
        hdr.skeleton_position = SkeletonPosition.METER

    # quat / euler + 旋转顺序
    if "quat" in tokens:
        hdr.skeleton_attitude = SkeletonAttitude.QUAT
    elif "euler" in tokens:
        hdr.skeleton_attitude = SkeletonAttitude.EULER
        try:
            euler_idx   = tokens.index("euler")
            order_str   = tokens[euler_idx + 1]
            hdr.channel_order = CHANNEL_ORDER_FROM_STR.get(order_str, ChannelOrder.ZXY)
        except IndexError:
            pass

    # relative / global
    if "relative" in tokens:
        hdr.skeleton_coordinate = SkeletonCoordinate.RELATIVE
    elif "global" in tokens:
        hdr.skeleton_coordinate = SkeletonCoordinate.GLOBAL

    # fn（帧序号）
    if "fn" in tokens:
        try:
            fn_idx          = tokens.index("fn")
            hdr.frame_number = int(tokens[fn_idx + 1])
        except (IndexError, ValueError):
            pass

    # gesture（左手手势，右手手势）
    if "gesture" in tokens:
        try:
            g_idx = tokens.index("gesture")
            hdr.left_hand_gesture  = HandGesture(int(tokens[g_idx + 1]))
            hdr.right_hand_gesture = HandGesture(int(tokens[g_idx + 2]))
        except (IndexError, ValueError):
            pass

    return hdr


def decode_glove_csv(actor: str,
                     fn: int,
                     body_csv: str,
                     header_tokens: list[str],
                     remote_ip: str = "",
                     remote_port: int = 0) -> GloveFrame | None:
    """@brief 将拼接完成的帧数据解析为 GloveFrame。

    对应 C++ GloveSplitFrameMgr::parseFrame() + decodeAsGloveCSV_Func()
    末段的填充逻辑。流程：解析 StreamHeader → 依 header 计算
    group_item_count（pos 3 + euler 3 或 quat 4）→ 按值总数识别 42/32 骨
    → 逐骨填充位置与姿态（EULER 帧同时转出四元数）。

    @param actor         演员名称（avatar name），非空字符串，≤ 63 字节。
    @param fn            帧序号，非负整数。
    @param body_csv      拼接完成的 CSV 数值串（逗号分隔，不含 header 行）。
    @param header_tokens header 行按空格分割后的 token 列表（解析 StreamHeader 用）。
    @param remote_ip     数据来源 IP（可选，默认空串）。
    @param remote_port   数据来源端口（可选，默认 0）。
    @return 解析成功 → GloveFrame；header 无姿态字段、数值总数不匹配
            或含非数值 → None（不抛异常）。
    """
    # ------------------------------------------------------------------
    # 1. 解析 StreamHeader
    # ------------------------------------------------------------------
    hdr = parse_header_tokens(header_tokens)
    hdr.avatar_name  = actor
    hdr.frame_number = fn

    # ------------------------------------------------------------------
    # 2. 计算每段骨骼的数值个数（group_item_count）
    #    对应 C++ parseFrame() 中的 groupItemCount 计算
    # ------------------------------------------------------------------
    group_item_count = 0
    if hdr.skeleton_position == SkeletonPosition.METER:
        group_item_count += 3           # x y z
    if hdr.skeleton_attitude == SkeletonAttitude.EULER:
        group_item_count += 3           # roll pitch yaw
    elif hdr.skeleton_attitude == SkeletonAttitude.QUAT:
        group_item_count += 4           # x y z w

    if group_item_count == 0:
        _debug_log(
            f"drop actor={actor} fn={fn} reason=group_item_count_zero "
            f"header={' '.join(header_tokens[:16])}"
        )
        return None

    # ------------------------------------------------------------------
    # 3. 分割 CSV 数值
    # ------------------------------------------------------------------
    values_str = [v for v in body_csv.split(",") if v.strip()]
    actual = len(values_str)
    expected_42 = group_item_count * KHHS42_SKELETON_COUNT
    expected_32 = group_item_count * KHHS32_SKELETON_COUNT

    if actual == expected_42:
        skeleton_count = KHHS42_SKELETON_COUNT
        bone_names = BONE_NAMES
        bone_index_map = None
    elif actual == expected_32:
        skeleton_count = KHHS32_SKELETON_COUNT
        bone_names = BONE_NAMES_32
        bone_index_map = BONE_INDEX_MAP_32_TO_42
    else:
        global _decode_drop_count
        _decode_drop_count += 1
        if group_item_count > 0 and actual % group_item_count == 0:
            inferred = actual // group_item_count
            _debug_log(
                f"drop#{_decode_drop_count} actor={actor} fn={fn} reason=value_count_mismatch "
                f"expected=({expected_32}/s32 or {expected_42}/s42) actual={actual} "
                f"group_item_count={group_item_count} inferred_skeletons={inferred}"
            )
        else:
            _debug_log(
                f"drop#{_decode_drop_count} actor={actor} fn={fn} reason=value_count_mismatch "
                f"expected=({expected_32}/s32 or {expected_42}/s42) actual={actual} "
                f"group_item_count={group_item_count}"
            )
        return None

    if _DEBUG and (fn <= 3 or fn % 120 == 0):
        _debug_log(
            f"decode actor={actor} fn={fn} skeleton_count={skeleton_count} "
            f"group_item_count={group_item_count}"
        )

    try:
        values = [float(v) for v in values_str]
    except ValueError:
        _debug_log(f"drop actor={actor} fn={fn} reason=non_float_value")
        return None

    # ------------------------------------------------------------------
    # 4. 填充骨骼数组
    #    对应 C++ parseFrame() 中按 skeletonIndex 填充 pos/euler/quat
    # ------------------------------------------------------------------
    skeletons: list[SingleSkeleton] = []

    for i in range(skeleton_count):
        base = i * group_item_count
        skel = SingleSkeleton()
        skel.bone_index = bone_index_map[i] if bone_index_map is not None else i
        skel.bone_name  = bone_names[i]

        offset = 0

        if hdr.skeleton_position == SkeletonPosition.METER:
            skel.contains_position = 1
            skel.position = [values[base], values[base + 1], values[base + 2]]
            offset = 3

        if hdr.skeleton_attitude == SkeletonAttitude.EULER:
            ex = values[base + offset]
            ey = values[base + offset + 1]
            ez = values[base + offset + 2]
            skel.contains_euler_degree = 1
            skel.euler_degree = [ex, ey, ez]
            # 欧拉角 → 四元数，对应 C++ parseFrame() 末段的 EulerToQuat 调用
            # C++ 内部将 EulerToQuat 结果的 w 存到 quat[0]，x→[1],y→[2],z→[3]
            # 再在填充 ssd 时重新映射为 xyzw；最终结果等价于直接输出 [x,y,z,w]
            xyzw = euler_degree_to_quat_xyzw(ex, ey, ez, int(hdr.channel_order))
            skel.contains_quat_wxyz = 1
            skel.quat_wxyz = [xyzw[3], xyzw[0], xyzw[1], xyzw[2]]

        elif hdr.skeleton_attitude == SkeletonAttitude.QUAT:
            # QUAT 帧线上顺序为 wxyz（与 C++ decodeAsGloveCSV.cpp 一致），
            # 直接按 w x y z 读取，无需重排。
            qw = values[base + offset]
            qx = values[base + offset + 1]
            qy = values[base + offset + 2]
            qz = values[base + offset + 3]
            skel.contains_quat_wxyz = 1
            skel.quat_wxyz = [qw, qx, qy, qz]

        skeletons.append(skel)

    # ------------------------------------------------------------------
    # 5. 组装 GloveFrame
    # ------------------------------------------------------------------
    frame = GloveFrame()
    frame.header      = hdr
    frame.skeletons   = skeletons
    frame.remote_ip   = remote_ip
    frame.remote_port = remote_port

    return frame
