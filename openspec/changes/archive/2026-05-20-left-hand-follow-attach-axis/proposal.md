## Why

The current left-hand tracker follow mode only translates the rendered left-hand skeleton so that the `LeftHand` root reaches the left Vive Tracker position. It does not rotate the hand root or recompute downstream finger poses from the `vive_tracker_attachAxis`, so the skeleton cannot be fully attached to the tracker-provided attachment frame.

## What Changes

- Change left-hand apply-location behavior so the whole left-hand skeleton is attached to the left Vive Tracker `vive_tracker_attachAxis` instead of the raw tracker origin.
- Replace the rendered `LeftHand` root rotation with the `vive_tracker_attachAxis` rotation when left-hand apply-location is enabled.
- Recompute the left-hand child bone positions and rotations relative to the rotated `LeftHand` root before drawing, so each finger keeps its pose relative to the hand back under the new attached frame.
- Ensure the whole left-hand skeleton continues to move when the left `vive_tracker_attachAxis` position changes, using the attach-axis as the live pose source.

## Capabilities

### New Capabilities
- `left-hand-follow-attach-axis`: Attach the rendered left-hand skeleton root to the left tracker attach-axis pose, including root rotation replacement and downstream left-hand pose recomputation.

### Modified Capabilities
- None.

## Impact

- Affected code: left-hand tracker follow logic in `motionGloveSDK_example3_3dView.py`, pose composition and attach-axis pose access in `ui/vive_tracker_widget.py`, and the existing application-positioning controls in `ui/vive_tracker_caliApply.py`.
- Affected behavior: enabling left-hand apply-location will no longer be translation-only; it will rotate and reposition the full left-hand skeleton using the attach-axis pose.
- Dependencies: no new external packages are expected; the change should reuse existing skeleton hierarchy data, tracker attach-axis pose composition, and VTK render flow.