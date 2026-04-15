"""
definitions.py - MotionGloveSDK Python
数据结构与枚举定义

对应 C++ 头文件：
  MotionGloveSDK/include/motionGloveSDK_commonDef.h
  MotionGloveSDK/include/motionGloveSDK_HMAXGloveDef.h
  MotionGloveSDK/include/motionGloveSDKDef.h
"""

from dataclasses import dataclass, field
from enum import IntEnum

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

KHHS42_SKELETON_COUNT = 42      # 对应 C++ KHHS42_SkeletonCount
KHHS32_SKELETON_COUNT = 32      # legacy alias — kept for CSV compatibility
ACTOR_NAME_LEN_MAX    = 64      # 对应 C++ ACTOR_NAME_LEN_MAX


# ---------------------------------------------------------------------------
# 枚举：对应 motionGloveSDK_commonDef.h
# ---------------------------------------------------------------------------

class SkeletonPosition(IntEnum):
    """对应 C++ SkeletonPosition_TypeDef"""
    NONE  = 0   # 不含骨骼位置
    METER = 1   # 含位置，单位：米

class SkeletonAttitude(IntEnum):
    """对应 C++ SkeletonAttitude_TypeDef"""
    NONE  = 0   # 不含旋转
    EULER = 1   # 欧拉角，单位：度
    QUAT  = 2   # 四元数

class SkeletonCoordinate(IntEnum):
    """对应 C++ SkeletonCoordinate_TypeDef"""
    RELATIVE = 0   # 本地坐标系（相对父骨骼）
    GLOBAL   = 1   # 全局坐标系

class ChannelOrder(IntEnum):
    """对应 C++ MVSDK_ChannelOrder"""
    XYZ = 0
    XZY = 1
    YXZ = 2
    YZX = 3
    ZXY = 4
    ZYX = 5

# 字符串 → 枚举的映射，对应 C++ MVSDK_ChannelOrder_StringDesc
CHANNEL_ORDER_FROM_STR: dict[str, ChannelOrder] = {
    "XYZ": ChannelOrder.XYZ,
    "XZY": ChannelOrder.XZY,
    "YXZ": ChannelOrder.YXZ,
    "YZX": ChannelOrder.YZX,
    "ZXY": ChannelOrder.ZXY,
    "ZYX": ChannelOrder.ZYX,
}

class HandGesture(IntEnum):
    """对应 C++ HandGesture_TypeDef（15 种手势识别结果）"""
    NONE =  0
    G1   =  1
    G2   =  2
    G3   =  3
    G4   =  4
    G5   =  5
    G6   =  6
    G7   =  7
    G8   =  8
    G9   =  9
    G10  = 10
    G11  = 11
    G12  = 12
    G13  = 13
    G14  = 14
    G15  = 15


# ---------------------------------------------------------------------------
# 枚举：骨骼索引 — 对应 motionGloveSDK_HMAXGloveDef.h
# ---------------------------------------------------------------------------

class BoneIndex(IntEnum):
    """对应 C++ kinemHumanHandsSkeleton42Index"""
    RightHand            =  0
    RightHandThumb1      =  1
    RightHandThumb2      =  2
    RightHandThumb3      =  3
    RightHandThumb3End   =  4
    RightHandIndex1      =  5
    RightHandIndex2      =  6
    RightHandIndex3      =  7
    RightHandIndex3End   =  8
    RightHandMiddle1     =  9
    RightHandMiddle2     = 10
    RightHandMiddle3     = 11
    RightHandMiddle3End  = 12
    RightHandRing1       = 13
    RightHandRing2       = 14
    RightHandRing3       = 15
    RightHandRing3End    = 16
    RightHandPinky1      = 17
    RightHandPinky2      = 18
    RightHandPinky3      = 19
    RightHandPinky3End   = 20
    LeftHand             = 21
    LeftHandThumb1       = 22
    LeftHandThumb2       = 23
    LeftHandThumb3       = 24
    LeftHandThumb3End    = 25
    LeftHandIndex1       = 26
    LeftHandIndex2       = 27
    LeftHandIndex3       = 28
    LeftHandIndex3End    = 29
    LeftHandMiddle1      = 30
    LeftHandMiddle2      = 31
    LeftHandMiddle3      = 32
    LeftHandMiddle3End   = 33
    LeftHandRing1        = 34
    LeftHandRing2        = 35
    LeftHandRing3        = 36
    LeftHandRing3End     = 37
    LeftHandPinky1       = 38
    LeftHandPinky2       = 39
    LeftHandPinky3       = 40
    LeftHandPinky3End    = 41

