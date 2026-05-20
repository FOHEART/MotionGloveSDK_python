## Why

The 3D viewer currently shows each Vive Tracker model and its local axes at the tracker origin, but it cannot visualize an attachment point that is offset from the tracker in tracker-local space. A dedicated attach-axis is needed so users can verify where a left-hand attachment point sits relative to the tracker while the tracker moves and rotates in real time.

## What Changes

- Add a new Vive Tracker attachment-axis visualization that starts from the tracker model position, applies a configurable local-space offset vector in meters, and renders a second local coordinate system aligned with the tracker orientation.
- Define the attachment-axis in a dedicated Python module named `vive_tracker_attachAxis` so creation, pose updates, and teardown are isolated from the main window wiring.
- Set the attachment-axis default offset to `(0, 0, 0.2)` meters and its X/Y/Z axis lengths to `20 mm`.
- Update the application positioning tab to include a `QGroupBox` with a toggle button for the left-hand tracker attachment point; the button creates the attach-axis on first click and removes it on second click.
- Ensure the button text reflects the current state: `附加左手附加点` before creation and `删除左手附加点` after successful attachment.

## Capabilities

### New Capabilities
- `vive-tracker-attach-axis`: Visualize and manage a toggleable tracker-local attachment coordinate system for the left-hand Vive Tracker, including UI control from the application positioning tab.

### Modified Capabilities
- None.

## Impact

- Affected code: the VTK tracker model load/update flow in `motionGloveSDK_example3_3dView.py`, the left-hand application-positioning UI in `ui/vive_tracker_caliApply.py` and its `.ui` file, and a new attach-axis helper module.
- Affected behavior: users can add or remove a left-hand tracker attachment axis without restarting the viewer, and the attach-axis follows the tracker pose using tracker-local offset composition.
- Dependencies: no new external packages are expected; implementation should reuse the existing VTK actor and Vive Tracker update pipeline.