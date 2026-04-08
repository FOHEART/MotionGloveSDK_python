## Context

`motionGloveSDK_example3_3dView.py` currently owns the entire program: it starts a `vtkRenderWindow`, runs a `vtkRenderWindowInteractor` event loop, and handles keyboard/timer events directly. There is no GUI framework wrapper — the window has no menu, status bar, or side panels.

VTK ships its own Qt embedding adapter (`vtkRenderWindowInteractor` via `QVTKRenderWindowInteractor` from `vtkmodules.qt.QVTKRenderWindowInteractor`) which connects VTK's render pipeline to a Qt widget while delegating event dispatch to Qt. PySide6 is the official Qt6 Python binding, and its `QMainWindow` provides the standard chrome (menu bar, status bar, dock widgets).

The existing SDK polling thread and timer callback are pure Python/threading — they are compatible with any event loop wrapper.

## Goals / Non-Goals

**Goals:**
- Wrap the VTK viewport in a `QMainWindow` so future UI features have a home
- Menu bar: **File → Exit**, **Help → About Qt** (built-in Qt dialog, no custom code)
- Left-side info panel: shows live UDP source IP and port
- Status bar at the bottom
- `pyside6` added to both setup scripts (installed into `libs/` alongside vtk)
- CI path must continue to work (offscreen render + headless Qt via `QT_QPA_PLATFORM=offscreen`)

**Non-Goals:**
- Redesigning or replacing the VTK scene (joints, links, axes, overlay text stay identical)
- Adding any controls to the left panel beyond IP/port display (deferred to future changes)
- Cross-platform packaging / pyinstaller integration (separate concern)

## Decisions

### D1 — Use `QVTKRenderWindowInteractor` for VTK embedding

PySide6 + VTK embedding is done via `vtkmodules.qt.QVTKRenderWindowInteractor.QVTKRenderWindowInteractor`. This is the upstream-supported path. The alternative (rendering offscreen and blitting to a `QLabel`) was rejected: it loses interactivity (mouse rotate/zoom/pan) and is significantly more complex.

**How it works:**
```
QMainWindow
├── QMenuBar
├── Central widget (QWidget, horizontal layout)
│   ├── Left panel (QWidget, ~220 px fixed width)
│   │   └── QLabel: IP / Port
│   └── QVTKRenderWindowInteractor  ← VTK lives here
└── QStatusBar
```

The `vtkRenderWindow` is obtained from the `QVTKRenderWindowInteractor` (`vtk_widget.GetRenderWindow()`). The existing renderer is added to it. The VTK interactor style and timer are attached to the widget's interactor (`vtk_widget.GetRenderWindow().GetInteractor()`).

### D2 — Qt event loop replaces VTK event loop

Current code calls `interactor.Start()` which blocks in VTK's own loop. With Qt embedding, `app.exec()` drives both Qt and VTK events. The `interactor.Initialize()` call is still needed; `interactor.Start()` is NOT called.

### D3 — Timer-driven updates via Qt `QTimer` instead of VTK timer

VTK's `CreateRepeatingTimer` API works differently under Qt embedding — Qt's own `QTimer` at ~16 ms calling `vtk_widget.GetRenderWindow().GetInteractor().InvokeEvent("TimerEvent")` is simpler and avoids cross-framework timer conflicts.

Alternatively, a `QTimer` calling the update callback directly (bypassing VTK timer event machinery) is even cleaner. **Decision: use `QTimer` → update callback → `render_window.Render()` directly.**

### D4 — Left panel shows remote IP/port from SDK

`motionGloveSDK._actor_store` stores frames but not the source address. The `_recv_loop` receives from `socket.recvfrom()` which returns `(data, addr)` where `addr = (ip, port)`. A small addition to `motionGloveSDK.py` exposes the last seen remote address. The left panel `QLabel` is refreshed by the same `QTimer` as the VTK update.

### D5 — CI path: `QT_QPA_PLATFORM=offscreen` for headless Qt

On Linux CI (no display), Qt requires `QT_QPA_PLATFORM=offscreen`. This is set in the CI workflow before running the script. The existing `MOTIONGLOVE_CI_RENDER=0` path (pipeline smoke test, no window) exits before `QApplication` is constructed, so it is unaffected.

### D6 — `pyside6` installed into `libs/` with a pinned version

Following the existing pattern, `pyside6` is added to the `--target libs` install in both setup scripts. A version compatible with Python 3.10 and the bundled Qt will be pinned (PySide6 6.5.x is the last series with broad Python 3.10 support on all platforms; 6.7+ dropped some Python 3.10 wheels). **Pin: `pyside6==6.5.3`.**

## Risks / Trade-offs

- **VTK + Qt version compatibility** → `vtkmodules.qt.QVTKRenderWindowInteractor` requires VTK to be built with Qt support. The `vtk==9.6.0` wheel on PyPI includes Qt6/PySide6 support. Mitigation: test import at startup and fail with a clear message if the adapter is unavailable.
- **PySide6 wheel size** (~80 MB compressed) significantly increases `libs/` size → acceptable for a desktop tool, noted in docs.
- **CI headless Qt** → `QT_QPA_PLATFORM=offscreen` must be set in the CI YAML. Missing it causes a hard crash. Mitigation: set it in the workflow and also as a fallback in the script when `_CI_MODE` is detected.
- **Space reset camera keyboard shortcut** → currently bound to VTK interactor via `bind_space_reset_camera`. Under Qt embedding the VTK widget still receives keyboard events, so this should continue to work unchanged.
- **`interactor.Start()` must NOT be called** under Qt embedding; calling it hangs the process. Mitigation: guard with `if not _QT_MODE` or simply remove it in the refactored code path.

## Migration Plan

1. Add `pyside6==6.5.3` to setup scripts (backward-compatible; users who already have `libs/` must re-run setup)
2. Expose `MotionGloveSDK_GetLastRemoteAddr()` in `motionGloveSDK.py`
3. Refactor `motionGloveSDK_example3_3dView.py`:
   - Build `QApplication` + `QMainWindow` + `QVTKRenderWindowInteractor`
   - Move VTK pipeline setup into a helper (no functional change)
   - Replace `interactor.Start()` with `app.exec()`
   - Replace VTK timer with `QTimer`
4. Update CI workflow to add `QT_QPA_PLATFORM=offscreen` on Linux

Rollback: the change is isolated to the example script and setup scripts. Reverting is a one-file git checkout.

## Open Questions

- Should the left panel use a `QDockWidget` (user-resizable/floatable) or a fixed-width `QFrame`? A fixed `QFrame` is simpler for now; docking can be added later.
- Does `pyside6==6.5.3` have Python 3.10 wheels for all three CI platforms (Windows, Ubuntu 22.04, Ubuntu 24.04)? **Verify before implementing.**
