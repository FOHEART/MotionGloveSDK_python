"""
@file  abi.py
@brief C++ 侧二进制布局的 ctypes 映射。
@details
═══════════════════════════════════════════════════════════════════════════
  这是整个转接层中【唯一】与 C++ 结构体内存布局耦合的文件。
  当 MotionGloveSDK_cpp 修改了结构体 / 枚举 / 导出函数签名时：
    1. 重新编译原生库：scripts/[Windows]build_mgsdk_cpp.cmd
    2. 运行 ABI 校验：  python scripts/verify_native_abi.py
    3. 只修改本文件，使 sizeof/offsetof 与 C++ 一致
  其余文件（loader.py / mapper.py / backend.py）无需改动。
═══════════════════════════════════════════════════════════════════════════

对应 C++ 头文件（均 #pragma pack(1)，Python 侧用 _pack_ = 1 镜像）：
  MotionGloveSDK/include/motionGloveSDK_commonDef.h
  MotionGloveSDK/include/motionGloveSDKDef.h
  MotionGloveSDK/include/motionGloveSDK_skeleton42Def.h
  MotionGloveSDK/include/motionGloveSDK_skeleton32Def.h

布局基准（VS2022 x64 / GCC x86_64 实测一致，由 scripts/abi_probe.cpp 打印）：
  sizeof(StreamHeader)                  = 131    skeletonFormat @ 91
  sizeof(SingleSkeletonDef)             = 196    skeletonName    @ 4
  sizeof(KHHS42PosAttitude_TypeDef)     = 8375   remoteIP        @ 8363
  sizeof(KHHS32PosAttitude_TypeDef)     = 6415   remoteIP        @ 6403
  sizeof(KHHSOpenXRPosAttitude_TypeDef) = 10335

测试：tests/unit/test_abi.py（布局基准 + verify_layout 自检）。
"""

from __future__ import annotations

import ctypes

# ---------------------------------------------------------------------------
# 常量（对应 motionGloveSDKDef.h / motionGloveSDK_skeleton*Def.h）
# ---------------------------------------------------------------------------

ACTOR_NAME_LEN_MAX = 64          # 数据流名称最大长度（含结尾 NUL）
SKELETON_NAME_LEN = 64           # SingleSkeletonDef.skeletonName 缓冲区长度
STREAM_HEADER_RESERVED_LEN = 39

KHHS32_SKELETON_COUNT = 32       # KHHS32_SkeletonCount
KHHS42_SKELETON_COUNT = 42       # KHHS42_SkeletonCount
KHHS_OPENXR_SKELETON_COUNT = 52  # KHHSOpenXR_SkeletonCount（布局未定义，仅用于定尺寸）


class SkeletonFormat:
    """@brief 骨骼流格式。@details GloveStreamSkeletonFormat_TypeDef（uint8 枚举）。"""

    SKELETON_32 = 0
    SKELETON_42 = 1
    OPENXR = 2


class SkeletonPosition:
    """@brief 骨骼位置类型。@details SkeletonPosition_TypeDef（uint8 枚举）。"""

    NONE = 0
    METER = 1


class SkeletonAttitude:
    """@brief 骨骼旋转类型。@details SkeletonAttitude_TypeDef（uint8 枚举）。"""

    NONE = 0
    EULER = 1
    QUAT = 2


class SkeletonCoordinate:
    """@brief 骨骼坐标系。@details SkeletonCoordinate_TypeDef（uint8 枚举）。"""

    RELATIVE = 0
    GLOBAL = 1


# ---------------------------------------------------------------------------
# 结构体
# ---------------------------------------------------------------------------

