## Context

The 3D viewer currently models both hands as 32 bones (16 per hand). Each finger chain ends at `*3` (e.g., `RightHandIndex3`), and the viewer synthesizes a virtual fingertip segment by extending a fixed length (`FINGERTIP_BONE_LENGTH = 0.030 m`) along the local Y-axis derived from the bone's global quaternion.

The hardware sender now transmits 42 bones per frame: the original 32 plus 10 end-nodes (`*3End`), one per finger chain. Each end-node carries a real world-space position (the actual fingertip location) and a zero rotation `(0, 0, 0)` — the rotation is not meaningful and should not be rendered as local axes.

The packet format is unchanged (`pos euler ZXY relative`); there are simply 10 more bone slots. The existing `glove_frame_assembler` and `decode_glove_csv` pipeline is generic over bone count, so no changes are needed there beyond updating the constant.

## Goals / Non-Goals

**Goals:**
- Update `KHHS_SKELETON_COUNT` from 32 → 42 and add the 10 new `BoneIndex` entries.
- Render each `*3End` bone as a joint sphere using its real position.
- Connect each `*3End` sphere to its `*3` parent with a bone link line.
- Suppress local coordinate axes on end-node joints (position-only rendering).
- Remove the fixed-length fingertip synthesis code entirely.

**Non-Goals:**
- CSV playback compatibility with old 32-bone files (out of scope).
- Any change to the UDP networking, packet assembly, or CSV reader.
- Modifying rotation/quaternion accumulation logic (end-nodes have zero rotation, so `global_quats[i]` will simply equal the identity-ish value; the accumulation code is harmless to leave as-is).

## Decisions

### Use `set_position_only()` for end-nodes, not `set_pose()`

End-node rotations are `(0,0,0)` by definition. Passing them through quaternion accumulation produces the parent's global rotation, which is meaningless for a fingertip. Rendering axes would add visual noise. Using the existing `BoneJointActor.set_position_only()` path is correct, concise, and requires no new API.

Alternative considered: render axes with identity quaternion — rejected because axes pointing world-forward on fingertips would be confusing.

### Extend `_BONE_LINKS` rather than a separate end-link list

The 10 new `*3` → `*3End` links are structurally identical to every other parent→child bone link. Folding them into `_BONE_LINKS` keeps the render loop uniform and avoids a second actor list.

Alternative considered: keep a separate `_fingertip_link_actors` list — rejected; unnecessary complexity now that real positions are available.

### Remove `_FINGERTIP_BONES` and `_fingertip_actors` entirely

The old virtual fingertip system (`FINGERTIP_BONE_LENGTH`, quaternion Y-axis projection, `_fingertip_actors`) served as an approximation. With real end-node positions the approximation is obsolete. Complete removal avoids dead code.

### Identify end-nodes by name suffix, not a hard-coded index set

The `_END_BONE_INDICES` set (built once at module load from `BoneIndex` names ending in `End`) drives the `set_position_only` branch in `_on_timer`. This is self-documenting and robust against future index renumbering.

## Risks / Trade-offs

- **Old 32-bone UDP streams** will silently produce garbled frames because `decode_glove_csv` will see too few values and return `None`. → Acceptable; the sender has been upgraded; this is expected behavior.
- **`global_quats` accumulation on end-nodes** will compute a result (parent quat × identity ≈ parent quat) that is never used. Minor wasted CPU; harmless. → No mitigation needed.

## Migration Plan

1. Update `definitions.py` (new enum members, updated count and name list).
2. Update `motionGloveSDK_example3_3dView.py` (constants, actor lists, render loop).
3. Run existing CI smoke test (`MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0`) — pipeline count change is the only observable effect in no-render mode; test should still pass.
4. Verify visually with live 42-bone UDP stream.

No rollback needed — change is confined to two files with no external API surface.
