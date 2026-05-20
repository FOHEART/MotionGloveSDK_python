## ADDED Requirements

### Requirement: Left-hand apply-location uses left tracker attach-axis pose
When left-hand apply-location is enabled, the viewer SHALL use the live left `vive_tracker_attachAxis` pose as the rendered `LeftHand` root frame instead of using only the raw left tracker position.

#### Scenario: Left-hand root moves to the attach-axis position
- **WHEN** left-hand apply-location is enabled and the left `vive_tracker_attachAxis` has a valid pose
- **THEN** the rendered `LeftHand` root is positioned at the left `vive_tracker_attachAxis` position

#### Scenario: Left-hand root adopts the attach-axis rotation
- **WHEN** left-hand apply-location is enabled and the left `vive_tracker_attachAxis` has a valid pose
- **THEN** the rendered `LeftHand` root orientation matches the left `vive_tracker_attachAxis` orientation

### Requirement: Left-hand child bones are recomputed from the attached root frame
When left-hand apply-location is enabled, the viewer SHALL recompute the rendered left-hand child bone positions and rotations from the original left-hand source pose under the new attached `LeftHand` root frame before drawing.

#### Scenario: Finger pose stays consistent relative to the hand back
- **WHEN** left-hand apply-location is enabled for a glove frame with articulated fingers
- **THEN** each rendered left-hand child bone preserves its relative pose within the left hand while the whole left-hand skeleton is rotated by the attach-axis root frame

#### Scenario: Left-hand links remain consistent after recomputation
- **WHEN** left-hand apply-location is enabled and the left-hand child bone positions are recomputed
- **THEN** the rendered left-hand joint actors and link actors remain connected using the recomputed positions

### Requirement: Left-hand follow updates when attach-axis pose changes between frames
The viewer SHALL keep the rendered left-hand skeleton synchronized with left `vive_tracker_attachAxis` pose changes even when no new glove frame has arrived, by reapplying the left-hand attached-root transform to cached source left-hand skeleton data.

#### Scenario: Attach-axis translation updates cached left-hand scene
- **WHEN** left-hand apply-location is enabled, no new glove frame is pending, and the left `vive_tracker_attachAxis` position changes
- **THEN** the rendered left-hand skeleton moves to follow the new left `vive_tracker_attachAxis` position

#### Scenario: Attach-axis rotation updates cached left-hand scene
- **WHEN** left-hand apply-location is enabled, no new glove frame is pending, and the left `vive_tracker_attachAxis` rotation changes
- **THEN** the rendered left-hand skeleton rotates to follow the new left `vive_tracker_attachAxis` rotation while preserving the source left-hand articulation