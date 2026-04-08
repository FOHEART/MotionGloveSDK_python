## 1. Setup & Dependencies

- [x] 1.1 Add `pyside6==6.5.3` to the runtime pip install line in `[Windows]setup_python_libs.cmd` (inside the `--target libs` block)
- [x] 1.2 Add `pyside6==6.5.3` to the runtime pip install line in `[Linux]setup_python_libs.sh` (inside the `--target libs` block)
- [x] 1.3 Verify `vtkmodules.qt.QVTKRenderWindowInteractor` is importable after `pyside6` and `vtk==9.6.0` are both installed in `libs/`

## 2. SDK — Expose Last Remote Address

- [x] 2.1 In `src/motionGloveSDK.py`, add a module-level variable `_last_remote_addr: tuple[str, int] | None = None` protected by the existing `_store_lock` (or a new lock)
- [x] 2.2 In `_recv_loop`, after each successful `recvfrom`, store `addr` into `_last_remote_addr`
- [x] 2.3 Add public function `MotionGloveSDK_GetLastRemoteAddr() -> tuple[str, int] | None` that returns `_last_remote_addr` thread-safely

## 3. Main Window — QMainWindow Scaffold

- [x] 3.1 In `motionGloveSDK_example3_3dView.py`, import `PySide6.QtWidgets`, `PySide6.QtCore`, and `vtkmodules.qt.QVTKRenderWindowInteractor.QVTKRenderWindowInteractor`
- [x] 3.2 Create a `MotionGloveMainWindow(QMainWindow)` class with `__init__` that builds the window layout (menu bar, central widget, left panel, status bar) without any VTK logic yet
- [x] 3.3 Add **File → Exit** menu action wired to `QApplication.quit()`
- [x] 3.4 Add **Help → About Qt** menu action wired to `QMessageBox.aboutQt(self)`
- [x] 3.5 Add `QStatusBar` with initial message `"Ready"`

## 4. VTK Embedding

- [x] 4.1 Instantiate `QVTKRenderWindowInteractor` as the right portion of the central horizontal layout
- [x] 4.2 Obtain `render_window` from `vtk_widget.GetRenderWindow()` and add the existing `vtkRenderer` to it
- [x] 4.3 Obtain `interactor` from `render_window.GetInteractor()`, set `vtkInteractorStyleTrackballCamera`, call `vtk_widget.Initialize()` (do NOT call `interactor.Start()`)
- [x] 4.4 Move all VTK scene construction (joint actors, link actors, axes, overlay text) into `MotionGloveMainWindow.__init__` after the render window is ready
- [x] 4.5 Re-attach `bind_space_reset_camera` and `setup_camera` using the embedded interactor and render window

## 5. Qt Timer & Update Loop

- [x] 5.1 Replace VTK `CreateRepeatingTimer` / `AddObserver("TimerEvent", ...)` with a `QTimer` at 16 ms
- [x] 5.2 Connect the `QTimer.timeout` signal to the existing `_on_timer` update callback (adapted to call `render_window.Render()` directly)
- [x] 5.3 Start the SDK poll thread and the `QTimer` in `MotionGloveMainWindow.showEvent` or at the end of `__init__`

## 6. Left-Side Network Info Panel

- [x] 6.1 Add a `QFrame` (fixed width 220 px) as the left widget in the central horizontal layout
- [x] 6.2 Add a `QLabel` for "Source IP:" and a `QLabel` value field; same for "Port:"
- [x] 6.3 In the `QTimer` callback, call `MotionGloveSDK_GetLastRemoteAddr()` and update the labels (show "Waiting..." if `None`)

## 7. CI Compatibility

- [x] 7.1 In `motionGloveSDK_example3_3dView.py`, when `_CI_MODE` is true and `not _CI_RENDER_ENABLED`, ensure the code exits before constructing `QApplication` (existing path unchanged)
- [x] 7.2 When `_CI_MODE` is true and `_CI_RENDER_ENABLED`, set `os.environ["QT_QPA_PLATFORM"] = "offscreen"` before constructing `QApplication`
- [x] 7.3 In the CI render path, after `app.exec()` is running (or before), render one frame and call `QApplication.quit()` after `_CI_RENDER_SECONDS`; ensure `MotionGloveSDK_CloseUDPPort()` is called on exit
- [x] 7.4 Update `.github/workflows/ci-3dview.yml` to set `QT_QPA_PLATFORM: offscreen` in the env block for Linux jobs

## 8. Cleanup & Verification

- [x] 8.1 Remove the `input("按 Enter 键退出程序\n")` thread — window close button and File→Exit replace it
- [x] 8.2 Connect `QMainWindow.closeEvent` to call `_quit.set()` and `MotionGloveSDK_CloseUDPPort()`
- [x] 8.3 Run `python motionGloveSDK_example3_3dView.py` locally and verify all UI elements are present
- [x] 8.4 Run the CI smoke test locally: `MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0 python motionGloveSDK_example3_3dView.py`
- [x] 8.5 Run Pyright (`pyright`) and fix any new type errors introduced
