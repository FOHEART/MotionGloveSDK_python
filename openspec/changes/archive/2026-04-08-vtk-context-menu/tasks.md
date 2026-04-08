## 1. Fix vtk_axes helper

- [x] 1.1 In `python_draw3d/vtk_axes.py`, change `add_axes_to_renderer` to `return axes` after `renderer.AddActor(axes)` (currently returns `None`)

## 2. Ground plane module

- [x] 2.1 Create `python_draw3d/ground_plane.py` with `build_ground_plane_actor(extent=0.30, spacing=0.05)` that builds a `vtkPolyData` grid of lines in the X–Z plane at Y=0
- [x] 2.2 Set grid color to `(0.4, 0.4, 0.4)` and line width to 1 px on the returned `vtkActor`

## 3. Store actor references in MotionGloveMainWindow

- [x] 3.1 In `_build_vtk_scene`, capture the return value of `add_axes_to_renderer(...)` as `self._axes_actor`
- [x] 3.2 Import and call `build_ground_plane_actor()`, add the actor to the renderer, store as `self._ground_actor`; set `self._ground_actor.SetVisibility(False)` (hidden by default)
- [x] 3.3 Add state flags `self._axes_visible = True` and `self._ground_visible = False` to `__init__`

## 4. Context menu via event filter

- [x] 4.1 In `MotionGloveMainWindow.__init__`, call `self._vtk_widget.installEventFilter(self)` after the widget is created
- [x] 4.2 Implement `eventFilter(self, obj, event)` on `MotionGloveMainWindow`: when `obj is self._vtk_widget` and `event.type() == QEvent.Type.ContextMenu`, call `self._show_context_menu(event.globalPos())` and return `True`; otherwise return `super().eventFilter(obj, event)`
- [x] 4.3 Implement `_show_context_menu(self, global_pos)`: create a `QMenu`, add axes toggle action with label based on `self._axes_visible`, add ground toggle action with label based on `self._ground_visible`, execute with `menu.exec(global_pos)`
- [x] 4.4 Wire axes action: flip `self._axes_visible`, call `self._axes_actor.SetVisibility(self._axes_visible)`, call `self._vtk_widget.GetRenderWindow().Render()`
- [x] 4.5 Wire ground action: flip `self._ground_visible`, call `self._ground_actor.SetVisibility(self._ground_visible)`, call `self._vtk_widget.GetRenderWindow().Render()`

## 5. Verification

- [x] 5.1 Run CI smoke test: `MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0 python motionGloveSDK_example3_3dView.py` — must pass
- [x] 5.2 Syntax-check `python_draw3d/ground_plane.py` and `motionGloveSDK_example3_3dView.py` via `ast.parse`
