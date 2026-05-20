## 1. Tracking Lifecycle Wiring

- [x] 1.1 Extend the main-window tracking-state callback path so `motionGloveSDK_example3_3dView.py` forwards Vive tracking start/stop events to `ViveTrackerCaliApplyWidget` in addition to the existing scene cleanup behavior.
- [x] 1.2 Add a public tracking-lifecycle entry point to `ui/vive_tracker_caliApply.py` that can start or stop the automatic attach/apply workflow without simulating button clicks.

## 2. Automatic Attach And Apply Flow

- [x] 2.1 Extract reusable left/right helper methods in `ui/vive_tracker_caliApply.py` for attach-axis create/remove and apply-location enable/disable so both manual button handlers and automation share the same success rules, button sync, and logging.
- [x] 2.2 Add per-side pending automation state plus a short-lived Qt retry timer in `ui/vive_tracker_caliApply.py` so tracking start keeps retrying left/right auto-attach until each side succeeds or tracking stops.
- [x] 2.3 Sequence each side's automation so successful left/right attach-axis creation immediately triggers the matching left/right apply-location action and marks that side complete.

## 3. Stop-Tracking Cleanup

- [x] 3.1 Update the tracking-stop automation path to cancel unfinished retries, remove any existing left/right attach-axis actors, and resync both attach-axis button labels to the detached state.
- [x] 3.2 Ensure stop-time cleanup also disables left/right hand root-follow state created by the automatic apply-location flow so a stopped session does not remain attached to removed attach-axis actors.

## 4. Validation

- [x] 4.1 Verify that after successful tracking start, each side auto-attaches as soon as that tracker side has valid pose data and that one unavailable side does not block the other side.
- [x] 4.2 Verify that each side automatically applies left/right hand location only after that side's attach-axis was created successfully, and that stop tracking removes attach-axis actors and clears the attached follow state.