## Why

The left-hand `vive_tracker_attachAxis` currently supports only tracker-local positional offset, so users cannot interactively add a local rotational correction to the attachment frame. This makes it hard to tune the visible attach-axis orientation and immediately see how a corrected local frame should behave before later attachment-driven features consume it.

## What Changes

- Extend the left-hand attach-axis controls in the application-positioning tab by adding three `0-360` sliders for local X/Y/Z rotation below the existing offset inputs.
- Add value labels beside the three left-hand rotation sliders so the actual current degrees are always visible while dragging.
- Change left-hand `vive_tracker_attachAxis` pose composition so an additional local rotation quaternion, built from the slider values, is left-multiplied onto the left tracker rotation while keeping the attach-axis origin at the same tracker-defined offset position.
- Update the left-hand attach-axis actor in real time while the user drags the sliders so the local rotation effect is immediately visible.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `vive-tracker-attach-axis`: expand the left-hand attach-axis behavior to include persistent local rotation UI controls, real-time slider feedback, and left-hand attach-axis pose composition with an additional local rotation applied before offset translation.

## Impact

- Affected code: left attach-axis UI definition in `ui/vive_tracker_caliApply.ui`, left attach-axis UI controller logic in `ui/vive_tracker_caliApply.py`, and left attach-axis pose composition/state in `ui/vive_tracker_widget.py` and `python_draw3d/vive_tracker_attachAxis.py`.
- Affected behavior: the left-hand attach-axis orientation will no longer be identical to the raw tracker orientation when users set a local rotation, but the attach-axis origin will remain at the same tracker-defined offset position; dragging the sliders will update the rendered attach-axis immediately.
- Dependencies: no new external packages are expected; the change should reuse existing quaternion math, attach-axis pose composition, and persisted Qt UI patterns already used for offset editing.