class StreamHeader(ctypes.Structure):
    """@brief 帧头结构体。@details 对应 C++ StreamHeader（motionGloveSDK_commonDef.h），
            #pragma pack(1) 与 Python 侧 _pack_ = 1 对齐；字段顺序必须与 C++ 一致。"""

    _pack_ = 1
    _fields_ = [
        ("protocol_version", ctypes.c_uint16),
        ("avatar_name_length", ctypes.c_uint8),
        ("avatar_name", ctypes.c_uint8 * ACTOR_NAME_LEN_MAX),
        ("suit_number", ctypes.c_uint32),
        ("suit_type", ctypes.c_uint8),
        ("frame_number", ctypes.c_uint32),
        ("body_skeleton_count", ctypes.c_uint8),
        ("left_figure_skeleton_count", ctypes.c_uint8),
        ("right_figure_skeleton_count", ctypes.c_uint8),
        ("stream_format", ctypes.c_uint8),
        ("skeleton_position", ctypes.c_uint8),
        ("skeleton_attitude", ctypes.c_uint8),
        ("skeleton_coordinate", ctypes.c_uint8),
        ("channel_order", ctypes.c_uint8),
        ("sensor_attitude", ctypes.c_uint8),
        ("sensor_accel", ctypes.c_uint8),
        ("sensor_l_accel", ctypes.c_uint8),
        ("sensor_gyro", ctypes.c_uint8),
        ("sensor_mag", ctypes.c_uint8),
        # H1GLOVE_FLEX_VALUE 未定义时没有 sensorFlex 字段
        ("left_hand_gesture", ctypes.c_uint8),
        ("right_hand_gesture", ctypes.c_uint8),
        ("skeleton_format", ctypes.c_uint8),
        ("resv", ctypes.c_uint8 * STREAM_HEADER_RESERVED_LEN),
    ]


class SingleSkeleton(ctypes.Structure):
    """@brief 单骨骼段结构体（196 字节）。

    @details 对应 C++ SingleSkeletonDef（motionGloveSDKDef.h）。quat_xyzw /
             sensor_quat_xyzw 按 xyzw 存储，Python 对外输出前由 mapper 重排为 wxyz。
    """

    _pack_ = 1
    _fields_ = [
        # union { gloveSkeletonIndex(42 索引); gloveSkeletonIndex32(32 索引) }
        ("skeleton_index", ctypes.c_int32),
        ("skeleton_name", ctypes.c_char * SKELETON_NAME_LEN),
        ("position_meter", ctypes.c_float * 3),
        ("quat_xyzw", ctypes.c_float * 4),
        ("euler_degree", ctypes.c_float * 3),
        ("euler_bias_degree", ctypes.c_float * 3),
        ("sensor_quat_xyzw", ctypes.c_float * 4),
        ("sensor_euler_degree", ctypes.c_float * 3),
        ("sensor_accel_g", ctypes.c_float * 3),
        ("sensor_l_accel_g", ctypes.c_float * 3),
        ("sensor_gyro_degree_per_second", ctypes.c_float * 3),
        ("sensor_mag_mgauss", ctypes.c_float * 3),
    ]


class KHHS42PosAttitude(ctypes.Structure):
    """对应 C++ KHHS42PosAttitude_TypeDef（42 段骨骼整帧）"""

    _pack_ = 1
    _fields_ = [
        ("hdr", StreamHeader),
        ("skeletons", SingleSkeleton * KHHS42_SKELETON_COUNT),
        ("remote_ip", ctypes.c_uint8 * 4),
        ("remote_port", ctypes.c_uint32),
        ("sdk_version", ctypes.c_uint32),
    ]


class KHHS32PosAttitude(ctypes.Structure):
    """对应 C++ KHHS32PosAttitude_TypeDef（32 段骨骼整帧）"""

    _pack_ = 1
    _fields_ = [
        ("hdr", StreamHeader),
        ("skeletons", SingleSkeleton * KHHS32_SKELETON_COUNT),
        ("remote_ip", ctypes.c_uint8 * 4),
        ("remote_port", ctypes.c_uint32),
        ("sdk_version", ctypes.c_uint32),
    ]


class KHHSOpenXRPosAttitude(ctypes.Structure):
    """对应 C++ KHHSOpenXRPosAttitude_TypeDef（布局未定义，仅冻结尺寸）"""

    _pack_ = 1
    _fields_ = [
        ("hdr", StreamHeader),
        ("skeletons", SingleSkeleton * KHHS_OPENXR_SKELETON_COUNT),
        ("remote_ip", ctypes.c_uint8 * 4),
        ("remote_port", ctypes.c_uint32),
        ("sdk_version", ctypes.c_uint32),
    ]


