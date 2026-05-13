"""
Bone Viewer Widget for MotionGlove 3D Viewer.
Displays skeletal hierarchy with checkboxes and real-time Euler angle display.
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QScrollArea
)
from PySide6.QtCore import Qt


class BoneViewerWidget(QWidget):
    """Display skeletal hierarchy with checkboxes and Euler angle monitoring."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bone_checkboxes = {}  # bone_name -> QCheckBox
        self.bone_labels = {}      # bone_name -> QLabel (for Euler angles)
        self.bone_indices = {}     # bone_name -> BoneIndex value
        self._bone_label_text_cache = {}  # bone_name -> last shown text
        self.current_frame = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI with skeletal hierarchy."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(3)
        
        # Scroll area for bone list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(2)
        
        # Load bone tree structure
        self._build_bone_tree(scroll_layout)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        self.setLayout(main_layout)
    
    def _load_bone_tree_from_file(self):
        """Load bone tree structure from kinemHumanHandsSkeleton32Index_tree.md."""
        candidates = [
            Path(__file__).parent.parent / "src" / "kinemHumanHandsSkeleton32Index_tree.md",
            Path(__file__).parent / ".." / "src" / "kinemHumanHandsSkeleton32Index_tree.md",
        ]
        
        # Try to find the file
        tree_file = None
        for candidate in candidates:
            try:
                if candidate.exists():
                    tree_file = candidate
                    break
            except Exception:
                pass
        
        bones_with_indent = []
        if tree_file:
            try:
                with open(tree_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        # Count leading spaces to determine indent level
                        stripped = line.lstrip()
                        indent_level = (len(line) - len(stripped)) // 1
                        bone_name = stripped.strip()
                        bones_with_indent.append((bone_name, indent_level))
            except Exception:
                pass
        
        # Fallback to hardcoded order if file not found
        if not bones_with_indent:
            bones_with_indent = [
                ("RightHand", 0),
                ("RightHandThumb1", 1),
                ("RightHandThumb2", 2),
                ("RightHandThumb3", 3),
                ("RightHandIndex1", 1),
                ("RightHandIndex2", 2),
                ("RightHandIndex3", 3),
                ("RightHandMiddle1", 1),
                ("RightHandMiddle2", 2),
                ("RightHandMiddle3", 3),
                ("RightHandRing1", 1),
                ("RightHandRing2", 2),
                ("RightHandRing3", 3),
                ("RightHandPinky1", 1),
                ("RightHandPinky2", 2),
                ("RightHandPinky3", 3),
                ("LeftHand", 0),
                ("LeftHandThumb1", 1),
                ("LeftHandThumb2", 2),
                ("LeftHandThumb3", 3),
                ("LeftHandIndex1", 1),
                ("LeftHandIndex2", 2),
                ("LeftHandIndex3", 3),
                ("LeftHandMiddle1", 1),
                ("LeftHandMiddle2", 2),
                ("LeftHandMiddle3", 3),
                ("LeftHandRing1", 1),
                ("LeftHandRing2", 2),
                ("LeftHandRing3", 3),
                ("LeftHandPinky1", 1),
                ("LeftHandPinky2", 2),
                ("LeftHandPinky3", 3),
            ]
        
        return bones_with_indent
    
    def _build_bone_tree(self, layout):
        """Build the bone tree with checkboxes and labels."""
        from src.definitions import BoneIndex, BONE_NAMES_32
        
        # Map bone names to BoneIndex values
        for bone_name in BONE_NAMES_32:
            try:
                self.bone_indices[bone_name] = BoneIndex[bone_name]
            except KeyError:
                # Some bones might not exist in BoneIndex
                pass
        
        # Load bone hierarchy from file or use fallback
        bone_hierarchy = self._load_bone_tree_from_file()
        
        for bone_name, indent_level in bone_hierarchy:
            if bone_name not in self.bone_indices:
                continue
                
            # Create row: [indent] [checkbox] [bone_name] [euler_label]
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)
            
            # Indentation
            indent_widget = QWidget()
            indent_widget.setFixedWidth(indent_level * 15)
            row_layout.addWidget(indent_widget)
            
            # Checkbox
            checkbox = QCheckBox(bone_name)
            checkbox.setMaximumWidth(150)
            checkbox.setChecked(True)  # 默认选中
            row_layout.addWidget(checkbox)
            self.bone_checkboxes[bone_name] = checkbox
            
            # Euler angle label
            euler_label = QLabel("—")
            euler_label.setMaximumWidth(120)
            euler_label.setStyleSheet("color: #888888; font-size: 11px;")
            row_layout.addWidget(euler_label)
            self.bone_labels[bone_name] = euler_label
            
            # Add stretch to push content to left
            row_layout.addStretch()
            
            # Add to main layout
            layout.addLayout(row_layout)
    
    def update_euler_angles(self, frame):
        """Update Euler angle display for all checked bones."""
        if frame is None:
            return
        
        self.current_frame = frame
        
        # Build a lookup map: bone_index -> skeleton for faster queries
        skeleton_by_index = {}
        for skel in frame.skeletons:
            # 使用 bone_index 作为键，但同一个 bone_index 只存一个（防止重复）
            if skel.bone_index not in skeleton_by_index:
                skeleton_by_index[skel.bone_index] = skel
        
        # Update labels for checked bones
        for bone_name, checkbox in self.bone_checkboxes.items():
            if not checkbox.isChecked():
                if self._bone_label_text_cache.get(bone_name) != "—":
                    self.bone_labels[bone_name].setText("—")
                    self._bone_label_text_cache[bone_name] = "—"
                continue
            
            # Find the skeleton with this bone name
            bone_idx = self.bone_indices.get(bone_name)
            if bone_idx is None:
                continue
            
            euler_text = "—"
            # 用构建的 map 进行快速查询
            skel = skeleton_by_index.get(bone_idx)
            if skel is not None and skel.contains_euler_degree:
                ex, ey, ez = skel.euler_degree
                euler_text = f"({ex:.1f}°, {ey:.1f}°, {ez:.1f}°)"

            if self._bone_label_text_cache.get(bone_name) != euler_text:
                self.bone_labels[bone_name].setText(euler_text)
                self._bone_label_text_cache[bone_name] = euler_text
