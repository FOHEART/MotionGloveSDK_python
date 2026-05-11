## Context

`motionGloveSDK_example3_3dView.py` already renders hand skeleton actors in a PySide6-embedded VTK viewport and runs periodic SteamVR online checks. The requested change adds dynamic Lighthouse base-station visualization using `triad_openvr/lh_basestation_vive/lh_basestation_vive.obj`, with actor lifecycle and pose updates driven by the existing 1 Hz SteamVR timer path. The system must support one or multiple base stations and keep UI statistics consistent when tracking state toggles.

Constraints:
- Lighthouse actor count and transforms are available only when SteamVR tracking is enabled.
- 1 Hz refresh is sufficient for base-station detection and transform sync.
- Mesh decimation ratio must be configurable, defaulting to 50%.

## Goals / Non-Goals

**Goals:**
- Show 1..N Lighthouse base station models in VTK while tracking is enabled.
- Use one shared Lighthouse model source with configurable mesh decimation ratio.
- Update Lighthouse actor position and quaternion rotation from per-second detection output.
- Add/remove Lighthouse actors only in tracking-enabled state.
- Remove all Lighthouse actors when tracking is disabled.
- Recompute right-bottom polygon totals whenever Lighthouse actors are added or removed.

**Non-Goals:**
- High-frequency (>1 Hz) Lighthouse transform interpolation.
- New SteamVR data transport layers or protocol changes.
- Redesign of existing hand skeleton rendering architecture.
- Changes to non-VTK views.

## Decisions

1. Reuse existing SteamVR 1 Hz timer for Lighthouse sync.
- Decision: Execute Lighthouse detection and actor reconciliation in the same 1 Hz online-state timer callback.
- Rationale: Meets user-required frequency, minimizes new timers, and keeps SteamVR state transitions centralized.
- Alternative considered: A dedicated Lighthouse timer. Rejected because it duplicates state checks and increases lifecycle complexity.

2. Introduce a Lighthouse actor registry keyed by stable base-station identifier.
- Decision: Maintain an in-memory map `{lighthouse_id: actor_bundle}` where each bundle stores actor(s), model metadata, and last-seen timestamp.
- Rationale: Enables deterministic add/update/remove logic for one or many stations.
- Alternative considered: Recreate all actors on every tick. Rejected due to flicker, unnecessary allocations, and repeated polygon recount work.

3. Decimate Lighthouse mesh at load time with configurable ratio.
- Decision: Add a configuration variable (for example `LIGHTHOUSE_MESH_DECIMATION_RATIO = 0.5`) and apply decimation once per model load path.
- Rationale: Satisfies requirement for 50% default and future tunability, while avoiding repeated expensive mesh processing.
- Alternative considered: Ship pre-decimated mesh asset. Rejected because it adds static asset maintenance and reduces flexibility.

4. Apply quaternion-to-actor rotation update each timer tick.
- Decision: Convert runtime quaternion to VTK actor orientation and update actor transform together with world position.
- Rationale: Ensures actor orientation reflects Lighthouse pose exactly from detection source.
- Alternative considered: Position-only update. Rejected because orientation is an explicit requirement.

5. Recalculate polygon totals on Lighthouse actor topology changes.
- Decision: Trigger polygon-count refresh when actor set changes (add/remove) and on tracking disable cleanup.
- Rationale: Meets requirement that right-bottom model face count reflects current scene composition after tracking lifecycle operations.
- Alternative considered: Refresh every frame. Rejected as unnecessary overhead.

## Risks / Trade-offs

- [Risk] SteamVR detection can transiently miss a base station and cause remove/re-add churn at 1 Hz.
  - Mitigation: Optional short grace window (for example 1-2 ticks) before hard removal.
- [Risk] Quaternion convention mismatch (component order or handedness) could rotate actors incorrectly.
  - Mitigation: Normalize and explicitly document quaternion mapping before applying to VTK transform.
- [Trade-off] 1 Hz update is lower fidelity than real-time pose update.
  - Mitigation: Accepted by requirement; prioritize stability and low overhead.
- [Risk] Decimation may remove too much geometric detail for debugging.
  - Mitigation: Keep ratio configurable and default to 0.5.

## Migration Plan

- No data migration required.
- Implementation rollout:
  - Add model-loading and decimation configuration.
  - Add Lighthouse registry and 1 Hz reconciliation logic.
  - Add tracking-disable cleanup path for all Lighthouse actors.
  - Integrate polygon-count refresh on actor topology changes.
- Rollback strategy:
  - Disable new Lighthouse rendering path behind a feature flag or guard variable and retain existing hand-only rendering behavior.

## Open Questions

- What is the canonical Lighthouse identifier from runtime detection (serial, index, or role)?
- Which existing helper currently owns polygon-count accumulation and should receive Lighthouse deltas?
- Should temporary detector dropouts use immediate removal or grace-window removal in the first implementation?
