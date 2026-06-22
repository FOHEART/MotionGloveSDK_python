# MotionGloveSDK Python — Agent Guidelines

> **First read [`CLAUDE.md`](./CLAUDE.md)** for complete architecture, data flow, threading model, and environment setup.

## Quick orientation

- **Language:** Python 3.10+
- **Deps install:** `bash scripts/[Linux]setup_python_libs.sh` (libs go to `libs/`, not system Python)
- **Main entry points:** `motionGloveSDK_example1.py` / `_example2.py` / `_example3_3dView.py`
- **SDK API:** `src/motionGloveSDK.py` (public functions use `C++-style PascalCase`)
- **Type check:** `pyright` (config in `pyrightconfig.json`)
- **CI:** `.github/workflows/ci-3dview.yml` — smoke test with `MOTIONGLOVE_CI=1 MOTIONGLOVE_CI_RENDER=0`

## Subproject: LinkerHand

`linkerhand-python-sdk/` is a separately-maintained SDK for controlling dexterous robotic hands (O6/L6/L7/L10/L20/G20/L21/L25) via CAN/RS485. It has its own [`AGENTS.md`](./linkerhand-python-sdk/AGENTS.md).

**Cross-subproject rules:**
- Do not modify `linkerhand-python-sdk/` files unless explicitly asked — they are synced from the upstream LinkerHand repo
- LinkerHand CAN setup requires `sudo` on Linux; see [`CAN_SETUP_GUIDE.md`](./linkerhand-python-sdk/CAN_SETUP_GUIDE.md)

## OpenSpec workflow

This project uses OpenSpec for spec-driven development. When asked to implement features:

1. **Propose** — use the `openspec-propose` skill to create design docs, specs, and tasks
2. **Apply** — use `openspec-apply-change` to work through implementation tasks
3. **Archive** — use `openspec-archive-change` after completion

See `.github/skills/openspec-*/SKILL.md` for detailed instructions.

## Skeleton system (42 bones)

- `BoneIndex` enum in `src/definitions.py` defines all 42 bones
- Bones 0–20: Right hand (0=RightHand root, then thumb/index/middle/ring/pinky chains)
- Bones 21–41: Left hand (21=LeftHand root, same chain structure)
- `*3End` bones (indices 4,8,12,16,20, 25,29,33,37,41): fingertip end-nodes, position-only (no local axes in 3D view)
- Legacy 32-bone streams: SDK auto-appends 10 virtual end nodes (`_VIRTUAL_TIP_LENGTH_M = 0.02`)

## Key patterns

- **Thread safety:** `_actor_store` is locked with `threading.RLock()`. Frames returned to users are NOT deep-copied — don't mutate them.
- **UI files:** `.ui` files in `ui/` are Qt Designer files loaded at runtime via `QUiLoader`. No compilation step.
- **Config:** `config.json` stores visual prefs and local paths. `python_draw3d/draw_config_io.py` handles JSON save/load for `DrawConfig`.
- **Euler/quaternion:** Always use `src/xsqeconverter.py` (ported from Movella C++). The old `euler_to_quat.py` is deleted.
- **CI mode:** Environment vars `MOTIONGLOVE_CI`, `MOTIONGLOVE_CI_RENDER`, `MOTIONGLOVE_CI_SECONDS` control headless test behavior.
- **CSV playback:** Use `CsvFrameReader` (from `src/csv_frame_reader.py`) — preloads all frames, supports `next_frame()`/`seek()`.
