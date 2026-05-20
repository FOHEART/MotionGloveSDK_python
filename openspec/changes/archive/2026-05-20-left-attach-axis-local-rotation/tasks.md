## 1. Left Rotation UI Controls

- [x] 1.1 Add persisted left local rotation sliders and adjacent value labels to `ui/vive_tracker_caliApply.ui` below the existing left attach-axis offset controls.
- [x] 1.2 Extend `ui/vive_tracker_caliApply.py` to resolve the new left slider and label widgets safely, initialize them from current left attach-axis local rotation state, and keep the displayed degree labels in sync.

## 2. Left Attach-Axis Local Rotation Composition

- [x] 2.1 Add left attach-axis local rotation degree state plus quaternion conversion helpers in the attach-axis runtime path so the left UI can read and update the current local rotation values.
- [x] 2.2 Update left attach-axis pose composition so the left local rotation quaternion is left-multiplied onto the left tracker rotation before the local offset vector is rotated and translated.
- [x] 2.3 Ensure all left attach-axis pose accessors and update paths reuse the same composed pose so live preview and downstream left attach-axis consumers see the same final transform.

## 3. Real-Time Preview Validation

- [x] 3.1 Connect left slider `valueChanged` updates so dragging any left rotation slider immediately recomputes and redraws the left `vive_tracker_attachAxis`.
- [x] 3.2 Verify that the left slider value labels show the actual current X/Y/Z degree values while dragging.
- [x] 3.3 Verify that the left attach-axis final pose uses rotation-before-translation, with the local offset rotated by the composed quaternion rather than translating first.