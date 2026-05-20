## Context

The left-hand `vive_tracker_attachAxis` already has persistent UI controls for creating the actor and editing its local positional offset, and the runtime pose helper currently composes the actor pose as `tracker rotation + rotated offset`. There is no persisted UI for local rotational correction, and there is no state in the left attach-axis path for an additional local quaternion that can be previewed in real time.

This change crosses the `.ui` file, the Qt controller that resolves persisted controls safely, and the attach-axis pose composition owned by `ViveTrackerWidget` and `python_draw3d/vive_tracker_attachAxis.py`. The user also explicitly requires the transform order to be rotation-first-then-translation, which benefits from recording the intended composition before implementation.

## Goals / Non-Goals

**Goals:**
- Add persisted left-hand X/Y/Z local rotation sliders with `0-360` ranges below the existing left attach-axis offset controls.
- Show the live degree value for each left-hand rotation slider in a dedicated label beside that slider.
- Represent the three slider values as one local rotation quaternion and apply it to the left `vive_tracker_attachAxis` orientation by left-multiplying it onto the left tracker rotation.
- Keep the left attach-axis origin at the same tracker-defined offset position while applying the additional local rotation only to the attach-axis orientation.
- Re-render the left attach-axis immediately while the user drags any of the three sliders.

**Non-Goals:**
- Changing right-hand attach-axis behavior in this change.
- Replacing the existing left attach-axis offset line edit workflow.
- Redesigning the 20 mm attach-axis geometry or adding new visualization actors.

## Decisions

### Decision: Persist the new left rotation sliders and value labels in the `.ui` file
The three left-hand local rotation sliders and their degree labels will be added to `ui/vive_tracker_caliApply.ui` rather than created dynamically in Python.

Rationale:
- The repository already moved attach-axis controls from dynamic creation into persisted `.ui` widgets to avoid stale Qt object references.
- Keeping the slider controls in the `.ui` file preserves the same robust `findChild`/`isValid` pattern already used for left/right attach-axis widgets.

Alternatives considered:
- Build the sliders dynamically in `ui/vive_tracker_caliApply.py`: rejected because this reintroduces the same deleted-object lifecycle risk the previous attach-axis UI change removed.

### Decision: Store left-hand attach-axis local rotation as slider-degree state and derive a quaternion from a fixed XYZ order
`ViveTrackerWidget` will own a left attach-axis local rotation state expressed as three degree values. Runtime pose composition will derive a normalized quaternion from those degrees using a fixed X-then-Y-then-Z composition order consistent with the slider labels.

Rationale:
- The UI naturally edits degree values, while the render path and future attach-axis consumers need a quaternion.
- A fixed order makes the behavior deterministic and testable, and aligning the order with the visible X/Y/Z slider sequence is the least surprising behavior.

Alternatives considered:
- Store only the quaternion and infer slider values later: rejected because the UI needs stable round-trippable degree values.
- Leave Euler order unspecified: rejected because the same slider values could otherwise produce ambiguous orientations.

### Decision: Compose attach-axis world pose with tracker-defined position and locally corrected orientation
The left attach-axis helper path will compute the attach-axis origin from the tracker display position plus the existing tracker-rotated local offset, and it will compute the attach-axis orientation by left-multiplying the user-controlled local rotation quaternion onto the base left tracker display quaternion.

Rationale:
- This matches the clarified user requirement that the additional local rotation should rotate only the attach-axis itself, not move the attach point around the tracker-to-attach offset line.
- It preserves the original tracker-defined attach point location while still allowing the user to correct the attach-axis' local orientation.

Alternatives considered:
- Rotate the offset vector by the composed quaternion: rejected because that makes the attach point move when the user only wants to rotate the attach-axis itself.
- Right-multiply the local rotation onto the tracker quaternion: rejected because the requirement explicitly calls for left multiplication.

### Decision: Update the left attach-axis actor continuously on slider drag
The left slider `valueChanged` path will update the stored degree values, sync the adjacent labels, recompute the left attach-axis pose immediately, and request a render when the left attach-axis is present.

Rationale:
- The user explicitly wants to see the effect while dragging.
- Reusing the existing attach-axis pose update path keeps live preview behavior consistent with offset edits and tracker updates.

Alternatives considered:
- Update only on slider release or via a separate confirm button: rejected because it would not provide immediate visual feedback.

## Risks / Trade-offs

- [Euler slider composition can be confusing near wraparound boundaries] → Mitigation: keep slider display values explicit in degree labels and normalize the derived quaternion internally.
- [Live slider updates may produce many render requests while dragging] → Mitigation: reuse the existing lightweight attach-axis pose update path and only re-render the left attach-axis slice.
- [Future attach-axis consumers could accidentally ignore the new local rotation state] → Mitigation: centralize final left attach-axis pose composition in the existing helper/accessor path so all callers share the same composed pose.
- [Changing left attach-axis pose composition could unintentionally affect right-hand behavior] → Mitigation: keep all new state, UI controls, and composition changes scoped to the left-hand code path only.

## Migration Plan

No data migration is required. This is a runtime UI and pose-composition enhancement.

Implementation can proceed in three steps:
- add persisted left slider/label controls and controller bindings in the application-positioning tab
- add left attach-axis local rotation state plus quaternion composition helpers in the attach-axis runtime path
- validate live slider updates and confirm the attach-axis orientation changes without moving the attach-axis origin

Rollback is straightforward: remove the new left slider controls and revert the left attach-axis pose path to tracker rotation plus local offset only.

## Open Questions

- The current request is left-hand only; if the same local rotation tuning is needed on the right-hand attach-axis, that should be proposed separately or added explicitly in a follow-up change.