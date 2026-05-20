## ADDED Requirements

### Requirement: Left-hand tracker attachment axis can be toggled from the application-positioning tab
The application-positioning tab SHALL provide a dedicated `QGroupBox` for the left-hand tracker attachment point and SHALL include a button that creates or removes the attachment axis without restarting the viewer.

#### Scenario: Left-hand attach-axis is created from the tab
- **WHEN** the user opens the application-positioning tab and clicks `附加左手附加点` while the left-hand Vive Tracker has a valid pose
- **THEN** the viewer creates a left-hand `vive_tracker_attachAxis` actor, adds it to the VTK scene, and changes the button text to `删除左手附加点`

#### Scenario: Left-hand attach-axis is removed from the tab
- **WHEN** the left-hand attach-axis already exists and the user clicks `删除左手附加点`
- **THEN** the viewer removes the left-hand `vive_tracker_attachAxis` actor from the VTK scene and restores the button text to `附加左手附加点`

#### Scenario: Creation is rejected when the left tracker has no valid pose
- **WHEN** the user clicks `附加左手附加点` and the left-hand Vive Tracker is offline or has no valid pose
- **THEN** no attach-axis actor is created and the button text remains `附加左手附加点`

### Requirement: Left-hand attach-axis uses tracker-local offset composition
The left-hand `vive_tracker_attachAxis` SHALL use the left-hand Vive Tracker as its pose source, SHALL start from the tracker's current display position, and SHALL place its own origin at the tracker-local offset vector `(0, 0, 0.2)` meters.

#### Scenario: Attach-axis origin is offset from tracker origin
- **WHEN** the left-hand attach-axis is visible and the left-hand Vive Tracker pose is updated
- **THEN** the attach-axis origin is rendered at the tracker's current display position plus the tracker-local offset vector `(0, 0, 0.2)` meters transformed by the tracker's current display rotation

#### Scenario: Attach-axis rotates with the tracker
- **WHEN** the left-hand attach-axis is visible and the left-hand Vive Tracker rotates
- **THEN** the attach-axis orientation remains identical to the left-hand Vive Tracker orientation

#### Scenario: Attach-axis translates with the tracker
- **WHEN** the left-hand attach-axis is visible and the left-hand Vive Tracker moves
- **THEN** the attach-axis origin moves with the tracker while preserving the same tracker-local offset

### Requirement: Left-hand attach-axis renders as a 20 mm local coordinate system
The left-hand `vive_tracker_attachAxis` SHALL render a local X/Y/Z coordinate system whose three axes are each `20 mm` long.

#### Scenario: Attach-axis geometry uses requested axis length
- **WHEN** the left-hand attach-axis is created successfully
- **THEN** the rendered X, Y, and Z axes are each 20 mm long and use the same local coordinate orientation convention as the Vive Tracker