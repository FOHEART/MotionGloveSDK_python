## ADDED Requirements

### Requirement: Left-hand attach-axis local rotation can be edited from the application-positioning tab
The application-positioning tab SHALL provide three persisted left-hand local rotation sliders below the existing left attach-axis offset controls, one each for X, Y, and Z rotation, and each slider SHALL cover the range `0-360` degrees.

#### Scenario: Left rotation sliders are available in the left attach-axis group
- **WHEN** the user opens the application-positioning tab
- **THEN** the left attach-axis group shows three left local rotation sliders for X, Y, and Z below the left offset inputs

#### Scenario: Left rotation slider values are visible while dragging
- **WHEN** the user drags any left local rotation slider
- **THEN** the label beside that slider shows the current actual degree value in real time

### Requirement: Left-hand attach-axis updates immediately from local rotation slider changes
The viewer SHALL recompute and render the left-hand `vive_tracker_attachAxis` immediately when the user changes any left local rotation slider value.

#### Scenario: Dragging a left rotation slider updates the attach-axis orientation
- **WHEN** the left `vive_tracker_attachAxis` is visible and the user changes a left local rotation slider value
- **THEN** the rendered left attach-axis orientation updates immediately without requiring a separate confirm action

#### Scenario: Slider changes update the composed local rotation state
- **WHEN** the user changes any left local rotation slider value
- **THEN** the viewer updates the stored left attach-axis local rotation state used to compute the final left attach-axis quaternion

## MODIFIED Requirements

### Requirement: Left-hand attach-axis uses tracker-local offset composition
The left-hand `vive_tracker_attachAxis` SHALL use the left-hand Vive Tracker as its pose source, SHALL start from the tracker's current display position and rotation, SHALL build an additional local rotation quaternion from the configured left-hand local X/Y/Z rotation values, SHALL left-multiply that local rotation onto the left-hand Vive Tracker rotation for the final attach-axis orientation, and SHALL keep its own origin at the tracker-local offset vector `(0, 0, 0.2)` meters transformed only by the left-hand Vive Tracker rotation.

#### Scenario: Attach-axis origin stays at the tracker-defined offset location
- **WHEN** the left-hand attach-axis is visible and the left-hand Vive Tracker pose is updated
- **THEN** the attach-axis origin is rendered at the tracker's current display position plus the tracker-local offset vector `(0, 0, 0.2)` meters transformed by the left-hand Vive Tracker rotation

#### Scenario: Attach-axis uses tracker rotation plus additional local rotation
- **WHEN** the left-hand attach-axis is visible and either the left-hand Vive Tracker rotates or the configured left local rotation values change
- **THEN** the attach-axis orientation equals the left local rotation quaternion left-multiplied onto the left-hand Vive Tracker orientation

#### Scenario: Local rotation does not move the attach-axis origin
- **WHEN** the left-hand attach-axis is visible and the configured left local rotation values change while the left-hand Vive Tracker pose stays the same
- **THEN** the attach-axis world position remains unchanged and only the attach-axis orientation is updated

### Requirement: Left-hand attach-axis renders as a 20 mm local coordinate system
The left-hand `vive_tracker_attachAxis` SHALL render a local X/Y/Z coordinate system whose three axes are each `20 mm` long.

#### Scenario: Attach-axis geometry uses requested axis length
- **WHEN** the left-hand attach-axis is created successfully
- **THEN** the rendered X, Y, and Z axes are each 20 mm long and use the same local coordinate orientation convention as the Vive Tracker