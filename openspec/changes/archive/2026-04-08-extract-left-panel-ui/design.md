## Context

The left info panel is currently constructed inline in `_build_central()` inside `_build_qt_app()` in `motionGloveSDK_example3_3dView.py`. It consists of a `QFrame` (fixed 220 px wide) with a `QVBoxLayout` containing a bold title label, two row layouts each with a static label + dynamic value label (IP, port), and a stretch spacer. These dynamic labels (`_lbl_ip`, `_lbl_port`) are stored as attributes on `MotionGloveMainWindow` and updated every timer tick.

The goal is to move this structure to `ui/left_panel.ui` (editable in Qt Designer) and load it at runtime via a `LeftPanelWidget` controller class in `ui/left_panel_widget.py`.

## Goals / Non-Goals

**Goals:**
- `ui/left_panel.ui` — complete, valid Qt Designer XML file that represents the panel exactly as currently built (fixed width, title, IP row, port row, stretch)
- `ui/left_panel_widget.py` — loads the `.ui` file via `QUiLoader`, wraps it in a `QWidget` subclass, exposes `lbl_ip` and `lbl_port` properties for the timer to call `setText()` on
- `motionGloveSDK_example3_3dView.py` — `_build_central()` replaces the inline panel construction with `LeftPanelWidget()` instantiation; `_on_timer` uses `self._left_panel.lbl_ip` / `self._left_panel.lbl_port`
- The panel must remain visually and functionally identical after the change

**Non-Goals:**
- Extracting the main window itself to a `.ui` file (the VTK widget cannot be placed in Qt Designer)
- Changing the panel's current layout or content
- Using `pyside6-uic` to pre-compile the `.ui` file to Python (runtime loading via `QUiLoader` keeps `.ui` editable without a build step)

## Decisions

### D1 — Runtime `QUiLoader` over compile-time `pyside6-uic`

`pyside6-uic left_panel.ui -o left_panel_ui.py` would produce a generated `Ui_LeftPanel` class. This works but creates a derived artifact that must be regenerated after every Qt Designer save. `QUiLoader` loads the `.ui` at runtime — the `.ui` is the single source of truth and changes in Qt Designer are immediately live on next run. **Decision: use `QUiLoader`.**

### D2 — `ui/` folder at project root, controller alongside `.ui` file

All Qt Designer files and their Python controllers live together in `ui/`. This makes them easy to find and keeps the `python_draw3d/` folder for VTK-specific helpers only. The `ui/` folder gets `sys.path` insertion in the same pattern as `python_draw3d/` and `libs/`.

### D3 — `LeftPanelWidget` wraps the loaded widget, does not subclass it

`QUiLoader.load()` returns a `QWidget` instance. The controller class owns this widget and either re-exposes it or (preferred) inherits from `QWidget` and re-parents the loaded widget into itself. This keeps the type stable (`LeftPanelWidget` is always a `QWidget`) even if the `.ui` top-level type changes.

**Simpler alternative:** load the widget and use it directly without a wrapper class. This is fine but gives no typed attribute access. The wrapper gives `panel.lbl_ip` / `panel.lbl_port` as explicit properties.

### D4 — Object names in `.ui` file match controller property names

Qt Designer object names for the dynamic labels shall be `lbl_ip` and `lbl_port` so `QUiLoader`'s automatic attribute resolution (`widget.findChild(QLabel, "lbl_ip")`) maps cleanly to the controller's properties.

## Risks / Trade-offs

- **`QUiLoader` path resolution** → The `.ui` file path must be resolved relative to `left_panel_widget.py`, not the current working directory. Use `Path(__file__).parent / "left_panel.ui"`. → Mitigation: use `__file__`-relative path.
- **`QUiLoader` not available in all environments** → `QUiLoader` is in `PySide6.QtUiTools` which is always part of the `pyside6` wheel. No separate install needed.
- **Fixed width in `.ui` vs code** → `QFrame.minimumWidth` / `maximumWidth` or a `QSizePolicy` fixed constraint in the `.ui` must match the current 220 px. Qt Designer sets this via the `geometry` or `minimumSize`/`maximumSize` properties.

## Migration Plan

1. Create `ui/` directory
2. Write `ui/left_panel.ui` (valid Qt XML matching current panel)
3. Write `ui/left_panel_widget.py`
4. Update `motionGloveSDK_example3_3dView.py` to import and use `LeftPanelWidget`
5. Verify CI smoke test still passes
