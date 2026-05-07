"""Linker hand panel loaded from linker_hand_widget.ui."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Qt


def _ui_path() -> Path:
    """Return linker_hand_widget.ui path for source and packaged runs."""
    candidates: list[Path] = []

    candidates.append(Path(__file__).parent / "linker_hand_widget.ui")
    candidates.append(Path(__file__).parent.parent / "ui" / "linker_hand_widget.ui")

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "ui" / "linker_hand_widget.ui")
        candidates.append(Path(meipass) / "_internal" / "ui" / "linker_hand_widget.ui")

    try:
        exe_dir = Path(sys.executable).parent
        candidates.append(exe_dir / "ui" / "linker_hand_widget.ui")
        candidates.append(exe_dir / "_internal" / "ui" / "linker_hand_widget.ui")
    except Exception:
        exe_dir = None

    candidates.append(Path.cwd() / "ui" / "linker_hand_widget.ui")
    candidates.append(Path.cwd() / "_internal" / "ui" / "linker_hand_widget.ui")

    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue

    search_roots = [Path(__file__).parent, Path(__file__).parent.parent]
    if exe_dir is not None:
        search_roots.append(exe_dir)
    search_roots.append(Path.cwd())
    for root in search_roots:
        try:
            for p in root.rglob("linker_hand_widget.ui"):
                return p
        except Exception:
            continue

    return Path(__file__).parent / "linker_hand_widget.ui"


class LinkerHandWidget(QWidget):
    """Display left hand finger linker angles (Y-axis rotation sum)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.finger_labels = {}  # finger_name -> QLabel
        self._latest_frame = None
        self._load_ui()
        self._bind_labels()
        self._start_refresh_timer()

    def _start_refresh_timer(self):
        # Keep this panel refresh rate at 30Hz regardless of upstream push rate.
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_from_latest_frame)
        self._refresh_timer.start(33)

    def _load_ui(self):
        loader = QUiLoader()
        ui_file = QFile(str(_ui_path()))
        if not ui_file.open(QIODevice.OpenModeFlag.ReadOnly):
            raise RuntimeError(f"无法打开 UI 文件：{_ui_path()}")
        self._ui = loader.load(ui_file)
        ui_file.close()
        if self._ui is None:
            raise RuntimeError(f"QUiLoader 加载失败：{_ui_path()}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._ui)

        # Apply an object-name stylesheet at the panel root so parent styles do not
        # wipe out the value label foreground color when embedded in the main window.
        self._ui.setStyleSheet(
            "QLabel#lbl_value_thumb, "
            "QLabel#lbl_value_index, "
            "QLabel#lbl_value_middle, "
            "QLabel#lbl_value_ring, "
            "QLabel#lbl_value_pinky {"
            "color: #ffffff;"
            "background: transparent;"
            "font-weight: bold;"
            "font-size: 12px;"
            "}"
        )

    def _bind_labels(self):
        # Key = panel row label; value = (ui object name, corresponding 3-bone list)
        row_specs = [
            ("左手拇指根部", "lbl_value_thumb", ["LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3"]),
            ("左手食指根部", "lbl_value_index", ["LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3"]),
            ("左手中指根部", "lbl_value_middle", ["LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3"]),
            ("左手无名指根部", "lbl_value_ring", ["LeftHandRing1", "LeftHandRing2", "LeftHandRing3"]),
            ("左手小指根部", "lbl_value_pinky", ["LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3"]),
        ]

        for finger_key, obj_name, bones in row_specs:
            label = self._ui.findChild(QLabel, obj_name)
            if label is None:
                raise RuntimeError(f"UI 控件未找到：{obj_name}")
            label.setMinimumWidth(72)
            label.setMaximumWidth(96)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
            self.finger_labels[finger_key] = {
                "label": label,
                "bones": bones,
            }
    
    def update_linker_angles(self, frame):
        """Accept newest frame from host view; actual UI paint runs at 30Hz timer."""
        self._latest_frame = frame

    def _extract_y_deg(self, skel, channel_order: int):
        """Read Y-angle from Euler if present, otherwise derive from quaternion."""
        if bool(getattr(skel, "contains_euler_degree", 0)):
            return float(skel.euler_degree[1])

        if bool(getattr(skel, "contains_quat_wxyz", 0)):
            try:
                from src.xsqeconverter import quat_to_euler_degree
                e = quat_to_euler_degree(list(skel.quat_wxyz), int(channel_order))
                return float(e[1])
            except Exception:
                return None

        return None

    def _refresh_from_latest_frame(self):
        """Update Y-axis rotation sum display for all fingers at fixed 30Hz."""
        frame = self._latest_frame
        if frame is None:
            return
        
        from src.definitions import BoneIndex
        
        # Build lookup maps for robust matching in both 32/42 skeleton streams.
        # Some streams can be indexed differently, so keep a name-based fallback.
        from src.definitions import BONE_NAMES

        # Build a lookup map: bone_index -> skeleton
        skeleton_by_index = {}
        skeleton_by_name = {}
        for skel in frame.skeletons:
            if skel.bone_index not in skeleton_by_index:
                skeleton_by_index[skel.bone_index] = skel
            if getattr(skel, "bone_name", "") and skel.bone_name not in skeleton_by_name:
                skeleton_by_name[skel.bone_name] = skel
            idx = int(skel.bone_index)
            if 0 <= idx < len(BONE_NAMES) and BONE_NAMES[idx] not in skeleton_by_name:
                skeleton_by_name[BONE_NAMES[idx]] = skel

        try:
            channel_order = int(frame.header.channel_order)
        except Exception:
            channel_order = 4  # ZXY default
        
        # Update labels for each finger
        for finger_key, info in self.finger_labels.items():
            label = info["label"]
            bone_names = info["bones"]
            
            total_y_abs = 0.0
            valid_count = 0
            
            # Sum absolute Y-axis rotation angles for the three bones
            for bone_name in bone_names:
                try:
                    bone_idx = BoneIndex[bone_name]
                    skel = skeleton_by_index.get(bone_idx)
                    if skel is None:
                        skel = skeleton_by_name.get(bone_name)
                    if skel is not None:
                        y_deg = self._extract_y_deg(skel, channel_order)
                        if y_deg is not None:
                            total_y_abs += abs(y_deg)
                            valid_count += 1
                except (KeyError, ValueError):
                    pass
            
            # Always show a numeric value so the UI does not stay blank.
            angle_text = f"{total_y_abs:.1f}°"
            
            label.setText(angle_text)
