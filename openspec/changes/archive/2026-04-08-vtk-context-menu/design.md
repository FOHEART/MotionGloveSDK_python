## Context

The VTK viewport is now embedded in a `QVTKRenderWindowInteractor` widget inside `MotionGloveMainWindow`. The existing scene has a coordinate-axes actor (created by `add_axes_to_renderer` in `python_draw3d/vtk_axes.py`) and no ground plane. Right-click events on the VTK widget currently pass through to VTK's interactor style (which does nothing useful on right-click for `vtkInteractorStyleTrackballCamera`).

`add_axes_to_renderer` calls `renderer.AddActor(...)` but returns `None`, so the caller has no handle to toggle it later.

## Goals / Non-Goals

**Goals:**
- Right-clicking inside the VTK widget shows a `QMenu` with two toggle entries
- Toggle 1: axes actor visibility (uses the existing `vtkAxesActor`)
- Toggle 2: ground-plane grid actor (new `vtkPolyData`-based grey grid, 5 cm spacing)
- Menu label text reflects current state ("显示…" vs "隐藏…")

**Non-Goals:**
- Persisting toggle state across sessions
- Adding more context menu items (deferred)
- Changing the interactor style or mouse button bindings

## Decisions

### D1 — Intercept right-click via Qt, not VTK observer

`QVTKRenderWindowInteractor` is a `QWidget`, so we can override `contextMenuEvent(self, event)` on the main window's central widget, or install an event filter on `_vtk_widget`. The cleanest approach: subclass `QVTKRenderWindowInteractor` inline or install a `QObject` event filter that catches `QEvent.Type.ContextMenu` and shows the `QMenu`. This keeps VTK's interactor style untouched — right-drag (zoom) still works because `ContextMenu` fires on release, not press.

**Decision: install an event filter on `_vtk_widget` inside `MotionGloveMainWindow`.**

```
_vtk_widget.installEventFilter(self)   # self = MotionGloveMainWindow
MotionGloveMainWindow.eventFilter() → catches ContextMenu → shows QMenu
```

### D2 — `add_axes_to_renderer` returns the actor

Change the return type from `None` to `vtkAxesActor`. The caller (`MotionGloveMainWindow._build_vtk_scene`) stores it as `self._axes_actor`. No callers outside the example file need updating.

### D3 — Ground plane: `vtkPolyData` grid lines via `vtkCellArray`

A grid of lines is the lightest VTK primitive. Build a `vtkPolyData` with:
- Vertices at grid intersections for the X–Z plane (Y = 0, i.e., the horizontal plane in VTK's default orientation)
- Lines connecting them in two directions (parallel to X and parallel to Z)
- Grid extent: ±30 cm (covers both hands comfortably), spacing 5 cm → 13 lines each direction = 169 points
- Color: mid-grey `(0.4, 0.4, 0.4)`, line width 1 px

Encapsulate in a helper function `build_ground_plane_actor(extent=0.30, spacing=0.05)` in a new file `python_draw3d/ground_plane.py`. Returns a `vtkActor`. Hidden by default; shown when the user enables it.

### D4 — Toggle state stored on the window

`MotionGloveMainWindow` keeps:
```python
self._axes_visible: bool = True      # axes start visible
self._ground_visible: bool = False   # ground starts hidden
```

The context menu actions read these flags to set their labels and flip them on trigger.

## Risks / Trade-offs

- **ContextMenu vs right-drag conflict** → Qt's `ContextMenu` event fires on right-button *release* after a short press. VTK's right-button zoom fires on press+drag. In practice they don't conflict: a drag suppresses the context menu naturally. No mitigation needed.
- **Ground plane Y=0 assumption** → the skeleton data uses Y-up with the floor near Y=0. If a stream uses a different convention, the plane appears at the wrong height. Acceptable for now; plane position is not configurable in this change.
- **`vtkAxesActor` visibility** → `actor.SetVisibility(0/1)` is the standard VTK API; works correctly.

## Migration Plan

1. Change `add_axes_to_renderer` to return the actor (one-line change, backward-compatible if callers ignore the return value)
2. Add `python_draw3d/ground_plane.py`
3. Update `MotionGloveMainWindow` in `motionGloveSDK_example3_3dView.py`

No schema changes, no dependency additions, no CI impact.
