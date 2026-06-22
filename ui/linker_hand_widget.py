"""Linker hand panel loaded from linker_hand_widget.ui."""

import os
import sys
import threading
from pathlib import Path

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QIODevice, QTimer, Slot

# LinkerHand SDK root (sibling folder to this project)
_LINKERHAND_SDK_ROOT = str(Path(__file__).parent.parent / "linkerhand-python-sdk")


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
    """Display right hand finger linker angles (Y-axis rotation sum) for O6."""
    
    # Data send rate to LinkerHand (Hz)
    SEND_HZ: float = 30.0

    # Thumb bend: max angle (degrees) for motor value mapping
    THUMB_BEND_MAX_DEG: float = 90.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.finger_labels = {}  # finger_name -> QLabel
        self._latest_frame = None
        # LinkerHand connection state
        self._linker_api = None
        self._send_timer = None
        self._connect_lock = threading.Lock()
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

    def _bind_labels(self):
        row_specs = [
            ("右手拇指弯曲", "lbl_text_thumb",  ["RightHandThumb2",  "RightHandThumb3"], "y"),
            ("右手拇指侧摆", "lbl_text_thumb_adduction", ["RightHandThumb1"], "y"),
            ("右手食指弯曲", "lbl_text_index",  ["RightHandIndex1",  "RightHandIndex2",  "RightHandIndex3"], "y"),
            ("右手中指弯曲", "lbl_text_middle", ["RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3"], "y"),
            ("右手无名指弯曲", "lbl_text_ring",  ["RightHandRing1",   "RightHandRing2",   "RightHandRing3"], "y"),
            ("右手小指弯曲", "lbl_text_pinky",  ["RightHandPinky1",  "RightHandPinky2",  "RightHandPinky3"], "y"),
        ]

        for finger_key, obj_name, bones, axis in row_specs:
            label = self._ui.findChild(QLabel, obj_name)
            if label is None:
                raise RuntimeError(f"UI 控件未找到：{obj_name}")
            self.finger_labels[finger_key] = {
                "label":      label,
                "base_text":  finger_key,
                "bones":      bones,
                "axis":       axis,
            }
        
        # Bind motor angle label
        self.lbl_motor_thumb = self._ui.findChild(QLabel, "lbl_motor_thumb")
        if self.lbl_motor_thumb is None:
            raise RuntimeError(f"UI 控件未找到：lbl_motor_thumb")
        self.lbl_motor_thumb_adduction = self._ui.findChild(QLabel, "lbl_motor_thumb_adduction")
        if self.lbl_motor_thumb_adduction is None:
            raise RuntimeError(f"UI 控件未找到：lbl_motor_thumb_adduction")
        
        self.lbl_motor_index = self._ui.findChild(QLabel, "lbl_motor_index")
        if self.lbl_motor_index is None:
            raise RuntimeError(f"UI 控件未找到：lbl_motor_index")
        self.lbl_motor_middle = self._ui.findChild(QLabel, "lbl_motor_middle")
        if self.lbl_motor_middle is None:
            raise RuntimeError(f"UI 控件未找到：lbl_motor_middle")
        self.lbl_motor_ring = self._ui.findChild(QLabel, "lbl_motor_ring")
        if self.lbl_motor_ring is None:
            raise RuntimeError(f"UI 控件未找到：lbl_motor_ring")
        self.lbl_motor_pinky = self._ui.findChild(QLabel, "lbl_motor_pinky")
        if self.lbl_motor_pinky is None:
            raise RuntimeError(f"UI 控件未找到：lbl_motor_pinky")

        # Bind buttons
        self.btn_connect = self._ui.findChild(QPushButton, "btn_connect")
        self.btn_disconnect = self._ui.findChild(QPushButton, "btn_disconnect")
        if self.btn_connect is None or self.btn_disconnect is None:
            raise RuntimeError("UI 控件未找到：btn_connect / btn_disconnect")
        self.btn_connect.clicked.connect(self._on_connect)
        self.btn_disconnect.clicked.connect(self._on_disconnect)

    # ------------------------------------------------------------------
    # LinkerHand connection / disconnection
    # ------------------------------------------------------------------

    def _on_connect(self):
        """Initialize CAN bus and LinkerHand API in a background thread."""
        self.btn_connect.setEnabled(False)
        self.btn_disconnect.setEnabled(False)
        self.btn_connect.setText("连接中…")

        def _connect_worker():
            log_lines = []
            success = False
            try:
                if _LINKERHAND_SDK_ROOT not in sys.path:
                    sys.path.insert(0, _LINKERHAND_SDK_ROOT)

                from LinkerHand.utils.setup_can_interface import initialize_can_interface
                log_lines.append("正在初始化 CAN 接口 can0 …")
                ok = initialize_can_interface(can_interface="can0", bitrate=1000000)
                log_lines.append(f"CAN 初始化结果: {'成功' if ok else '失败（继续尝试）'}")

                from LinkerHand.linker_hand_api import LinkerHandApi
                log_lines.append("正在连接灵巧手 (right O6) …")
                with self._connect_lock:
                    self._linker_api = LinkerHandApi(
                        hand_type="right",
                        hand_joint="O6",
                        can="can0",
                        modbus="None",
                    )
                log_lines.append("✓ 灵巧手连接成功")
                success = True

            except Exception as exc:
                log_lines.append(f"✗ 连接失败: {exc}")

            # Print results to stdout (visible in terminal)
            for line in log_lines:
                print(f"[LinkerHand] {line}")

            # Update UI back on main thread via stored flag + QTimer single-shot
            self._connect_success = success
            from PySide6.QtCore import QMetaObject, Qt
            QMetaObject.invokeMethod(self, "_on_connect_done", Qt.ConnectionType.QueuedConnection)

        threading.Thread(target=_connect_worker, daemon=True).start()

    @Slot()
    def _on_connect_done(self):
        """Called on main thread after connect worker finishes."""
        success = getattr(self, "_connect_success", False)
        if success:
            self.btn_connect.setText("已连接")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self._start_send_timer()
        else:
            self.btn_connect.setText("连接灵巧手")
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)

    def _on_disconnect(self):
        """Stop send timer and close CAN connection."""
        self._stop_send_timer()
        with self._connect_lock:
            if self._linker_api is not None:
                try:
                    self._linker_api.close_can()
                except Exception as exc:
                    print(f"[LinkerHand] 断开时发生错误: {exc}")
                finally:
                    self._linker_api = None
        print("[LinkerHand] 灵巧手已断开")
        self.btn_connect.setText("连接灵巧手")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    # ------------------------------------------------------------------
    # Periodic data send to LinkerHand
    # ------------------------------------------------------------------

    def _start_send_timer(self):
        interval_ms = int(1000.0 / self.SEND_HZ)
        self._send_timer = QTimer(self)
        self._send_timer.timeout.connect(self._send_to_linker_hand)
        self._send_timer.start(interval_ms)

    def _stop_send_timer(self):
        if self._send_timer is not None:
            self._send_timer.stop()
            self._send_timer.deleteLater()
            self._send_timer = None

    def _send_to_linker_hand(self):
        """Build 6-element pose and call finger_move at SEND_HZ."""
        with self._connect_lock:
            api = self._linker_api
        if api is None:
            return

        # Extract all motor values from labels
        motor_values = [255] * 6  # default all 255

        # Index 0: thumb motor value
        try:
            text = self.lbl_motor_thumb.text()
            if "：" in text:
                motor_values[0] = int(round(float(text.split("：")[1])))
        except (ValueError, IndexError):
            pass

        # Index 1: thumb adduction motor value
        try:
            text = self.lbl_motor_thumb_adduction.text()
            if "：" in text:
                motor_values[1] = int(round(float(text.split("：")[1])))
        except (ValueError, IndexError):
            pass

        # Index 2: index finger motor value
        try:
            text = self.lbl_motor_index.text()
            if "：" in text:
                motor_values[2] = int(round(float(text.split("：")[1])))
        except (ValueError, IndexError):
            pass

        # Index 3: middle finger motor value
        try:
            text = self.lbl_motor_middle.text()
            if "：" in text:
                motor_values[3] = int(round(float(text.split("：")[1])))
        except (ValueError, IndexError):
            pass

        # Index 4: ring finger motor value
        try:
            text = self.lbl_motor_ring.text()
            if "：" in text:
                motor_values[4] = int(round(float(text.split("：")[1])))
        except (ValueError, IndexError):
            pass

        # Index 5: pinky finger motor value
        try:
            text = self.lbl_motor_pinky.text()
            if "：" in text:
                motor_values[5] = int(round(float(text.split("：")[1])))
        except (ValueError, IndexError):
            pass

        # Clamp all values to [0, 255]
        pose = [max(0, min(255, v)) for v in motor_values]

        try:
            api.finger_move(pose=pose)
        except Exception as exc:
            print(f"[LinkerHand] 发送失败: {exc}")
            self._on_disconnect()

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

    def _extract_z_deg(self, skel, channel_order: int):
        """Read Z-angle from Euler if present, otherwise derive from quaternion."""
        if bool(getattr(skel, "contains_euler_degree", 0)):
            return float(skel.euler_degree[2])

        if bool(getattr(skel, "contains_quat_wxyz", 0)):
            try:
                from src.xsqeconverter import quat_to_euler_degree
                e = quat_to_euler_degree(list(skel.quat_wxyz), int(channel_order))
                return float(e[2])
            except Exception:
                return None

        return None

    def _refresh_from_latest_frame(self):
        """Update rotation sum display for all fingers at fixed 30Hz."""
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
            axis = info.get("axis", "y")  # default to Y-axis for backward compatibility
            
            # Choose extraction method based on axis
            if axis == "z":
                extract_func = self._extract_z_deg
            else:
                extract_func = self._extract_y_deg
            
            total_abs = 0.0
            valid_count = 0
            
            if finger_key == "右手拇指弯曲":
                # Thumb bend: sum Y angles with sign first, then abs
                # Only negative Y values are valid (bending); positive → 0
                total_signed = 0.0
                for bone_name in bone_names:
                    try:
                        bone_idx = BoneIndex[bone_name]
                        skel = skeleton_by_index.get(bone_idx)
                        if skel is None:
                            skel = skeleton_by_name.get(bone_name)
                        if skel is not None:
                            angle_deg = extract_func(skel, channel_order)
                            if angle_deg is not None:
                                # Clamp positive values to 0: only bending (negative) counts
                                total_signed += min(angle_deg, 0.0)
                                valid_count += 1
                    except (KeyError, ValueError):
                        pass
                total_abs = abs(total_signed)
            else:
                # Other fingers: sum absolute rotation angles per bone
                for bone_name in bone_names:
                    try:
                        bone_idx = BoneIndex[bone_name]
                        skel = skeleton_by_index.get(bone_idx)
                        if skel is None:
                            skel = skeleton_by_name.get(bone_name)
                        if skel is not None:
                            angle_deg = extract_func(skel, channel_order)
                            if angle_deg is not None:
                                total_abs += abs(angle_deg)
                                valid_count += 1
                    except (KeyError, ValueError):
                        pass
            
            # Always show a numeric value so the UI does not stay blank.
            label.setText(f"{info['base_text']}：{total_abs:.1f}")
        
        # Calculate motor angle: clamp thumb bend to [0, THUMB_BEND_MAX_DEG], then invert
        try:
            thumb_text = self.finger_labels["右手拇指弯曲"]["label"].text()
            if "：" in thumb_text:
                raw_value = float(thumb_text.split("：")[1])
                clamped_value = max(0.0, min(self.THUMB_BEND_MAX_DEG, raw_value))
                motor_value = 255.0 * (1.0 - clamped_value / self.THUMB_BEND_MAX_DEG)
                self.lbl_motor_thumb.setText(f"拇指弯曲：{motor_value:.1f}")
        except (KeyError, ValueError, IndexError):
            pass

        # Calculate thumb adduction motor value: 0~120 → 255~0
        try:
            adduction_text = self.finger_labels["右手拇指侧摆"]["label"].text()
            if "：" in adduction_text:
                raw_adduction = float(adduction_text.split("：")[1])
                clamped_adduction = max(0.0, min(120.0, raw_adduction))
                mapped_adduction = (clamped_adduction / 120.0) * 255.0
                motor_adduction = 255.0 - mapped_adduction
                self.lbl_motor_thumb_adduction.setText(f"拇指侧摆：{motor_adduction:.1f}")
        except (KeyError, ValueError, IndexError):
            pass

        # Calculate index finger motor value: same as thumb (0~255 → 255~0)
        try:
            index_text = self.finger_labels["右手食指弯曲"]["label"].text()
            if "：" in index_text:
                raw_index = float(index_text.split("：")[1])
                clamped_index = max(0.0, min(255.0, raw_index))
                motor_index = 255.0 - clamped_index
                self.lbl_motor_index.setText(f"食指弯曲：{motor_index:.1f}")
        except (KeyError, ValueError, IndexError):
            pass

        # Calculate middle finger motor value: same as thumb (0~255 → 255~0)
        try:
            middle_text = self.finger_labels["右手中指弯曲"]["label"].text()
            if "：" in middle_text:
                raw_middle = float(middle_text.split("：")[1])
                clamped_middle = max(0.0, min(255.0, raw_middle))
                motor_middle = 255.0 - clamped_middle
                self.lbl_motor_middle.setText(f"中指弯曲：{motor_middle:.1f}")
        except (KeyError, ValueError, IndexError):
            pass

        # Calculate ring finger motor value: same as thumb (0~255 → 255~0)
        try:
            ring_text = self.finger_labels["右手无名指弯曲"]["label"].text()
            if "：" in ring_text:
                raw_ring = float(ring_text.split("：")[1])
                clamped_ring = max(0.0, min(255.0, raw_ring))
                motor_ring = 255.0 - clamped_ring
                self.lbl_motor_ring.setText(f"无名指弯曲：{motor_ring:.1f}")
        except (KeyError, ValueError, IndexError):
            pass

        # Calculate pinky finger motor value: same as thumb (0~255 → 255~0)
        try:
            pinky_text = self.finger_labels["右手小指弯曲"]["label"].text()
            if "：" in pinky_text:
                raw_pinky = float(pinky_text.split("：")[1])
                clamped_pinky = max(0.0, min(255.0, raw_pinky))
                motor_pinky = 255.0 - clamped_pinky
                self.lbl_motor_pinky.setText(f"小指弯曲：{motor_pinky:.1f}")
        except (KeyError, ValueError, IndexError):
            pass
