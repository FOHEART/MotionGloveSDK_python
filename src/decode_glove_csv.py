"""
decode_glove_csv.py - MotionGloveSDK Python
将拼接完成的 CSV body 字符串解析为 GloveFrame 数据容器

对应 C++ 实现：
  MotionGloveSDK/src/decodeAsGloveCSV.cpp  - GloveSplitFrameMgr::parseFrame()
  MotionGloveSDK/src/motionGloveSdkHelper.cpp - isFrameCSV_Glove()

调用方（由 glove_frame_assembler.py 的回调触发）：
  from decode_glove_csv import decode_glove_csv

  def on_frame(actor, fn, body_csv):
      frame = decode_glove_csv(actor, fn, body_csv, header_tokens)
"""

from .definitions import (
    KHHS32_SKELETON_COUNT,
    BONE_NAMES,
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
from .euler_to_quat import euler_to_quat


def parse_header_tokens(tokens: list[str]) -> StreamHeader:
    """
    从 header token 列表中解析 StreamHeader。
    对应 C++ decodeAsGloveCSV_Func() 中对 splitHeaderVec 的逐项解析。

    tokens 示例：
      ["Glove1", "pos", "euler", "ZXY", "relative", "fn", "340772",
       "gesture", "0", "0", "subpackage", "1/1"]
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
    """
    将拼接完成的帧数据解析为 GloveFrame。
    对应 C++ GloveSplitFrameMgr::parseFrame() + decodeAsGloveCSV_Func() 末段的填充逻辑。

    参数：
      actor         : 演员名称（avatar name）
      fn            : 帧序号
      body_csv      : 拼接完成的 CSV 数值串（不含 header 行）
      header_tokens : header 行按空格分割后的 token 列表（用于解析 StreamHeader）
      remote_ip     : 数据来源 IP（可选）
      remote_port   : 数据来源端口（可选）

    返回：
      解析成功 → GloveFrame；格式不符 → None
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
        return None

    # ------------------------------------------------------------------
    # 3. 分割 CSV 数值
    # ------------------------------------------------------------------
    values_str = [v for v in body_csv.split(",") if v.strip()]
    expected   = group_item_count * KHHS32_SKELETON_COUNT

    if len(values_str) != expected:
        return None

    try:
        values = [float(v) for v in values_str]
    except ValueError:
        return None

    # ------------------------------------------------------------------
    # 4. 填充骨骼数组
    #    对应 C++ parseFrame() 中按 skeletonIndex 填充 pos/euler/quat
    # ------------------------------------------------------------------
    skeletons: list[SingleSkeleton] = []

    for i in range(KHHS32_SKELETON_COUNT):
        base = i * group_item_count
        skel = SingleSkeleton()
        skel.bone_index = i
        skel.bone_name  = BONE_NAMES[i]

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
            xyzw = euler_to_quat(ex, ey, ez, hdr.channel_order)
            skel.contains_quat_wxyz = 1
            skel.quat_wxyz = [xyzw[3], xyzw[0], xyzw[1], xyzw[2]]

        elif hdr.skeleton_attitude == SkeletonAttitude.QUAT:
            # CSV 中四元数顺序为 x y z w
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
