## Why

Starting Vive tracker tracking currently leaves the user to manually switch to the application-positioning tab, attach the left and right tracker attach-axis actors, and then apply left and right hand location. That extra sequence is repetitive and error-prone, especially because the desired outcome is always to attach both hand roots to their corresponding attach-axis as soon as tracking starts successfully.

## What Changes

- Add automatic tracking-start orchestration that, after tracking starts successfully, attempts the same left and right attach-axis actions currently exposed in the application-positioning tab.
- After each side's attach-axis is created successfully, automatically invoke the corresponding left or right apply-location action so the hand skeleton root follows that attach-axis without requiring a second manual click.
- Add automatic tracking-stop cleanup that removes any left and right attach-axis actors created for live tracking and restores the positioning UI to a consistent detached state.
- Keep the automation aligned with the existing manual button behavior so start/stop tracking reuses the same attach/apply success rules, button text synchronization, and logging paths rather than introducing a separate code path.

## Capabilities

### New Capabilities
- `tracking-toggle-auto-attach-and-apply-location`: automatically attach left/right tracker attach-axis actors after a successful tracking start, automatically apply left/right hand location after successful attachment, and remove the attach-axis state when tracking stops.

### Modified Capabilities
- None.

## Impact

- Affected code: tracking lifecycle control in `ui/vive_tracker_widget.py`, application-positioning orchestration in `ui/vive_tracker_caliApply.py`, and any startup wiring that connects the tracking widget to the positioning widget.
- Affected behavior: successful tracking start now triggers the left/right attach-axis and left/right apply-location workflow automatically; tracking stop now cleans up the attach-axis state automatically.
- Dependencies: no new external dependencies are required; the change reuses the existing attach-axis creation/removal and hand-root follow logic.