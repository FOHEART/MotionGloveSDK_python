## ADDED Requirements

### Requirement: Lighthouse models are rendered in VTK from SteamVR detection
The system SHALL render one Lighthouse model actor per detected base station in the VTK 3D scene while tracking is enabled.

#### Scenario: One detected Lighthouse is rendered
- **WHEN** tracking is enabled and SteamVR detection reports one Lighthouse base station
- **THEN** exactly one Lighthouse model actor is present in the VTK scene

#### Scenario: Multiple detected Lighthouses are rendered
- **WHEN** tracking is enabled and SteamVR detection reports N Lighthouse base stations where N > 1
- **THEN** exactly N Lighthouse model actors are present in the VTK scene

### Requirement: Lighthouse model asset and decimation are configurable
The system SHALL load Lighthouse geometry from `triad_openvr/lh_basestation_vive/lh_basestation_vive.obj` and SHALL apply mesh decimation using a configurable ratio variable whose default value is 0.5.

#### Scenario: Default decimation is 50 percent
- **WHEN** the application starts with default configuration
- **THEN** Lighthouse mesh decimation ratio is 0.5 before Lighthouse actors are created

#### Scenario: Decimation ratio can be changed
- **WHEN** a non-default decimation ratio value is configured
- **THEN** newly created Lighthouse actors use the configured ratio for mesh decimation

### Requirement: Lighthouse detection and pose sync run in 1 Hz SteamVR timer path
The system SHALL execute Lighthouse detection and actor reconciliation within the existing SteamVR online-state periodic timer, and the effective update frequency SHALL be 1 Hz.

#### Scenario: Detection executes every second
- **WHEN** tracking is enabled and SteamVR is online
- **THEN** Lighthouse presence and pose reconciliation runs once per second

### Requirement: Lighthouse actor transforms reflect detected position and quaternion
For each detected Lighthouse actor, the system SHALL update world position and rotation from detection output on each 1 Hz sync cycle.

#### Scenario: Position update is applied
- **WHEN** a Lighthouse detection update provides a new world position
- **THEN** the corresponding Lighthouse actor position in VTK is updated to that position

#### Scenario: Quaternion rotation update is applied
- **WHEN** a Lighthouse detection update provides a quaternion rotation
- **THEN** the corresponding Lighthouse actor orientation in VTK is updated to match that quaternion

### Requirement: Lighthouse actor lifecycle follows tracking lifecycle
The system SHALL add or remove Lighthouse actors only when tracking is enabled, and SHALL remove all Lighthouse actors when tracking is disabled.

#### Scenario: Actor count changes while tracking enabled
- **WHEN** tracking is enabled and the detected Lighthouse set changes
- **THEN** Lighthouse actors are added or removed to match the detected set

#### Scenario: All Lighthouse actors are removed on tracking disable
- **WHEN** tracking transitions from enabled to disabled
- **THEN** all Lighthouse actors are removed from the VTK scene
