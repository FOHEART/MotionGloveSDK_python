## Context

`ViveTrackerWidget` owns the actual tracking lifecycle and emits a `tracking_state_changed_callback` after `_start_tracking()` succeeds and after `_stop_tracking()` finishes clearing tracking state. The manual attach-axis and apply-location actions already live in `ViveTrackerCaliApplyWidget`, which owns the positioning-tab buttons, button text synchronization, and calls into `ViveTrackerWidget` for left/right attach-axis creation, removal, and left/right hand root follow.

The requested behavior is cross-cutting: tracking start in one widget must trigger attach/apply orchestration in another widget, and tracking stop must clean up the related scene/UI state. A simple one-shot call at tracking-start time is not robust enough because a successful OpenVR startup can happen before a given side has produced its first valid tracker pose, which would cause immediate attach-axis creation to fail even though the side becomes valid a moment later.

## Goals / Non-Goals

**Goals:**
- Start automatic left/right attach-axis orchestration only after tracking has successfully enabled.
- Retry each side independently until that side can be attached or tracking stops, so a temporarily unavailable side does not block the other side.
- Automatically enable the matching left/right apply-location behavior immediately after that side's attach-axis is created successfully.
- Stop automation cleanly when tracking stops, removing left/right attach-axis actors and restoring detached hand-follow state and button text.
- Reuse the existing attach/apply success conditions and UI synchronization paths instead of introducing a second implementation of the same operations.

**Non-Goals:**
- Changing attach-axis offset math, local rotation composition, or any existing manual button labels.
- Adding new UI controls or persistent configuration for this automation.
- Retrying forever after tracking has stopped or after a side has already completed its auto-attach/apply sequence.

## Decisions

### 1. Keep orchestration in the positioning widget and trigger it from the existing tracking-state callback

The main window already receives `tracking_state_changed_callback` events from `ViveTrackerWidget`. It should forward that lifecycle event to `ViveTrackerCaliApplyWidget`, which will expose a small public method such as `handle_tracking_state_changed(enabled: bool)`.

This keeps cross-widget orchestration at the composition layer while leaving attach/apply behavior inside the widget that already owns the buttons, sync helpers, and attach/apply logic.

Alternative considered: implement the whole automation inside `ViveTrackerWidget`. Rejected because it would force the tracking widget to know about positioning-tab UI semantics and duplicate button-state synchronization concerns that already belong to `ViveTrackerCaliApplyWidget`.

### 2. Add per-side auto-attach/apply retry state in `ViveTrackerCaliApplyWidget`

`ViveTrackerCaliApplyWidget` should track pending automation separately for left and right, plus a lightweight Qt timer used only while there is unfinished work. On tracking start, both sides become pending. Each timer tick attempts the next missing step for each side:

- if the side has no attach-axis yet, try to create it
- if attach-axis creation succeeds, sync the button text and immediately try the side's apply-location action
- if apply-location succeeds, mark that side complete and stop retrying it

This design handles the startup race where tracking is enabled before the first valid pose arrives. It also makes the sequence explicit: attach first, then apply.

Alternative considered: call the manual handlers once immediately after start. Rejected because attach-axis creation depends on valid tracker pose availability and would fail spuriously when data has not arrived yet.

### 3. Reuse existing manual operations through helper methods that return success

The current private click handlers log messages and update button text, but they do not expose a clean success result to the caller. The implementation should extract side-specific helper methods for:

- attach-axis toggle/create-or-remove behavior
- apply-location enable/disable behavior
- stop-time cleanup behavior

The manual button handlers and the new automation flow should both call the same helpers so that validation, logging, rendering requests, and button-text synchronization remain identical.

Alternative considered: simulate button clicks from automation. Rejected because it makes sequencing harder to control and mixes user-intent events with internal orchestration.

### 4. Tracking stop clears pending automation and restores a detached session state

When tracking stops, the positioning widget should:

- stop the retry timer
- clear any pending left/right auto-attach state
- remove left/right attach-axis actors if present
- disable left/right hand root-follow flags so the hand skeletons are no longer treated as attached to removed attach-axis actors
- resync the left/right attach-axis button text

This ensures stop always leaves the session in a coherent detached state rather than retaining follow flags that reference attach-axis objects that no longer exist.

Alternative considered: remove only the attach-axis actors and leave follow flags unchanged. Rejected because it can leave the UI and render pipeline in a partially attached state that no longer matches live scene objects.

## Risks / Trade-offs

- Startup retry loop may produce repeated log lines while waiting for the first valid pose. → Keep retries lightweight, only log meaningful transitions, and stop per side as soon as it succeeds.
- Stop-time cleanup disables follow state even if the user would have preferred it to persist logically across sessions. → Favor a deterministic detached state because tracking stop already clears tracker state and removes scene objects.
- Cross-widget orchestration depends on the main window forwarding tracking-state changes to the positioning widget. → Keep the forwarding in one place, adjacent to the existing callback hookup in `motionGloveSDK_example3_3dView.py`, so the wiring remains easy to audit.

## Migration Plan

No data migration is required. The change only affects runtime orchestration of existing UI actions.

## Open Questions

- None for proposal time; the implementation can use a short Qt retry interval as long as it runs only while auto-start work remains pending.