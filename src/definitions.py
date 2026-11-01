"""
@file  definitions.py
@brief MotionGloveSDK Python 数据结构与枚举定义。
@details
与 C++ 头文件保持一一对应（改 C++ 结构体时同步改这里，并用
scripts/verify_native_abi.py / tests/unit/test_abi.py 校验）：
  - MotionGloveSDK/include/motionGloveSDK_commonDef.h
  - MotionGloveSDK/include/motionGloveSDK_HMAXGloveDef.h
  - MotionGloveSDK/include/motionGloveSDKDef.h

内容分四部分：
  1. 常量与 32 骨名称表 / 32→42 索引映射表；
  2. 协议枚举（姿态类型、坐标系、旋转顺序、手势）；
  3. 骨骼索引枚举 BoneIndex（42 节点，含 *End 端点）与名称表；
  4. 数据容器 StreamHeader / SingleSkeleton / GloveFrame。

测试：tests/unit/test_definitions.py、tests/unit/test_abi.py。
"""

from dataclasses import dataclass, field
from enum import IntEnum

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

KHHS42_SKELETON_COUNT = 42      # 对应 C++ KHHS42_SkeletonCount
KHHS32_SKELETON_COUNT = 32      # legacy alias — kept for CSV compatibility
ACTOR_NAME_LEN_MAX    = 64      # 对应 C++ ACTOR_NAME_LEN_MAX

# 32 节点骨架顺序（无 *End 节点），与 kinemHumanHandsSkeleton32Index_tree.md 保持一致
BONE_NAMES_32: list[str] = [
    # Right hand
    "RightHand",
    "RightHandThumb1", "RightHandThumb2", "RightHandThumb3",
    "RightHandIndex1", "RightHandIndex2", "RightHandIndex3",
    "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3",
    "RightHandRing1", "RightHandRing2", "RightHandRing3",
    "RightHandPinky1", "RightHandPinky2", "RightHandPinky3",
    # Left hand
    "LeftHand",
    "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3",
    "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3",
    "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3",
    "LeftHandRing1", "LeftHandRing2", "LeftHandRing3",
    "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3",
]

# 32 节点流索引映射到 42 节点 BoneIndex（无 End 节点）
BONE_INDEX_MAP_32_TO_42: list[int] = [
    0, 1, 2, 3,
    5, 6, 7,
    9, 10, 11,
    13, 14, 15,
    17, 18, 19,
    21, 22, 23, 24,
    26, 27, 28,
    30, 31, 32,
    34, 35, 36,
    38, 39, 40,
]


# ---------------------------------------------------------------------------
# 枚举：对应 motionGloveSDK_commonDef.h
# ---------------------------------------------------------------------------

class SkeletonPosition(IntEnum):
    """@brief 骨骼位置数据类型。@details 对应 C++ SkeletonPosition_TypeDef。"""
    NONE  = 0   # 不含骨骼位置
    METER = 1   # 含位置，单位：米

class SkeletonAttitude(IntEnum):
    """@brief 骨骼旋转数据类型。@details 对应 C++ SkeletonAttitude_TypeDef。"""
    NONE  = 0   # 不含旋转
    EULER = 1   # 欧拉角，单位：度
    QUAT  = 2   # 四元数

class SkeletonCoordinate(IntEnum):
    """@brief 骨骼坐标系。@details 对应 C++ SkeletonCoordinate_TypeDef。"""
    RELATIVE = 0   # 本地坐标系（相对父骨骼）
    GLOBAL   = 1   # 全局坐标系

class ChannelOrder(IntEnum):
    """@brief 欧拉角旋转顺序。@details 对应 C++ MVSDK_ChannelOrder；
             数值与 xsqeconverter 的 rot_order 参数一致（0=XYZ … 5=ZYX）。"""
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
    """@brief 手势识别结果。@details 对应 C++ HandGesture_TypeDef（15 种手势）。"""
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
    """@brief 42 节点手部骨骼索引。@details 对应 C++ kinemHumanHandsSkeleton42Index；
             *3End 为指尖端点节点，数据流（32 骨）中不发送。"""
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
    """@brief 帧头信息。

    @details 对应 C++ StreamHeader（motionGloveSDK_commonDef.h）。
             CSV 路径下由 decode_glove_csv.parse_header_tokens() 填充；
             原生库路径下由 mapper.py 从 C 结构体映射。
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
    """@brief 单段骨骼数据。

    @details 对应 C++ SingleSkeletonDef（motionGloveSDKDef.h）。
             contains_* 标志表示对应数据在当前流中是否存在
             （1 存在，0 不存在）；quat_wxyz 以 [w,x,y,z] 存储
             （与 C++ quat_xyzw[4] 内存顺序一致）。
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
    """@brief 一帧完整的手套骨骼数据。

    @details 对应 C++ KHHS32PosAttitude_TypeDef（motionGloveSDKDef.h）。
             skeletons 默认按 42 骨初始化；CSV 32 骨流经
             BONE_INDEX_MAP_32_TO_42 映射到 42 骨索引。
    """
    header:     StreamHeader              = field(default_factory=StreamHeader)
    skeletons:  list[SingleSkeleton]      = field(
        default_factory=lambda: [SingleSkeleton() for _ in range(KHHS42_SKELETON_COUNT)]
    )
    remote_ip:   str  = ""     # 数据来源 IP
    remote_port: int  = 0      # 数据来源端口
