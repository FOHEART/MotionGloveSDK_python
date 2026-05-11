## 1. Lighthouse Model Pipeline

- [x] 1.1 Add Lighthouse model path constant for `triad_openvr/lh_basestation_vive/lh_basestation_vive.obj` in the 3D view pipeline.
- [x] 1.2 Add configurable Lighthouse mesh decimation ratio variable with default `0.5`.
- [x] 1.3 Implement Lighthouse mesh loader/mapper creation with decimation applied once and reused by actor creation.

## 2. Runtime Detection And Actor Registry

- [x] 2.1 Add Lighthouse actor registry keyed by Lighthouse identifier (for example serial/index).
- [x] 2.2 Integrate Lighthouse detection into the existing SteamVR online-state timer callback at 1 Hz.
- [x] 2.3 Implement reconciliation logic to add missing Lighthouse actors and remove stale actors while tracking is enabled.
- [x] 2.4 Update Lighthouse actor transforms from detection output each timer tick, including world position and quaternion rotation.

## 3. Tracking Lifecycle Rules

- [x] 3.1 Gate Lighthouse actor add/remove behavior so it runs only when tracking is enabled.
- [x] 3.2 On tracking disable, remove all Lighthouse actors from VTK and clear Lighthouse registry state.

## 4. Polygon Statistics Integration

- [x] 4.1 Identify and hook into the right-bottom VTK polygon-count update path used by existing model actors.
- [x] 4.2 Trigger polygon-count recomputation when Lighthouse actors are added while tracking is enabled.
- [x] 4.3 Trigger polygon-count recomputation when Lighthouse actors are removed while tracking is enabled.
- [x] 4.4 Trigger polygon-count recomputation after full Lighthouse cleanup on tracking disable.

## 5. Validation

- [ ] 5.1 Validate one-Lighthouse case: actor appears, pose updates at 1 Hz, and polygon totals include Lighthouse model.
- [ ] 5.2 Validate multi-Lighthouse case: actor count matches detection set and per-actor transforms update correctly.
- [ ] 5.3 Validate tracking-off behavior: all Lighthouse actors are removed and polygon totals are updated.
