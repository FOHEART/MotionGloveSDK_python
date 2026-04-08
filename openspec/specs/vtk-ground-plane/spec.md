## ADDED Requirements

### Requirement: Ground plane grid actor
The system SHALL provide a `build_ground_plane_actor(extent, spacing)` function in `python_draw3d/ground_plane.py` that returns a `vtkActor` representing a flat grid in the X–Z plane (Y = 0). The grid SHALL use grey lines (`(0.4, 0.4, 0.4)`), a spacing of 5 cm (0.05 m), and a default extent of ±30 cm from the origin on both X and Z axes.

#### Scenario: Actor geometry is correct
- **WHEN** `build_ground_plane_actor()` is called with default parameters
- **THEN** the returned actor contains grid lines spaced 5 cm apart covering −30 cm to +30 cm on both X and Z axes at Y = 0

#### Scenario: Actor is grey
- **WHEN** the ground plane actor is rendered
- **THEN** all lines appear in a mid-grey color approximately `(0.4, 0.4, 0.4)` in RGB

### Requirement: Ground plane toggle via context menu
Right-clicking in the VTK viewport SHALL display a `QMenu` action that toggles the ground plane actor's visibility. The action label SHALL read "隐藏地平面" when the ground plane is visible, and "显示地平面" when it is hidden. The ground plane SHALL be hidden by default on application start.

#### Scenario: Ground plane shown via context menu
- **WHEN** the ground plane is hidden (initial state) and the user right-clicks and selects "显示地平面"
- **THEN** the ground plane grid becomes visible and the viewport re-renders

#### Scenario: Ground plane hidden via context menu
- **WHEN** the ground plane is visible and the user right-clicks and selects "隐藏地平面"
- **THEN** the ground plane grid becomes invisible and the viewport re-renders

#### Scenario: Menu label reflects current ground plane state
- **WHEN** the context menu is opened
- **THEN** the ground plane toggle item label correctly reflects whether the ground plane is currently visible or hidden

#### Scenario: Ground plane hidden on startup
- **WHEN** the application starts without user interaction
- **THEN** the ground plane grid is not visible in the viewport
