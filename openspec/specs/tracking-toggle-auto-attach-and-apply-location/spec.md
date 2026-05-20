# tracking-toggle-auto-attach-and-apply-location Specification

## Purpose
TBD - created by archiving change auto-attach-and-apply-location-on-tracking-toggle. Update Purpose after archive.
## Requirements
### Requirement: Successful tracking start automatically attaches each hand to its tracker attach-axis when that side becomes pose-valid
After Vive tracker tracking starts successfully, the viewer SHALL automatically attempt left-hand and right-hand attach-axis creation for each side independently, using the same success rules and visible UI state as the application-positioning tab attach-axis actions.

#### Scenario: Left side auto-attaches after tracking start once the left tracker has a valid pose
- **WHEN** tracking has started successfully and the left Vive Tracker later has a valid pose while no left attach-axis exists
- **THEN** the viewer creates the left `vive_tracker_attachAxis` automatically and the left attach-axis button state matches the manual attached state

#### Scenario: Right side auto-attaches after tracking start once the right tracker has a valid pose
- **WHEN** tracking has started successfully and the right Vive Tracker later has a valid pose while no right attach-axis exists
- **THEN** the viewer creates the right `vive_tracker_attachAxis` automatically and the right attach-axis button state matches the manual attached state

#### Scenario: One side failing to attach does not block the other side
- **WHEN** tracking has started successfully, one side still has no valid pose, and the other side already has a valid pose
- **THEN** the pose-valid side is still auto-attached without waiting for the unavailable side

### Requirement: Successful auto-attachment automatically applies the matching hand location for that side
Whenever an automatic left-hand or right-hand attach-axis creation succeeds, the viewer SHALL automatically invoke the matching apply-location behavior for that side so the rendered hand root follows the newly created attach-axis.

#### Scenario: Left auto-attach automatically applies left-hand location
- **WHEN** the left attach-axis is created successfully by the tracking-start automation
- **THEN** the rendered `LeftHand` root begins following the left attach-axis without requiring the user to click `应用左手定位`

#### Scenario: Right auto-attach automatically applies right-hand location
- **WHEN** the right attach-axis is created successfully by the tracking-start automation
- **THEN** the rendered `RightHand` root begins following the right attach-axis without requiring the user to click `应用右手定位`

#### Scenario: Failed auto-attach does not auto-apply that side
- **WHEN** automatic attach-axis creation for a side does not succeed
- **THEN** the viewer does not enable apply-location for that side until attach-axis creation succeeds later

### Requirement: Tracking stop clears automatic attach/apply session state for both hands
When Vive tracker tracking stops, the viewer SHALL cancel any pending tracking-start automation, remove existing left/right attach-axis actors, and restore both hands to a detached non-following state for that stopped tracking session.

#### Scenario: Stop tracking removes both attach-axis actors
- **WHEN** tracking stops while the left and/or right attach-axis exists
- **THEN** the viewer removes every existing hand attach-axis actor and the left/right attach-axis button state matches the manual detached state

#### Scenario: Stop tracking clears hand follow state created by auto-apply
- **WHEN** tracking stops after automatic left-hand and/or right-hand apply-location has been enabled
- **THEN** the corresponding hand root-follow state is disabled so no stopped session remains attached to a removed attach-axis

#### Scenario: Stop tracking cancels pending auto-attach retries
- **WHEN** tracking stops before one or both sides have completed automatic attach/apply
- **THEN** the viewer stops retrying unfinished automatic attach/apply work for that stopped session