# 帧容器按骨骼格式选择，对应 C++ MotionGloveSDK_GetSkeletonsFrameType() 的返回值
FRAME_STRUCT_BY_FORMAT: dict[int, type[ctypes.Structure]] = {
    SkeletonFormat.SKELETON_32: KHHS32PosAttitude,
    SkeletonFormat.SKELETON_42: KHHS42PosAttitude,
}

STRUCTS: dict[str, type[ctypes.Structure]] = {
    "StreamHeader": StreamHeader,
    "SingleSkeleton": SingleSkeleton,
    "KHHS42PosAttitude": KHHS42PosAttitude,
    "KHHS32PosAttitude": KHHS32PosAttitude,
    "KHHSOpenXRPosAttitude": KHHSOpenXRPosAttitude,
}


# ---------------------------------------------------------------------------
# 布局自检
# ---------------------------------------------------------------------------

EXPECTED_SIZES: dict[str, int] = {
    "StreamHeader": 131,
    "SingleSkeleton": 196,
    "KHHS42PosAttitude": 8375,
    "KHHS32PosAttitude": 6415,
    "KHHSOpenXRPosAttitude": 10335,
}

EXPECTED_OFFSETS: dict[str, dict[str, int]] = {
    "StreamHeader": {
        "protocol_version": 0,
        "avatar_name_length": 2,
        "avatar_name": 3,
        "frame_number": 72,
        "skeleton_position": 80,
        "skeleton_attitude": 81,
        "skeleton_coordinate": 82,
        "channel_order": 83,
        "left_hand_gesture": 89,
        "right_hand_gesture": 90,
        "skeleton_format": 91,
        "resv": 92,
    },
    "SingleSkeleton": {
        "skeleton_index": 0,
        "skeleton_name": 4,
        "position_meter": 68,
        "quat_xyzw": 80,
        "euler_degree": 96,
    },
    "KHHS42PosAttitude": {
        "skeletons": 131,
        "remote_ip": 8363,
        "remote_port": 8367,
        "sdk_version": 8371,
    },
}


def describe_layout() -> dict[str, dict[str, int]]:
    """@brief 返回当前 ctypes 定义实际的 sizeof 与全部字段 offset。

    @return 嵌套字典 {结构体名: {"sizeof": N, 字段名: offset, ...}}，
            供 verify_layout() 与 scripts/abi_probe.cpp 输出比对。
    """
    layout: dict[str, dict[str, int]] = {}
    for struct_name, struct in STRUCTS.items():
        entry: dict[str, int] = {"sizeof": ctypes.sizeof(struct)}
        for field in struct._fields_:
            field_name = field[0]
            entry[field_name] = getattr(struct, field_name).offset
        layout[struct_name] = entry
    return layout


def verify_layout() -> list[str]:
    """@brief 校验 ctypes 定义与基准布局是否一致。

    @details 基准见 EXPECTED_SIZES / EXPECTED_OFFSETS（scripts/abi_probe.cpp
             实测值）。供 tests/unit/test_abi.py 与 scripts/verify_native_abi.py 使用。
    @return 不一致项描述列表（每项一条）；完全一致时返回空列表。
    """
    problems: list[str] = []

    for struct_name, expected in EXPECTED_SIZES.items():
        actual = ctypes.sizeof(STRUCTS[struct_name])
        if actual != expected:
            problems.append(f"sizeof({struct_name}) = {actual}, 期望 {expected}")

    for struct_name, offsets in EXPECTED_OFFSETS.items():
        struct = STRUCTS[struct_name]
        for field_name, expected in offsets.items():
            actual = getattr(struct, field_name).offset
            if actual != expected:
                problems.append(f"offset({struct_name}.{field_name}) = {actual}, 期望 {expected}")

    return problems
