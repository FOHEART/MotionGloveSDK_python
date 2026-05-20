## Context

The current 3D viewer already loads a left/right Vive Tracker model and a tracker-origin local axes actor, then keeps both synchronized through `ViveTrackerWidget.update_model_pose()`. The application-positioning tab is also already separated into `ui/vive_tracker_caliApply.py` plus a `.ui` file, and its buttons call methods on `ViveTrackerWidget` rather than manipulating VTK scene objects directly.

This change adds a second coordinate system that is not placed at the tracker origin. Instead, it must be composed from the left-hand tracker's final display pose plus a tracker-local offset vector `(0, 0, 0.2)` meters, while preserving the tracker orientation. Because the feature touches VTK actor creation, real-time pose update flow, and tab UI state, a design document is warranted.

## Goals / Non-Goals

**Goals:**
- Add a left-hand Vive Tracker attachment-axis that is rendered at a tracker-local offset and rotates exactly with the tracker.
- Keep the new axis synchronized through the existing 60 Hz tracker pose update path so calibration-adjusted position and quaternion remain the single source of truth.
- Expose the feature in the application-positioning tab through a `QGroupBox` and a single toggle button whose label reflects whether the attachment point exists.
- Isolate attach-axis construction and update logic in a dedicated Python module named `vive_tracker_attachAxis`.

**Non-Goals:**
- Adding right-hand attachment-axis controls.
- Adding user-editable offset or axis-length configuration in this change.
- Persisting attach-axis enabled state across application restarts.

## Decisions

### Decision: Put VTK attach-axis construction in a dedicated helper module
The change will add a new helper module named `vive_tracker_attachAxis` in the VTK helper area, responsible for building and updating the attach-axis actor.

Rationale:
- The feature is VTK-specific actor composition, not generic UI code.
- It keeps `motionGloveSDK_example3_3dView.py` and `ui/vive_tracker_widget.py` focused on orchestration rather than geometry setup.
- It satisfies the explicit requirement that the attach-axis live in its own Python file.

Alternatives considered:
- Inline actor creation in `motionGloveSDK_example3_3dView.py`: rejected because it mixes scene setup details into the main window.
- Inline actor creation in `ui/vive_tracker_widget.py`: rejected because that widget already coordinates multiple responsibilities and should not own VTK geometry definitions directly.

### Decision: Make `ViveTrackerWidget` own the attach-axis lifecycle and pose updates
`ViveTrackerWidget` will store the left-hand attach-axis actor reference and enabled state, create/remove the actor through its existing renderer access, and refresh the actor inside the same pose-update path that already updates tracker models and tracker-origin axes.

Rationale:
- `ViveTrackerWidget` already owns the current tracker display position/quaternion composition, actor references, renderer reference, and render-request callback.
- The application-positioning tab already talks to `ViveTrackerWidget`, so the new button can reuse the established control flow.
- Updating the attach-axis in the same place as the tracker model avoids duplicate pose polling and prevents drift between tracker origin axes and attach-axis.

Alternatives considered:
- Let the tab widget manipulate renderer actors directly: rejected because it would couple a UI tab to VTK scene internals.
- Let the main window poll and update the attach-axis separately: rejected because it duplicates pose-composition logic that already lives in `ViveTrackerWidget`.

### Decision: Compose attach-axis position from final display pose plus rotated local offset
The attach-axis origin will be computed as:

- tracker final display position, after the existing position-bias and calibration-rotation logic
- plus the offset vector `(0, 0, 0.2)` meters rotated by the tracker's final display quaternion

The attach-axis orientation will reuse the tracker's final display quaternion unchanged.

Rationale:
- The user explicitly requested that the attach-axis stay in the tracker local coordinate system and follow both movement and rotation.
- Reusing the final display pose ensures the attach-axis stays aligned with whatever calibration transforms are already visible in the scene.

Alternatives considered:
- Add the offset in world space without rotation: rejected because the axis would not remain fixed relative to the tracker body when the tracker rotates.
- Base the offset on raw origin pose instead of final display pose: rejected because it would diverge from the tracker model shown to the user.

### Decision: Use a two-state left-hand toggle in the application-positioning tab
The application-positioning tab will gain a new `QGroupBox` containing one button. When no left-hand attach-axis exists, the button text is `附加左手附加点`; after successful creation it changes to `删除左手附加点`; clicking again removes the actor and restores the original label.

Rationale:
- The user asked for a single-button toggle with explicit text change.
- A group box keeps the new control visually separated from the existing left/right root-follow actions.

Alternatives considered:
- Separate add/remove buttons: rejected because the requested interaction is a single toggle control.
- A checkbox: rejected because the requested control text is action-oriented and should communicate success/failure clearly.

## Risks / Trade-offs

- [Tracker actor and attach-axis can get out of sync if updated in different code paths] → Mitigation: update both from `ViveTrackerWidget.update_model_pose()` using the same final pose inputs.
- [Attach-axis creation may fail when the left tracker is offline or has no valid pose] → Mitigation: treat creation as conditional on a valid left tracker pose and leave the button text unchanged on failure.
- [New actor references can leak in the renderer if tracker unload and manual delete paths diverge] → Mitigation: centralize add/remove helpers in `ViveTrackerWidget` and clear the actor reference in both manual removal and tracker teardown paths.
- [A 200 mm offset may place the axis visually far from the tracker and expose transform mistakes] → Mitigation: define the offset in one constant and verify it against tracker rotation scenarios during implementation.

## Migration Plan

No data migration is required. The feature is additive and runtime-only.

Implementation rollout can proceed in three steps:
- add the helper module and `ViveTrackerWidget` lifecycle/update methods
- wire the new toggle control into `ui/vive_tracker_caliApply.ui` and `ui/vive_tracker_caliApply.py`
- validate creation, following behavior, and deletion with a live or simulated left-hand tracker

Rollback is straightforward: remove the new tab control, stop creating the attach-axis actor, and delete the helper module.

## Open Questions

- The request fixes the default offset to `(0, 0, 0.2)` meters; no runtime editing UI is planned unless a later change asks for configurable attachment points.
- The request only names the left-hand tracker button; if a symmetric right-hand feature is needed later, it should be proposed as a follow-up capability rather than inferred here.