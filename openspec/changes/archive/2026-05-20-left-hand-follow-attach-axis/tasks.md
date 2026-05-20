## 1. Attach-Axis Pose Access

- [x] 1.1 Add a left attach-axis pose accessor in `ui/vive_tracker_widget.py` that returns the current left `vive_tracker_attachAxis` position and quaternion when valid.
- [x] 1.2 Ensure the left attach-axis pose accessor reuses the existing tracker and attach-axis offset composition logic instead of duplicating divergent pose state.

## 2. Left-Hand Follow Recompute

- [x] 2.1 Replace the current translation-only left-hand branch in `motionGloveSDK_example3_3dView.py` with a transform that maps the cached source left-hand root frame to the live left attach-axis frame.
- [x] 2.2 Recompute left-hand child joint positions and global quaternions from the attached root transform before updating joint and link actors.

## 3. Cached-Frame Follow Validation

- [x] 3.1 Verify that enabling left-hand apply-location positions the rendered `LeftHand` root at the left `vive_tracker_attachAxis` position and aligns its rotation to the attach-axis rotation.
- [x] 3.2 Verify that the rendered left-hand fingers keep their articulation relative to the hand back after the attached-root transform is applied.
- [x] 3.3 Verify that cached-frame redraws continue following left `vive_tracker_attachAxis` translation and rotation changes when no new glove frame has arrived.