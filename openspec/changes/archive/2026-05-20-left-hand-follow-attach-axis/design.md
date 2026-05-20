## Context

The 3D viewer already supports a left-hand apply-location mode, but the current implementation only offsets every left-hand joint position by the translation from `LeftHand` to the live left tracker position. The cached `global_quats` array remains unchanged, so the rendered hand root does not adopt the tracker attach-axis rotation and the downstream finger joints are not recomputed relative to a rotated hand back.

The code path lives across multiple modules: the application-positioning tab enables the mode through `ViveTrackerWidget`, the viewer caches source skeleton positions/quaternions in `motionGloveSDK_example3_3dView.py`, and the tracker attach-axis pose is already being composed from the left Vive Tracker plus a local offset. This is a cross-cutting behavior change and benefits from a concrete design before implementation.

## Goals / Non-Goals

**Goals:**
- Make left-hand apply-location use the left `vive_tracker_attachAxis` pose instead of the raw tracker origin.
- Replace the rendered `LeftHand` root rotation with the attach-axis rotation when left-hand apply-location is enabled.
- Recompute left-hand child bone positions and rotations from the new attached root pose so finger poses remain consistent relative to the hand back.
- Keep the left-hand skeleton following live attach-axis position changes without requiring a new frame from the glove stream.

**Non-Goals:**
- Changing right-hand apply-location behavior in this change.
- Introducing a full IK solver or changing the source glove frame format.
- Redesigning the existing attach-axis UI or tracker offset editing controls.

## Decisions

### Decision: Treat the attach-axis pose as a replacement left-hand root frame
When left-hand apply-location is enabled, the viewer will treat the left `vive_tracker_attachAxis` position and rotation as the rendered `LeftHand` root frame. The original glove frame's left-hand skeleton will be transformed from its cached source root frame into the attach-axis frame before rendering.

Rationale:
- The user requirement is not only positional attachment but also rotational attachment of the whole left-hand skeleton.
- Using the attach-axis frame directly makes the behavior consistent with the already visible tracker attachment gizmo.

Alternatives considered:
- Keep translation-only follow and just swap the root quaternion: rejected because child positions would no longer match the rotated root.
- Drive the hand from raw tracker origin instead of attach-axis: rejected because the request explicitly names `vive_tracker_attachAxis` as the attachment source.

### Decision: Recompute the left-hand skeleton from cached source local offsets during render
The render loop will continue caching the original `positions` and `global_quats` for the current glove frame. When left-hand apply-location is enabled, a new left-hand follow transform will be applied to the cached left-hand slice by:
- reading the cached source root position/quaternion for `LeftHand`
- reading the current attach-axis target position/quaternion
- computing the delta rotation between source root frame and target attach-axis frame
- rotating each left-hand bone's position offset from the source root and composing each left-hand bone quaternion with the same delta rotation

Rationale:
- This keeps finger articulation from the glove frame while applying one coherent rigid transform to the whole left-hand skeleton.
- It avoids mutating the source glove frame and naturally supports repeated recomputation when the attach-axis moves between frames.

Alternatives considered:
- Recompute child bones from parent-by-parent forward kinematics using inferred local transforms: rejected because the viewer already has stable cached world-space poses, and a rigid root-frame delta is simpler and less error-prone.
- Modify VTK actors directly without updating `positions/global_quats`: rejected because links, end nodes, and cached redraw flow all already depend on those arrays.

### Decision: Expose current left attach-axis pose from `ViveTrackerWidget`
`ViveTrackerWidget` will provide a pose accessor for the live left attach-axis, returning both position and quaternion when valid. The viewer follow logic will query this accessor instead of rebuilding the pose from multiple internal pieces.

Rationale:
- The attach-axis pose is already owned by `ViveTrackerWidget` and should stay the single source of truth.
- A dedicated accessor keeps `motionGloveSDK_example3_3dView.py` from depending on widget internals such as offset storage or tracker data fields.

Alternatives considered:
- Recompute attach-axis pose in the main window: rejected because it duplicates tracker pose composition logic.
- Read the VTK actor transform back from the attach-axis actor: rejected because the render logic should depend on semantic pose data, not scene actor state.

## Risks / Trade-offs

- [Rigid root-frame delta may expose mismatches between source root orientation and expected hand local basis] → Mitigation: define the transform explicitly as source-root-to-attach-axis and validate with known hand poses.
- [Follow updates without new glove frames could drift if they mutate cached source data] → Mitigation: always start from the unchanged cached source positions/quaternions before applying the live attach-axis transform.
- [Left-hand links and end nodes may visually break if only joints are updated] → Mitigation: keep using the transformed `positions/global_quats` arrays so existing joint/link drawing remains consistent.
- [Attach-axis pose may be unavailable while apply-location remains enabled] → Mitigation: fall back to the existing cached scene when the attach-axis pose accessor returns `None`.

## Migration Plan

No data migration is needed. This is a runtime behavior change in the viewer.

Implementation can proceed in three steps:
- add left attach-axis pose accessors to `ViveTrackerWidget`
- replace the current translation-only left-hand follow logic with root-frame transform recomputation in `motionGloveSDK_example3_3dView.py`
- validate both same-frame and cached-frame follow behavior when the attach-axis moves or rotates

Rollback is straightforward: restore the previous translation-only `_apply_hand_tracker_follow()` behavior and stop querying the attach-axis pose accessor.

## Open Questions

- The request only mentions the left hand; right-hand rotational follow remains out of scope unless proposed separately.
- If future hardware data reveals a systematic basis mismatch between glove `LeftHand` and attach-axis frames, that correction should be proposed as a separate calibration capability rather than folded into this behavior change implicitly.