# 骨骼全名列表，对应 C++ kinemHumanHandsSkeleton32[]
BONE_NAMES: list[str] = [b.name for b in BoneIndex]

# 骨骼短名列表，对应 C++ kinemHumanHandsSkeleton42Short[]
BONE_NAMES_SHORT: list[str] = [
    "rHAND",
    "RHT1","RHT2","RHT3","RHT3E",
    "RHI1","RHI2","RHI3","RHI3E",
    "RHM1","RHM2","RHM3","RHM3E",
    "RHR1","RHR2","RHR3","RHR3E",
    "RHP1","RHP2","RHP3","RHP3E",
    "lHAND",
    "LHT1","LHT2","LHT3","LHT3E",
    "LHI1","LHI2","LHI3","LHI3E",
    "LHM1","LHM2","LHM3","LHM3E",
    "LHR1","LHR2","LHR3","LHR3E",
    "LHP1","LHP2","LHP3","LHP3E",
]


# ---------------------------------------------------------------------------
# 数据容器
# ---------------------------------------------------------------------------

@dataclass
class StreamHeader:
    """
    帧头信息。
    对应 C++ StreamHeader（motionGloveSDK_commonDef.h）
    """
    protocol_version:        int              = 0
    avatar_name:             str              = ""
    suit_number:             int              = 0
    frame_number:            int              = 0
    body_skeleton_count:     int              = 0
    left_figure_skeleton_count:  int          = 0
    right_figure_skeleton_count: int          = 0
    skeleton_position:       SkeletonPosition = SkeletonPosition.NONE
    skeleton_attitude:       SkeletonAttitude = SkeletonAttitude.EULER
    skeleton_coordinate:     SkeletonCoordinate = SkeletonCoordinate.RELATIVE
    channel_order:           ChannelOrder     = ChannelOrder.ZXY
    left_hand_gesture:       HandGesture      = HandGesture.NONE
    right_hand_gesture:      HandGesture      = HandGesture.NONE


@dataclass
class SingleSkeleton:
    """
    单段骨骼数据。
    对应 C++ SingleSkeletonDef（motionGloveSDKDef.h）
    """
    bone_index:   int = -1
    bone_name:    str = ""

    # 数据流中各项是否存在：1 存在，0 不存在
    contains_position:    int = 0
    contains_quat_wxyz:   int = 0
    contains_euler_degree: int = 0

    # 骨骼位置（米），对应 C++ position_meter[3]
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])

    # 骨骼旋转四元数 wxyz，对应 C++ quat_xyzw[4]（内部存储顺序为 w x y z）
    quat_wxyz: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])

    # 骨骼旋转欧拉角（度），对应 C++ euler_degree[3]
    euler_degree: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])


@dataclass
class GloveFrame:
    """
    一帧完整的手套骨骼数据。
    对应 C++ KHHS32PosAttitude_TypeDef（motionGloveSDKDef.h）
    """
    header:     StreamHeader              = field(default_factory=StreamHeader)
    skeletons:  list[SingleSkeleton]      = field(
        default_factory=lambda: [SingleSkeleton() for _ in range(KHHS42_SKELETON_COUNT)]
    )
    remote_ip:   str  = ""     # 数据来源 IP
    remote_port: int  = 0      # 数据来源端口
