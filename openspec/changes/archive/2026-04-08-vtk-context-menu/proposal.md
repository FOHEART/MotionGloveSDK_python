## Why

The VTK viewport currently has no way to toggle visual helpers at runtime — the coordinate axes and ground plane are either always on or require code changes. A right-click context menu on the VTK widget gives users instant, discoverable control over scene overlays without adding permanent toolbar clutter.

## What Changes

- Right-clicking anywhere inside the VTK viewport opens a `QMenu` with two toggle actions
- **显示坐标轴 / 隐藏坐标轴** — shows or hides the world-origin axes actor (the existing `add_axes_to_renderer` output)
- **显示地平面 / 隐藏地平面** — draws or removes a grey grid ground plane; grid spacing 5 cm, extent covers a reasonable working volume
- Menu item text updates to reflect current state (e.g., if axes are visible the item reads "隐藏坐标轴", if hidden it reads "显示坐标轴")

## Capabilities

### New Capabilities

- `vtk-axes-toggle`: Runtime toggle for the coordinate-axes actor via context menu
- `vtk-ground-plane`: Ground-plane grid actor (grey, 5 cm spacing) with runtime toggle via context menu

### Modified Capabilities

<!-- None -->

## Impact

- `motionGloveSDK_example3_3dView.py` — intercept right-click on `QVTKRenderWindowInteractor`, show `QMenu`
- `python_draw3d/vtk_axes.py` — `add_axes_to_renderer` currently returns nothing; needs to return the actor so it can be toggled
- No new dependencies; no breaking API changes to the public SDK
