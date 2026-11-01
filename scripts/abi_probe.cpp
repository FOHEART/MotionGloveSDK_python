// abi_probe.cpp — 打印 MotionGloveSDK_cpp 公开结构体的尺寸与关键字段偏移。
//
// 用途：src/native/abi.py 中的 ctypes 定义必须与 C++ 侧的二进制布局完全一致。
//      C++ 工程改动结构体时，先重新编译本探针，核对 scripts/verify_native_abi.py
//      报告的差异，然后只修改 src/native/abi.py（转接层唯一与 ABI 耦合的文件）。
//
// 编译：见 scripts/verify_native_abi.py（会自动调用，无需手动编译）

#include <cstdio>
#include <cstddef>

#include "motionGloveSDKDef.h"

#define PRINT_SIZE(T)      std::printf("sizeof:%s=%zu\n", #T, sizeof(T))
#define PRINT_OFFSET(T, F) std::printf("offset:%s.%s=%zu\n", #T, #F, offsetof(T, F))

int main()
{
    PRINT_SIZE(StreamHeader);
    PRINT_SIZE(SingleSkeletonDef);
    PRINT_SIZE(KHHS42PosAttitude_TypeDef);
    PRINT_SIZE(KHHS32PosAttitude_TypeDef);
    PRINT_SIZE(KHHSOpenXRPosAttitude_TypeDef);

    PRINT_OFFSET(StreamHeader, protocolVersion);
    PRINT_OFFSET(StreamHeader, AvatarNameLength);
    PRINT_OFFSET(StreamHeader, AvatarName);
    PRINT_OFFSET(StreamHeader, suitNumber);
    PRINT_OFFSET(StreamHeader, suitType);
    PRINT_OFFSET(StreamHeader, frameNumber);
    PRINT_OFFSET(StreamHeader, bodySkeletonCount);
    PRINT_OFFSET(StreamHeader, leftFigureSkeletonCount);
    PRINT_OFFSET(StreamHeader, rightFigureSkeletonCount);
    PRINT_OFFSET(StreamHeader, streamFormat);
    PRINT_OFFSET(StreamHeader, skeletonPosition);
    PRINT_OFFSET(StreamHeader, skeletonAttitude);
    PRINT_OFFSET(StreamHeader, skeletonCoordinate);
    PRINT_OFFSET(StreamHeader, channelOrder);
    PRINT_OFFSET(StreamHeader, sensorAttitude);
    PRINT_OFFSET(StreamHeader, sensorAccel);
    PRINT_OFFSET(StreamHeader, sensorLAccel);
    PRINT_OFFSET(StreamHeader, sensorGyro);
    PRINT_OFFSET(StreamHeader, sensorMag);
    PRINT_OFFSET(StreamHeader, leftHandGesture);
    PRINT_OFFSET(StreamHeader, rightHandGesture);
    PRINT_OFFSET(StreamHeader, skeletonFormat);
    PRINT_OFFSET(StreamHeader, resv);

    PRINT_OFFSET(SingleSkeletonDef, skeletonName);
    PRINT_OFFSET(SingleSkeletonDef, position_meter);
    PRINT_OFFSET(SingleSkeletonDef, quat_xyzw);
    PRINT_OFFSET(SingleSkeletonDef, euler_degree);
    PRINT_OFFSET(SingleSkeletonDef, euler_biasDegree);
    PRINT_OFFSET(SingleSkeletonDef, sensorQuat_xyzw);

    PRINT_OFFSET(KHHS42PosAttitude_TypeDef, hdr);
    PRINT_OFFSET(KHHS42PosAttitude_TypeDef, skeletons);
    PRINT_OFFSET(KHHS42PosAttitude_TypeDef, remoteIP);
    PRINT_OFFSET(KHHS42PosAttitude_TypeDef, remotePort);
    PRINT_OFFSET(KHHS42PosAttitude_TypeDef, sdkVersion);

    PRINT_OFFSET(KHHS32PosAttitude_TypeDef, skeletons);
    PRINT_OFFSET(KHHS32PosAttitude_TypeDef, remoteIP);

    return 0;
}
