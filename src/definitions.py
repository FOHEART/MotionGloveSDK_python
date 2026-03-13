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

KHHS32_SKELETON_COUNT = 32      # 对应 C++ KHHS32_SkeletonCount
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
    """对应 C++ kinemHumanHandsSkeleton32Index"""
    RightHand       =  0
    RightHandThumb1 =  1
    RightHandThumb2 =  2
    RightHandThumb3 =  3
    RightHandIndex1 =  4
    RightHandIndex2 =  5
    RightHandIndex3 =  6
    RightHandMiddle1=  7
    RightHandMiddle2=  8
    RightHandMiddle3=  9
    RightHandRing1  = 10
    RightHandRing2  = 11
    RightHandRing3  = 12
    RightHandPinky1 = 13
    RightHandPinky2 = 14
    RightHandPinky3 = 15
    LeftHand        = 16
    LeftHandThumb1  = 17
    LeftHandThumb2  = 18
    LeftHandThumb3  = 19
    LeftHandIndex1  = 20
    LeftHandIndex2  = 21
    LeftHandIndex3  = 22
    LeftHandMiddle1 = 23
    LeftHandMiddle2 = 24
    LeftHandMiddle3 = 25
    LeftHandRing1   = 26
    LeftHandRing2   = 27
    LeftHandRing3   = 28
    LeftHandPinky1  = 29
    LeftHandPinky2  = 30
    LeftHandPinky3  = 31

# 骨骼全名列表，对应 C++ kinemHumanHandsSkeleton32[]
BONE_NAMES: list[str] = [b.name for b in BoneIndex]

# 骨骼短名列表，对应 C++ kinemHumanHandsSkeleton32Short[]
BONE_NAMES_SHORT: list[str] = [
    "rHAND",
    "RHT1","RHT2","RHT3",
    "RHI1","RHI2","RHI3",
    "RHM1","RHM2","RHM3",
    "RHR1","RHR2","RHR3",
    "RHP1","RHP2","RHP3",
    "lHAND",
    "LHT1","LHT2","LHT3",
    "LHI1","LHI2","LHI3",
    "LHM1","LHM2","LHM3",
    "LHR1","LHR2","LHR3",
    "LHP1","LHP2","LHP3",
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
        default_factory=lambda: [SingleSkeleton() for _ in range(KHHS32_SKELETON_COUNT)]
    )
    remote_ip:   str  = ""     # 数据来源 IP
    remote_port: int  = 0      # 数据来源端口
