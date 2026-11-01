"""
native_smoke_test.py - 原生后端端到端冒烟测试（不需要真实数据手套）

用法：
    python scripts/native_smoke_test.py

流程：
    1. 加载 MotionGloveSDK 原生库（缺少库时直接失败）
    2. 绑定一个空闲 UDP 端口
    3. 用本机 socket 发送合成的 MotionGlove CSV 数据帧（42 段 / 32 段各一帧）
    4. 通过 motionGloveSDK 公共接口取回 GloveFrame，逐项校验
       （帧序号、骨骼名/索引、位置、欧拉角、四元数、来源地址、格式）
"""

from __future__ import annotations

import socket
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src import motionGloveSDK  # noqa: E402
from src.definitions import (  # noqa: E402
    BONE_INDEX_MAP_32_TO_42,
    BONE_NAMES_32,
    ChannelOrder,
    SkeletonAttitude,
    SkeletonPosition,
)
from src.native import SkeletonFormat  # noqa: E402
from src.xsqeconverter import euler_degree_to_quat_xyzw  # noqa: E402

ACTOR_42 = "Glove1"
ACTOR_32 = "Glove2"
TIMEOUT_S = 5.0

_failures: list[str] = []


def check(condition: bool, message: str) -> None:
    if condition:
        return
    _failures.append(message)
    print(f"[fail] {message}")


def approx(actual, expected, tol: float = 1e-4) -> bool:
    return abs(float(actual) - float(expected)) <= tol


def approx_seq(actual, expected, tol: float = 1e-4) -> bool:
    return len(actual) == len(expected) and all(
        approx(a, e, tol) for a, e in zip(actual, expected)
    )


def free_udp_port() -> int:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]
    finally:
        probe.close()


def build_payload(actor: str, frame_number: int, skeleton_count: int) -> bytes:
    """构造与 MotionGlove 客户端一致的一帧 CSV 数据。"""
    header = f"{actor} pos euler ZXY relative fn {frame_number}  subpackage 1/1"
    values: list[str] = []
    for index in range(skeleton_count):
        values.extend([repr(index * 0.001), "0.0", "0.0", "1.0", "2.0", "3.0"])
    return f"{header},{','.join(values)}".encode("utf-8")


def wait_pending(actor: str) -> bool:
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending(actor):
            return True
        time.sleep(0.005)
    return False


def fetch_frame(actor: str):
    if not wait_pending(actor):
        check(False, f"{actor}: 超时未收到新帧")
        return None
    frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame(actor)
    motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending(actor)
    check(frame is not None, f"{actor}: 取帧失败")
    return frame


def test_42_frame(frame, frame_number: int, sender_port: int) -> None:
    check(len(frame.skeletons) == 42, f"42 段帧长度应为 42，实际 {len(frame.skeletons)}")
    check(frame.header.frame_number == frame_number,
          f"帧序号应为 {frame_number}，实际 {frame.header.frame_number}")
    check(frame.header.avatar_name == ACTOR_42,
          f"数据流名称应为 {ACTOR_42}，实际 {frame.header.avatar_name}")
    check(frame.header.skeleton_position == SkeletonPosition.METER, "帧头应标记含位置（米）")
    check(frame.header.skeleton_attitude == SkeletonAttitude.EULER, "帧头应标记欧拉角姿态")
    check(frame.header.channel_order == ChannelOrder.ZXY, "帧头旋转顺序应为 ZXY")

    first = frame.skeletons[0]
    check(first.bone_name == "RightHand", f"0 号骨骼应为 RightHand，实际 {first.bone_name}")
    check(first.bone_index == 0, f"0 号骨骼索引应为 0，实际 {first.bone_index}")
    check(first.contains_position == 1, "0 号骨骼应标记含位置")
    check(first.contains_euler_degree == 1, "0 号骨骼应标记含欧拉角")
    check(first.contains_quat_wxyz == 1, "0 号骨骼应标记含四元数")
    check(approx_seq(first.euler_degree, [1.0, 2.0, 3.0]),
          f"0 号骨骼欧拉角应为 [1,2,3]，实际 {first.euler_degree}")

    last = frame.skeletons[41]
    check(last.bone_name == "LeftHandPinky3End",
          f"41 号骨骼应为 LeftHandPinky3End，实际 {last.bone_name}")
    check(approx_seq(frame.skeletons[5].position, [0.005, 0.0, 0.0]),
          f"5 号骨骼位置应为 [0.005,0,0]，实际 {frame.skeletons[5].position}")

    # 欧拉角 → 四元数由 C++ 内部换算，应与 Python 侧同一算法一致
    qx, qy, qz, qw = euler_degree_to_quat_xyzw(1.0, 2.0, 3.0, int(ChannelOrder.ZXY))
    check(approx_seq(first.quat_wxyz, [qw, qx, qy, qz], tol=1e-4),
          f"0 号骨骼四元数应为 {[qw, qx, qy, qz]}，实际 {first.quat_wxyz}")

    check(frame.remote_ip == "127.0.0.1", f"来源 IP 应为 127.0.0.1，实际 {frame.remote_ip}")
    check(frame.remote_port == sender_port,
          f"来源端口应为 {sender_port}，实际 {frame.remote_port}")
    check(motionGloveSDK.MotionGloveSDK_GetSkeletonsFrameType(ACTOR_42) == SkeletonFormat.SKELETON_42,
          "GetSkeletonsFrameType 应返回 42 段格式")


