## ADDED Requirements

### Requirement: End-node bones rendered as position-only joint spheres
The application SHALL render each of the 10 end-node bones (`*3End`) as a joint sphere at the bone's real world-space position. End-node joint actors SHALL use `set_position_only()` and SHALL NOT display local coordinate axis tripods. The 10 end-node bones SHALL be connected to their respective `*3` parent bones by `BoneLinkActor` lines, rendered identically to all other bone links.

#### Scenario: Fingertip sphere appears at real position
- **WHEN** a 42-bone frame is rendered
- **THEN** a joint sphere is visible at each `*3End` bone position, coinciding with the actual fingertip location

#### Scenario: No coordinate axes on end-node joints
- **WHEN** a 42-bone frame is rendered
- **THEN** no RGB axis tripod lines are drawn at any `*3End` joint sphere

#### Scenario: End-node bone link connects parent to fingertip
- **WHEN** a 42-bone frame is rendered
- **THEN** a bone link line connects `RightHandIndex3` to `RightHandIndex3End` (and equivalently for all other finger chains)

## REMOVED Requirements

### Requirement: Fixed-length virtual fingertip bones
**Reason**: Replaced by real end-node position data from the 42-bone skeleton. The fixed-length synthesis was an approximation no longer needed.
**Migration**: The 10 `BoneLinkActor` instances in `_fingertip_actors`, the `FINGERTIP_BONE_LENGTH` constant, and the quaternion Y-axis projection code in `_on_timer` SHALL be removed. The `_FINGERTIP_BONES` list SHALL be removed. End-node bone links are added to `_BONE_LINKS` instead.
