# CLAUDE.md

This file provides guidance to Claude Code when working with files in this directory.

## Directory Purpose

`MotionGloveBVH/` contains BVH (BioVision Hierarchy) motion capture files for the FOHEART H2 data glove project. These files define skeletal hierarchies and recorded motion sequences used for testing, retargeting, and animation pipeline development.

## Files

| File                | Description                                                                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `FullHuman.bvh`     | Full-body human skeleton with fingers. 75 joints, 450 channels per frame, 5 frames at 60fps (Frame Time: 0.016667). Root joint: `Hips`.     |
| `LeftRightHand.bvh` | Extracted left and right hand skeleton only. 43 joints, 258 channels per frame, 5 frames. Root joint: `ROOT`. Derived from `FullHuman.bvh`. |

## BVH File Structure

```
HIERARCHY
ROOT <name>
{
    OFFSET x y z
    CHANNELS 6 Xposition Yposition Zposition Zrotation Yrotation Xrotation
    JOINT <child>
    { ... }
    End Site
    { OFFSET x y z }
}
MOTION
Frames: N
Frame Time: 0.016667
<frame data rows, one per frame, space-separated channel values>
```

* All joints use **6 channels**: 3 position (XYZ) + 3 rotation (ZYX order)

* Channel order in frame data follows the depth-first traversal order of the hierarchy

* `End Site` nodes have no channels and do not appear in frame data

## LeftRightHand.bvh Skeleton Layout

```
ROOT ROOT
├── JOINT RightHand
│   ├── RightHandThumb1 → Thumb2 → Thumb3 → Thumb4
│   ├── RightHandIndex1 → Index2 → Index3 → Index4
│   ├── RightHandMiddle1 → Middle2 → Middle3 → Middle4
│   ├── RightHandRing1 → Ring2 → Ring3 → Ring4
│   └── RightHandPinky1 → Pinky2 → Pinky3 → Pinky4
└── JOINT LeftHand
    ├── LeftHandThumb1 → Thumb2 → Thumb3 → Thumb4
    ├── LeftHandIndex1 → Index2 → Index3 → Index4
    ├── LeftHandMiddle1 → Middle2 → Middle3 → Middle4
    ├── LeftHandRing1 → Ring2 → Ring3 → Ring4
    └── LeftHandPinky1 → Pinky2 → Pinky3 → Pinky4
```

The synthetic `ROOT` joint has zero offset and zero motion data (all 6 values = 0 every frame).

## Deriving LeftRightHand.bvh from FullHuman.bvh

Key mapping from `FullHuman.bvh` joint index (0-based depth-first order):

| Joint                                     | Index | Channel column start |
| ----------------------------------------- | ----- | -------------------- |
| RightHand                                 | 12    | 72                   |
| RightHandPinky4 (last right finger joint) | 32    | —                    |
| LeftHand                                  | 38    | 228                  |
| LeftHandPinky4 (last left finger joint)   | 58    | —                    |

Excluded from `LeftRightHand.bvh` (present in `FullHuman.bvh`):

* `RightForeArmEnd`, `RightArmEnd`, `LeftForeArmEnd`, `LeftArmEnd` — auxiliary end-effector joints on the arm, not part of the hand skeleton

* All torso, head, neck, shoulder, arm, forearm, leg, foot joints

## Modifying BVH Files

When writing scripts to process these files:

1. **Parse hierarchy first** to build a joint→channel-column map before touching frame data

2. **Removing a joint** requires both removing its block from `HIERARCHY` and removing its 6 columns from every frame data row

3. **Column indices shift** after each removal — process removals from highest column index to lowest, or recalculate after each removal

4. **Adding a synthetic root** requires prepending 6 zero values to every frame data row and wrapping existing top-level joints as children

5. Frame data rows are single long space-separated lines — split on whitespace, index by column, rejoin

## Others

BVH文件头，骨骼结构结束后，MOTION行之前不要有空行，否则会导致第三方软件无法打开。



