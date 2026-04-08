## ADDED Requirements

### Requirement: Axes actor handle returned by helper
`add_axes_to_renderer` in `python_draw3d/vtk_axes.py` SHALL return the `vtkAxesActor` it adds to the renderer, so callers can store a reference for later toggling.

#### Scenario: Return value is the added actor
- **WHEN** `add_axes_to_renderer(renderer)` is called
- **THEN** the returned object is the `vtkAxesActor` that was added to the renderer

### Requirement: VTK viewport right-click menu with axes toggle
Right-clicking in the VTK viewport SHALL display a `QMenu` containing an action that toggles the coordinate-axes actor's visibility. The action label SHALL read "隐藏坐标轴" when the axes are currently visible, and "显示坐标轴" when they are hidden.

#### Scenario: Axes hidden via context menu
- **WHEN** axes are visible and the user right-clicks the viewport and selects "隐藏坐标轴"
- **THEN** the axes actor becomes invisible and the viewport re-renders

#### Scenario: Axes shown via context menu
- **WHEN** axes are hidden and the user right-clicks the viewport and selects "显示坐标轴"
- **THEN** the axes actor becomes visible and the viewport re-renders

#### Scenario: Menu label reflects current axes state
- **WHEN** the context menu is opened
- **THEN** the axes toggle item label correctly reflects whether axes are currently visible or hidden
