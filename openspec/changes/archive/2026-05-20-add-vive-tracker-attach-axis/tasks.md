## 1. Attach-Axis Core

- [x] 1.1 Add the dedicated `vive_tracker_attachAxis` helper module to build the 20 mm local XYZ actor and expose pose-update utilities for a tracker-local offset origin.
- [x] 1.2 Extend `ui/vive_tracker_widget.py` with left-hand attach-axis state, actor references, and create/remove/query methods that guard on a valid left-hand tracker pose.
- [x] 1.3 Update the existing left-hand tracker pose refresh path so the attach-axis origin is composed from the tracker's final display pose plus the rotated `(0, 0, 0.2)` meter local offset, and ensure tracker teardown also removes the attach-axis actor.

## 2. Application-Positioning UI

- [x] 2.1 Update `ui/vive_tracker_caliApply.ui` to add a dedicated `QGroupBox` and toggle button for the left-hand attachment point.
- [x] 2.2 Update `ui/vive_tracker_caliApply.py` to wire the new toggle button to `ViveTrackerWidget`, switching the label between `附加左手附加点` and `删除左手附加点` only when create/remove operations succeed.

## 3. Verification

- [x] 3.1 Verify that clicking the new button with a valid left-hand tracker creates the attach-axis actor, renders 20 mm axes, and clicking again removes it cleanly.
- [x] 3.2 Verify that the attach-axis keeps the same orientation as the left-hand tracker and preserves the `(0, 0, 0.2)` meter tracker-local offset while the tracker translates and rotates.
- [x] 3.3 Verify that offline or invalid-pose conditions do not create the actor and do not flip the button text, and that tracker unload clears any active attach-axis state.