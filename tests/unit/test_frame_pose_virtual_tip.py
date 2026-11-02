"""
@file  test_frame_pose_virtual_tip.py
@brief 32 骨数据流「虚拟指尖」（compute_frame_pose）单元测试。
@details
回归目标：虚拟末梢必须沿第三段骨骼的**局部 +Y 轴**（骨骼静止姿态的轴向）
延伸。历史上误用了局部 +X 轴，指尖会与手指成 90° 折角（“骨折”现象）。

用例全部使用合成数据，不依赖真实采集文件。导入示例脚本需要 libs/ 中的
VTK 依赖，缺失时整文件跳过。
"""

import importlib.util
import math
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
# VTK / PySide6 由 scripts/[Windows]setup_python_libs.cmd 安装到 libs/
sys.path.insert(0, str(_ROOT / "libs"))
pytest.importorskip("vtk", reason="需要 libs/ 中的 VTK 依赖")

from src.definitions import (  # noqa: E402
    BONE_NAMES_32,
    BoneIndex,
    GloveFrame,
    SingleSkeleton,
)

_SPEC = importlib.util.spec_from_file_location(
    "example3_3dview", _ROOT / "motionGloveSDK_example3_3dView.py"
)
assert _SPEC is not None and _SPEC.loader is not None
v3d = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(v3d)

_IDENTITY = (1.0, 0.0, 0.0, 0.0)

# 32 骨数据流（无 *End 末梢节点）包含的骨骼索引
_STREAM_32_NAMES = set(BONE_NAMES_32)
_STREAM_32_INDICES = [b for b in BoneIndex if b.name in _STREAM_32_NAMES]


def _skel(bone, position, quat=_IDENTITY, with_quat=True):
    """构造一个同时携带位置与（可选）四元数的骨骼节点。"""
    s = SingleSkeleton()
    s.bone_index = int(bone)
    s.contains_position = 1
    s.contains_quat_wxyz = 1 if with_quat else 0
    s.position = list(position)
    s.quat_wxyz = list(quat)
    return s


def _frame_32(overrides):
    """构造 32 骨帧；未在 overrides 中给出的骨骼落在原点、姿态为单位元。

    @param overrides {BoneIndex: (position, quat, with_quat)} 覆盖项。
    """
    skeletons = []
    for bone in _STREAM_32_INDICES:
        position, quat, with_quat = overrides.get(
            bone, ((0.0, 0.0, 0.0), _IDENTITY, True)
        )
        skeletons.append(_skel(bone, position, quat, with_quat))
    assert len(skeletons) == 32
    frame = GloveFrame()
    frame.skeletons = skeletons
    return frame


def _direction(a, b):
    d = [b[i] - a[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in d))
    return [c / n for c in d]


def _axis_angle_quat(axis, degrees):
    half = math.radians(degrees) * 0.5
    s, c = math.sin(half), math.cos(half)
    return (c, axis[0] * s, axis[1] * s, axis[2] * s)


def test_virtual_tip_continues_rest_axis_y():
    """静止姿态（四元数为单位元）下，指尖必须沿 +Y 继续，而不是 +X。"""
    frame = _frame_32({
        BoneIndex.RightHand: ((0.10, 0.00, 0.0), _IDENTITY, True),
        BoneIndex.RightHandIndex1: ((0.08, 0.08, 0.0), _IDENTITY, True),
        BoneIndex.RightHandIndex2: ((0.08, 0.10, 0.0), _IDENTITY, True),
        BoneIndex.RightHandIndex3: ((0.08, 0.12, 0.0), _IDENTITY, True),
    })
    positions, _ = v3d.compute_frame_pose(frame)

    p3 = positions[BoneIndex.RightHandIndex3]
    tip = positions[BoneIndex.RightHandIndex3End]
    assert tip is not None
    assert _direction(p3, tip) == pytest.approx([0.0, 1.0, 0.0], abs=1e-6)
    assert math.dist(p3, tip) == pytest.approx(v3d._VIRTUAL_TIP_LENGTH_M, abs=1e-9)


def test_virtual_tip_follows_hand_rotation():
    """手掌绕 Z 轴旋转 90° 后，指尖应随第三段的全局姿态转到 -X。"""
    hand_rot = _axis_angle_quat((0.0, 0.0, 1.0), 90.0)
    frame = _frame_32({
        BoneIndex.LeftHand: ((-0.10, 0.00, 0.0), hand_rot, True),
        BoneIndex.LeftHandIndex1: ((-0.11, 0.00, 0.0), _IDENTITY, True),
        BoneIndex.LeftHandIndex2: ((-0.13, 0.00, 0.0), _IDENTITY, True),
        BoneIndex.LeftHandIndex3: ((-0.15, 0.00, 0.0), _IDENTITY, True),
    })
    positions, _ = v3d.compute_frame_pose(frame)

    p3 = positions[BoneIndex.LeftHandIndex3]
    tip = positions[BoneIndex.LeftHandIndex3End]
    assert tip is not None
    assert _direction(p3, tip) == pytest.approx([-1.0, 0.0, 0.0], abs=1e-6)


def test_virtual_tip_falls_back_to_last_phalanx_without_attitude():
    """无姿态数据时，指尖方向退化为第二节到第三节的实际骨段方向。"""
    frame = _frame_32({
        BoneIndex.RightHand: ((0.10, 0.00, 0.0), _IDENTITY, False),
        BoneIndex.RightHandIndex1: ((0.08, 0.08, 0.0), _IDENTITY, False),
        BoneIndex.RightHandIndex2: ((0.08, 0.10, 0.0), _IDENTITY, False),
        BoneIndex.RightHandIndex3: ((0.09, 0.12, 0.0), _IDENTITY, False),
    })
    positions, _ = v3d.compute_frame_pose(frame)

    p2 = positions[BoneIndex.RightHandIndex2]
    p3 = positions[BoneIndex.RightHandIndex3]
    tip = positions[BoneIndex.RightHandIndex3End]
    assert tip is not None
    assert _direction(p3, tip) == pytest.approx(_direction(p2, p3), abs=1e-6)


def test_no_virtual_tip_for_full_42_bone_stream():
    """42 骨数据流自带末梢节点，不得再追加虚拟指尖。"""
    frame = GloveFrame()
    frame.skeletons = [_skel(b, (0.0, 0.0, 0.0)) for b in BoneIndex]
    assert len(frame.skeletons) == 42
    positions, _ = v3d.compute_frame_pose(frame)
    # 全部节点位于原点：虚拟指尖若被追加，末梢位置会偏移 20mm
    assert positions[BoneIndex.RightHandIndex3End] == [0.0, 0.0, 0.0]
    assert positions[BoneIndex.LeftHandPinky3End] == [0.0, 0.0, 0.0]