def test_32_frame(frame, frame_number: int) -> None:
    check(len(frame.skeletons) == 32, f"32 段帧长度应为 32，实际 {len(frame.skeletons)}")
    check(frame.header.frame_number == frame_number,
          f"帧序号应为 {frame_number}，实际 {frame.header.frame_number}")
    check(frame.skeletons[0].bone_index == 0, "32 段首骨骼应映射到 42 段索引 0")
    check(frame.skeletons[16].bone_index == BONE_INDEX_MAP_32_TO_42[16],
          f"32 段第 16 段应映射到 42 段索引 {BONE_INDEX_MAP_32_TO_42[16]}，"
          f"实际 {frame.skeletons[16].bone_index}")
    check(frame.skeletons[16].bone_name in (BONE_NAMES_32[16], "LeftHand"),
          f"32 段第 16 段名称异常：{frame.skeletons[16].bone_name}")
    check(motionGloveSDK.MotionGloveSDK_GetSkeletonsFrameType(ACTOR_32) == SkeletonFormat.SKELETON_32,
          "GetSkeletonsFrameType 应返回 32 段格式")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except AttributeError:  # pragma: no cover - 非 TextIOWrapper
        pass

    print(f"[info] 后端      : {motionGloveSDK.MotionGloveSDK_GetBackendName()}")
    print(f"[info] 原生库    : {motionGloveSDK.MotionGloveSDK_GetNativeLibraryPath()}")
    print(f"[info] 版本号    : {motionGloveSDK.MotionGloveSDK_getVersion()}")
    check(motionGloveSDK.MotionGloveSDK_getVersion() > 0, "SDK 版本号应大于 0")

    # 无效输入
    check(motionGloveSDK.MotionGloveSDK_isGloveNewFramePending("") is False, "空名称应返回 False")
    check(motionGloveSDK.MotionGloveSDK_isGloveNewFramePending("x" * 64) is False,
          "超长名称（64 字节）应返回 False")
    check(motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame("NoSuchActor") is None,
          "未知数据流取帧应返回 None")

    port = free_udp_port()
    print(f"[info] 监听端口  : {port}")
    if motionGloveSDK.MotionGloveSDK_ListenUDPPort(port) != 0:
        print("[fail] 绑定 UDP 端口失败")
        return 1

    sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sender.bind(("127.0.0.1", 0))
    sender_port = sender.getsockname()[1]
    target = ("127.0.0.1", port)

    try:
        sender.sendto(build_payload(ACTOR_42, 1001, 42), target)
        frame = fetch_frame(ACTOR_42)
        if frame is not None:
            test_42_frame(frame, 1001, sender_port)
            check(
                motionGloveSDK.MotionGloveSDK_GetLastRemoteAddr() == ("127.0.0.1", sender_port),
                f"GetLastRemoteAddr 应为 ('127.0.0.1', {sender_port})，"
                f"实际 {motionGloveSDK.MotionGloveSDK_GetLastRemoteAddr()}",
            )

        sender.sendto(build_payload(ACTOR_32, 2002, 32), target)
        frame = fetch_frame(ACTOR_32)
        if frame is not None:
            test_32_frame(frame, 2002)

        actor_names = motionGloveSDK.MotionGloveSDK_GetActorNames()
        check(ACTOR_42 in actor_names, f"GetActorNames 应包含 {ACTOR_42}，实际 {actor_names}")
        check(ACTOR_32 in actor_names, f"GetActorNames 应包含 {ACTOR_32}，实际 {actor_names}")
    finally:
        sender.close()
        check(motionGloveSDK.MotionGloveSDK_CloseUDPPort() == 0, "CloseUDPPort 应返回 0")
        check(motionGloveSDK.MotionGloveSDK_CloseUDPPort() == -1,
              "重复 CloseUDPPort 应返回 -1")
        check(motionGloveSDK.MotionGloveSDK_ListenUDPPort(port) == 0, "关闭后应能重新绑定同一端口")
        motionGloveSDK.MotionGloveSDK_CloseUDPPort()

    if _failures:
        print(f"\n[fail] {len(_failures)} 项校验未通过")
        return 1

    print("\n[ok] 原生后端冒烟测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
