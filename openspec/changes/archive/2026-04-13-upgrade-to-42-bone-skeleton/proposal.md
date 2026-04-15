## Why

The hardware sender has been upgraded from a 32-bone to a 42-bone skeleton model. The 10 new bones are fingertip end-nodes (`*3End`) that carry real position data, replacing the previous fixed-length virtual fingertip segments synthesized in software.

## What Changes

- **BREAKING**: `KHHS32_SKELETON_COUNT` (32) replaced by a 42-bone constant throughout the codebase.
- `definitions.py`: add 10 new `BoneIndex` enum members (`RightHandThumb3End` … `LeftHandPinky3End`) and update `BONE_NAMES`, `KHHS_SKELETON_COUNT`.
- `motionGloveSDK_example3_3dView.py`:
  - Replace the 10 fixed-length fingertip `BoneLinkActor` segments (`_fingertip_actors`) with 10 real `BoneJointActor` joint spheres, one per `*3End` bone.
  - Add 10 `BoneLinkActor` entries in `_BONE_LINKS` connecting each `*3End` to its parent `*3` bone.
  - End-node joint actors must **not** display local coordinate axes (position-only rendering).
  - Remove `FINGERTIP_BONE_LENGTH` constant and all related quaternion-based direction code.
- `_BONE_PARENT` lookup table extended to cover all 42 bones.
- `_FINGERTIP_BONES` list and `self._fingertip_actors` removed entirely.

## Capabilities

### New Capabilities

- `42-bone-skeleton`: Support for the 42-bone hand skeleton model including 10 fingertip end-nodes with real position data and no rotation.

### Modified Capabilities

- `pyside6-main-window`: The main window rendering loop must handle 42 bones, render end-nodes as position-only joint spheres (no axes), and remove fixed-length fingertip synthesis.

## Impact

- `src/definitions.py` — BoneIndex enum, BONE_NAMES, skeleton count constant.
- `motionGloveSDK_example3_3dView.py` — actor lists, bone links, render loop, constants.
- No changes to SDK networking, CSV reader, or UI panel code.
- Existing 32-bone CSV files will fail to parse (wrong bone count) — expected, out of scope.
