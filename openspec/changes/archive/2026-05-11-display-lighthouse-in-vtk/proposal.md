## Why

The 3D VTK view currently shows hand-related actors but does not visualize detected Lighthouse base stations, so operators cannot verify tracker topology at a glance. Adding Lighthouse visualization now improves observability during SteamVR tracking sessions and helps quickly diagnose setup issues.

## What Changes

- Add Lighthouse base station actors to the VTK 3D scene, sourced from runtime SteamVR Lighthouse detection.
- Load model `triad_openvr/lh_basestation_vive/lh_basestation_vive.obj` and support configurable mesh decimation ratio (default 50%).
- Run Lighthouse presence/pose sync in the existing SteamVR online-state 1 Hz timer path.
- Update each Lighthouse actor transform from per-second detection output, including position and quaternion rotation.
- Adjust Lighthouse actor count only when tracking is enabled; remove all Lighthouse actors when tracking is disabled.
- Recompute and refresh the right-bottom VTK polygon-count overlay when Lighthouse actors are added or removed after tracking state changes.

## Capabilities

### New Capabilities
- `vtk-lighthouse-visualization`: Visualize one or more detected Lighthouse base stations in the VTK scene and keep actors synchronized with 1 Hz SteamVR detection updates.
- `vtk-lighthouse-polygon-stats`: Include Lighthouse actor add/remove events in the right-bottom VTK polygon-count totals during tracking lifecycle transitions.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `motionGloveSDK_example3_3dView.py` (SteamVR timer loop, tracking lifecycle, actor management)
  - `python_draw3d/` helper modules used for model loading, actor registration, and polygon stats
  - `triad_openvr/` integration path used to query Lighthouse IDs and poses
- No public API changes expected.
- Runtime impact is low: update frequency remains 1 Hz for Lighthouse synchronization.
