import sys
import os
import enum
import math
import threading
import time
import argparse
import subprocess


def _force_utf8_stdio():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_force_utf8_stdio()

# ── 路径：libs/ 和 python_draw3d/ 均在当前目录 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LIBS_DIR   = os.path.join(_SCRIPT_DIR, "libs")
_DRAW3D_DIR = os.path.join(_SCRIPT_DIR, "python_draw3d")
_UI_DIR     = os.path.join(_SCRIPT_DIR, "ui")
sys.path.insert(0, _DRAW3D_DIR)
sys.path.insert(0, _LIBS_DIR)
sys.path.insert(0, _UI_DIR)

import vtk
from vtk_axes import add_axes_to_renderer
from camera_control import bind_space_reset_camera, setup_camera
from bone_joint_actor import BoneJointActor
from bone_link_actor import BoneLinkActor
from overlay_text import add_overlay_text
from ground_plane import build_ground_plane_actor
from fps_counter import FpsCounter
from vtk_fps_overlay import VtkFpsOverlay

from src import motionGloveSDK
from src.definitions import BoneIndex, KHHS42_SKELETON_COUNT, GloveFrame

# ─────────────────────────────────────────────
#  配置
# ─────────────────────────────────────────────

RX_PORT      = 5001
GLOVE_NAME   = "Glove1"
WINDOW_WIDTH  = 1366
WINDOW_HEIGHT = 768

# ── 启动模式 ────────────────────────────────────
class AppMode(enum.Enum):
    UDP_STREAM   = "udp"   # 实时 UDP 数据流（默认）
    CSV_PLAYBACK = "csv"   # 回放硬盘上的 CSV 文件

# 由命令行参数 --bootmode 决定，main() 中赋值
APP_MODE: AppMode = AppMode.UDP_STREAM

SPHERE_RADIUS_PALM   = 0.005
SPHERE_RADIUS_FINGER = 0.005

COLOR_RIGHT = (0.3, 0.8, 1.0)
COLOR_LEFT  = (1.0, 0.5, 0.2)

BONE_LINK_COLOR_RIGHT = (0.3, 0.8, 1.0)
BONE_LINK_COLOR_LEFT  = (1.0, 0.5, 0.2)
BONE_LINK_WIDTH       = 3.0

_BONE_LINKS: list[tuple[int, int]] = [
    # 右手
    (BoneIndex.RightHandThumb1,    BoneIndex.RightHand),
    (BoneIndex.RightHandThumb2,    BoneIndex.RightHandThumb1),
    (BoneIndex.RightHandThumb3,    BoneIndex.RightHandThumb2),
    (BoneIndex.RightHandThumb3End, BoneIndex.RightHandThumb3),
    (BoneIndex.RightHandIndex1,    BoneIndex.RightHand),
    (BoneIndex.RightHandIndex2,    BoneIndex.RightHandIndex1),
    (BoneIndex.RightHandIndex3,    BoneIndex.RightHandIndex2),
    (BoneIndex.RightHandIndex3End, BoneIndex.RightHandIndex3),
    (BoneIndex.RightHandMiddle1,   BoneIndex.RightHand),
    (BoneIndex.RightHandMiddle2,   BoneIndex.RightHandMiddle1),
    (BoneIndex.RightHandMiddle3,   BoneIndex.RightHandMiddle2),
    (BoneIndex.RightHandMiddle3End,BoneIndex.RightHandMiddle3),
    (BoneIndex.RightHandRing1,     BoneIndex.RightHand),
    (BoneIndex.RightHandRing2,     BoneIndex.RightHandRing1),
    (BoneIndex.RightHandRing3,     BoneIndex.RightHandRing2),
    (BoneIndex.RightHandRing3End,  BoneIndex.RightHandRing3),
    (BoneIndex.RightHandPinky1,    BoneIndex.RightHand),
    (BoneIndex.RightHandPinky2,    BoneIndex.RightHandPinky1),
    (BoneIndex.RightHandPinky3,    BoneIndex.RightHandPinky2),
    (BoneIndex.RightHandPinky3End, BoneIndex.RightHandPinky3),
    # 左手
    (BoneIndex.LeftHandThumb1,     BoneIndex.LeftHand),
    (BoneIndex.LeftHandThumb2,     BoneIndex.LeftHandThumb1),
    (BoneIndex.LeftHandThumb3,     BoneIndex.LeftHandThumb2),
    (BoneIndex.LeftHandThumb3End,  BoneIndex.LeftHandThumb3),
    (BoneIndex.LeftHandIndex1,     BoneIndex.LeftHand),
    (BoneIndex.LeftHandIndex2,     BoneIndex.LeftHandIndex1),
    (BoneIndex.LeftHandIndex3,     BoneIndex.LeftHandIndex2),
    (BoneIndex.LeftHandIndex3End,  BoneIndex.LeftHandIndex3),
    (BoneIndex.LeftHandMiddle1,    BoneIndex.LeftHand),
    (BoneIndex.LeftHandMiddle2,    BoneIndex.LeftHandMiddle1),
    (BoneIndex.LeftHandMiddle3,    BoneIndex.LeftHandMiddle2),
    (BoneIndex.LeftHandMiddle3End, BoneIndex.LeftHandMiddle3),
    (BoneIndex.LeftHandRing1,      BoneIndex.LeftHand),
    (BoneIndex.LeftHandRing2,      BoneIndex.LeftHandRing1),
    (BoneIndex.LeftHandRing3,      BoneIndex.LeftHandRing2),
    (BoneIndex.LeftHandRing3End,   BoneIndex.LeftHandRing3),
    (BoneIndex.LeftHandPinky1,     BoneIndex.LeftHand),
    (BoneIndex.LeftHandPinky2,     BoneIndex.LeftHandPinky1),
    (BoneIndex.LeftHandPinky3,     BoneIndex.LeftHandPinky2),
    (BoneIndex.LeftHandPinky3End,  BoneIndex.LeftHandPinky3),
]

# 每根骨骼的父骨骼索引（-1 表示根骨骼，无父）
# 拓扑顺序：根在前，子骨骼在后，保证全局四元数计算时父节点已先算完
_BONE_PARENT: list[int] = [-1] * KHHS42_SKELETON_COUNT
for _child, _par in _BONE_LINKS:
    _BONE_PARENT[_child] = _par
# RightHand(0) 和 LeftHand(21) 保持 -1（根骨骼）

# End-node bone indices — position-only rendering (no axis tripods)
_END_BONE_INDICES: set[int] = {b for b in BoneIndex if b.name.endswith("End")}

# 32 节点流（无 End）时，为每根手指第三节补一个固定 20mm 虚拟末梢点
_VIRTUAL_TIP_LENGTH_M = 0.02
_VIRTUAL_TIP_RULES: list[tuple[int, int, int]] = [
    # (virtual_end_idx, third_idx, second_idx)
    (BoneIndex.RightHandThumb3End, BoneIndex.RightHandThumb3, BoneIndex.RightHandThumb2),
    (BoneIndex.RightHandIndex3End, BoneIndex.RightHandIndex3, BoneIndex.RightHandIndex2),
    (BoneIndex.RightHandMiddle3End, BoneIndex.RightHandMiddle3, BoneIndex.RightHandMiddle2),
    (BoneIndex.RightHandRing3End, BoneIndex.RightHandRing3, BoneIndex.RightHandRing2),
    (BoneIndex.RightHandPinky3End, BoneIndex.RightHandPinky3, BoneIndex.RightHandPinky2),
    (BoneIndex.LeftHandThumb3End, BoneIndex.LeftHandThumb3, BoneIndex.LeftHandThumb2),
    (BoneIndex.LeftHandIndex3End, BoneIndex.LeftHandIndex3, BoneIndex.LeftHandIndex2),
    (BoneIndex.LeftHandMiddle3End, BoneIndex.LeftHandMiddle3, BoneIndex.LeftHandMiddle2),
    (BoneIndex.LeftHandRing3End, BoneIndex.LeftHandRing3, BoneIndex.LeftHandRing2),
    (BoneIndex.LeftHandPinky3End, BoneIndex.LeftHandPinky3, BoneIndex.LeftHandPinky2),
]

# CI/无界面环境下用于自动化冒烟测试
_CI_MODE = os.environ.get("MOTIONGLOVE_CI", "").strip().lower() in ("1", "true", "yes") or \
           os.environ.get("CI", "").strip().lower() in ("1", "true", "yes")

_ci_render_env = os.environ.get("MOTIONGLOVE_CI_RENDER", "").strip().lower()
if _ci_render_env:
    _CI_RENDER_ENABLED = _ci_render_env in ("1", "true", "yes")
else:
    _CI_RENDER_ENABLED = not sys.platform.startswith("win")

_CI_RENDER_SECONDS = float(os.environ.get("MOTIONGLOVE_CI_SECONDS", "0.5"))

# ─────────────────────────────────────────────


def _bone_radius(bone_idx):
    if bone_idx in (BoneIndex.RightHand, BoneIndex.LeftHand):
        return SPHERE_RADIUS_PALM
    return SPHERE_RADIUS_FINGER


def _bone_color(bone_idx):
    return COLOR_RIGHT if bone_idx < BoneIndex.LeftHand else COLOR_LEFT


def _normalize_vec3(v):
    x, y, z = v
    n = math.sqrt(x * x + y * y + z * z)
    if n <= 1e-9:
        return None
    return (x / n, y / n, z / n)


def _quat_rotate_vec3(q, v):
    qw, qx, qy, qz = q
    vx, vy, vz = v
    tx = 2.0 * (qy * vz - qz * vy)
    ty = 2.0 * (qz * vx - qx * vz)
    tz = 2.0 * (qx * vy - qy * vx)
    return (
        vx + qw * tx + (qy * tz - qz * ty),
        vy + qw * ty + (qz * tx - qx * tz),
        vz + qw * tz + (qx * ty - qy * tx),
    )


def _install_configured_translator(app):
    from PySide6.QtCore import QTranslator

    try:
        from src.config_io import read_config
        cfg = read_config()
        lang_code = cfg.get("language", "en")
    except Exception:
        lang_code = "en"

    existing_translator = getattr(app, "_motionglove_translator", None)
    existing_lang = getattr(app, "_motionglove_language", None)
    if existing_translator is not None and existing_lang == lang_code:
        return existing_translator, lang_code

    if existing_translator is not None:
        app.removeTranslator(existing_translator)

    translator = QTranslator()
    qm_path = os.path.join(_SCRIPT_DIR, "translations", f"{lang_code}.qm")
    try:
        if os.path.exists(qm_path) and translator.load(qm_path):
            app.installTranslator(translator)
        else:
            print(f"Translation not loaded (missing): {qm_path}")
    except Exception as e:
        print(f"Error loading translator: {e}")

    app._motionglove_translator = translator
    app._motionglove_language = lang_code
    return translator, lang_code


# ─────────────────────────────────────────────
#  CI 快速路径（不构建任何 Qt 对象）
# ─────────────────────────────────────────────

def _run_ci_no_render():
    """仅做 VTK 导入 + 基础管线冒烟测试，不触发 OpenGL 上下文。"""
    try:
        renderer = vtk.vtkRenderer()
        sphere = vtk.vtkSphereSource()
        sphere.SetRadius(1.0)
        sphere.SetThetaResolution(8)
        sphere.SetPhiResolution(8)
        sphere.Update()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        renderer.AddActor(actor)

        print("[CI] VTK pipeline smoke test passed (render skipped).")
    finally:
        motionGloveSDK.MotionGloveSDK_CloseUDPPort()


# ─────────────────────────────────────────────
#  PySide6 主窗口
# ─────────────────────────────────────────────

def _build_qt_app():
    """构建并运行 PySide6 主窗口（含 VTK 嵌入）。"""
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QHBoxLayout,
        QMessageBox, QSizePolicy, QMenu,
    )
    from PySide6.QtCore import QTimer, QEvent, Qt, QTranslator
    from PySide6.QtGui import QAction, QActionGroup
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    from left_panel_widget import LeftPanelWidget
    from draw_config_widget import DrawConfigWidget
    from csv_import_widget import CsvImportWidget

    class MotionGloveMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle(self.tr("MotionGlove 3D Viewer"))
            self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

            self._quit_event = threading.Event()
            self._latest_frame: list[GloveFrame | None] = [None]
            self._frame_lock = threading.Lock()
            self._axes_visible = True
            self._ground_visible = True
            self._rb_press_pos = None   # 记录右键按下时的位置，用于判断是否发生了拖拽
            self._total_frames = 0       # 本次接收会话的累计帧数
            self._dropped_frames = 0     # 本次接收会话的累计丢失帧数
            self._last_frame_fn = None   # 上一次消费的帧序号（在 _poll 线程中更新）
            self._drop_event: tuple[int, int, int] | None = None  # (first_lost_fn, last_lost_fn, cumulative)
            self._fps_counter = FpsCounter()

            # CSV 回放模式专用
            self._csv_reader = None      # CsvFrameReader 实例
            self._csv_playing: bool = False          # 是否正在播放
            self._csv_next_frame_time: float = 0.0   # 下一帧应推进的单调时刻（秒）

            self._build_menu()
            self._build_central()
            self._build_status_bar()
            self._build_vtk_scene()
            if APP_MODE == AppMode.UDP_STREAM:
                self._start_sdk_poll()
            else:
                self._start_csv_playback()
            self._start_render_timer()

        # ── 菜单栏 ────────────────────────────────────────
        def _build_menu(self):
            menu_bar = self.menuBar()

            file_menu = menu_bar.addMenu(self.tr("文件(&F)"))
            exit_action = QAction(self.tr("退出(&X)"), self)
            exit_action.triggered.connect(QApplication.quit)
            file_menu.addAction(exit_action)

            win_menu = menu_bar.addMenu(self.tr("窗口(&W)"))
            self._action_show_left = QAction(self.tr("数据面板"), self)
            self._action_show_left.setCheckable(True)
            self._action_show_left.setChecked(True)
            win_menu.addAction(self._action_show_left)

            self._action_show_right = QAction(self.tr("配置面板"), self)
            self._action_show_right.setCheckable(True)
            self._action_show_right.setChecked(True)
            win_menu.addAction(self._action_show_right)

            # 设置 -> 语言 菜单
            settings_menu = menu_bar.addMenu(self.tr("设置(&S)"))
            language_menu = settings_menu.addMenu(self.tr("语言"))
            # QActionGroup 用于互斥选择
            ag = QActionGroup(self)
            ag.setExclusive(True)
            act_zh = QAction(self.tr("中文"), self)
            act_zh.setCheckable(True)
            act_en = QAction(self.tr("English"), self)
            act_en.setCheckable(True)
            ag.addAction(act_zh)
            ag.addAction(act_en)
            language_menu.addAction(act_zh)
            language_menu.addAction(act_en)

            # 读取当前配置以设置初始选中状态
            try:
                from src.config_io import read_config
                cfg = read_config()
                cur = cfg.get("language", "en")
            except Exception:
                cur = "en"
            if cur.lower() in ("zh_cn", "zh", "zh-cn"):
                act_zh.setChecked(True)
            else:
                act_en.setChecked(True)

            act_zh.triggered.connect(lambda: self._on_language_selected("zh_CN"))
            act_en.triggered.connect(lambda: self._on_language_selected("en"))

            help_menu = menu_bar.addMenu(self.tr("帮助(&H)"))
            about_qt_action = QAction(self.tr("关于 Qt(&Q)"), self)
            about_qt_action.triggered.connect(lambda: QMessageBox.aboutQt(self))
            help_menu.addAction(about_qt_action)

            oss_action = QAction(self.tr("开源声明(&O)"), self)
            oss_action.triggered.connect(self._show_oss_dialog)
            help_menu.addAction(oss_action)

        # ── 状态栏 ────────────────────────────────────────
        def _build_status_bar(self):
            self.statusBar().showMessage(self.tr("就绪"))

        def _show_oss_dialog(self):
            from oss_licenses_dialog import OssLicensesDialog
            dlg = OssLicensesDialog(self)
            dlg.exec()

        # ── 中央布局：左侧面板 + VTK 视口 ───────────────
        def _build_central(self):
            central = QWidget()
            self.setCentralWidget(central)
            h_layout = QHBoxLayout(central)
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(0)

            # ── 左侧面板：根据模式选择 ──
            if APP_MODE == AppMode.UDP_STREAM:
                self._left_panel = LeftPanelWidget()
                self._left_panel.btn_start.clicked.connect(self._on_start_clicked)
                self._left_panel.btn_stop.clicked.connect(self._on_stop_clicked)
                self._csv_panel = None
                left_widget: QWidget = self._left_panel
            else:
                self._csv_panel = CsvImportWidget()
                self._left_panel = None
                left_widget = self._csv_panel
            h_layout.addWidget(left_widget)

            # ── VTK 视口 ──
            self._vtk_widget = QVTKRenderWindowInteractor(central)
            self._vtk_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._vtk_widget.installEventFilter(self)
            h_layout.addWidget(self._vtk_widget)

            # ── 右侧绘图配置面板 ──
            self._draw_config_widget = DrawConfigWidget()
            h_layout.addWidget(self._draw_config_widget)
            self._last_applied_config = None

            # 连接窗口菜单的显示/隐藏信号（widget 已创建后才能连接）
            self._action_show_left.triggered.connect(
                lambda checked: left_widget.setVisible(checked)
            )
            self._action_show_right.triggered.connect(
                lambda checked: self._draw_config_widget.setVisible(checked)
            )

        # ── VTK 场景 ──────────────────────────────────────
        def _build_vtk_scene(self):
            self._renderer = vtk.vtkRenderer()
            self._renderer.SetBackground(0.10, 0.10, 0.16)

            render_window = self._vtk_widget.GetRenderWindow()
            render_window.AddRenderer(self._renderer)

            self._interactor = render_window.GetInteractor()
            self._interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

            # 42 个关节演员
            self._joint_actors = [
                BoneJointActor(self._renderer,
                               radius=_bone_radius(i),
                               sphere_color=_bone_color(i))
                for i in range(KHHS42_SKELETON_COUNT)
            ]

            # 骨骼连线演员
            def _link_color(child_idx):
                return BONE_LINK_COLOR_RIGHT if child_idx < BoneIndex.LeftHand else BONE_LINK_COLOR_LEFT

            self._link_actors = [
                BoneLinkActor(self._renderer,
                              color=_link_color(child),
                              line_width=BONE_LINK_WIDTH)
                for child, _ in _BONE_LINKS
            ]

            self._axes_actor = add_axes_to_renderer(self._renderer, length=0.025)

            # 地平面网格（默认隐藏）
            self._ground_actor = build_ground_plane_actor(extent=0.30, spacing=0.05)
            self._ground_actor.SetVisibility(True)
            self._renderer.AddActor(self._ground_actor)

            _font_file = os.path.join(_SCRIPT_DIR, "fonts", "HarmonyOS_Sans_SC_Regular.ttf")
            if not os.path.isfile(_font_file):
                _font_file = None
            add_overlay_text(
                self._renderer,
                text=self.tr("鼠标左键 旋转    鼠标右键 缩放    鼠标中键 平移    空格 重置视角"),
                font_file=_font_file,
                font_size=15,
                color=(0.75, 0.75, 0.75),
                position=(0.5, 0.97),
                justification="center",
            )

            # 左下角渲染帧率叠加（默认不显示）
            self._render_fps_overlay = VtkFpsOverlay(
                self._renderer,
                font_file=_font_file,
                visible=False,
            )

            # 右上角小坐标系（gizmo），使用 vtkOrientationMarkerWidget
            self._gizmo_axes_actor = vtk.vtkAxesActor()
            self._gizmo_axes_actor.SetTotalLength(0.08, 0.08, 0.08)
            self._gizmo_axes_actor.SetShaftTypeToCylinder()
            # 禁用 caption 自动缩放以保证在小尺寸下显示合理
            for cap in (
                self._gizmo_axes_actor.GetXAxisCaptionActor2D(),
                self._gizmo_axes_actor.GetYAxisCaptionActor2D(),
                self._gizmo_axes_actor.GetZAxisCaptionActor2D(),
            ):
                cap.GetTextActor().SetTextScaleModeToNone()

            self._gizmo_marker = vtk.vtkOrientationMarkerWidget()
            self._gizmo_marker.SetOrientationMarker(self._gizmo_axes_actor)
            self._gizmo_marker.SetInteractor(self._interactor)
            # 放置在右上角 -- 小一点并留出边距
            self._gizmo_marker.SetViewport(0.84, 0.84, 0.99, 0.99)
            self._gizmo_marker.SetEnabled(1)
            # 不让小坐标系本身响应拖拽（只作为指示器）
            self._gizmo_marker.InteractiveOff()

            self._vtk_widget.Initialize()
            setup_camera(self._renderer, render_window)
            self._reset_camera_cb = bind_space_reset_camera(self._interactor, self._renderer, render_window)

        # ── SDK 轮询线程 ──────────────────────────────────
        def _start_sdk_poll(self):
            def _poll():
                while not self._quit_event.is_set():
                    # 把队列中所有积压帧逐一消费，做连续性检测，取最新帧用于渲染
                    latest = None
                    while motionGloveSDK.MotionGloveSDK_isGloveNewFramePending(GLOVE_NAME):
                        frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame(GLOVE_NAME)
                        motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending(GLOVE_NAME)
                        if frame is None:
                            continue
                        fn = frame.header.frame_number
                        with self._frame_lock:
                            # 连续性检测
                            if self._last_frame_fn is not None:
                                lost = fn - self._last_frame_fn - 1
                                if lost > 0:
                                    self._dropped_frames += lost
                                    self._drop_event = (
                                        self._last_frame_fn + 1,
                                        fn - 1,
                                        self._dropped_frames,
                                    )
                            self._total_frames += 1
                            self._last_frame_fn = fn
                            self._fps_counter.tick()
                            latest = frame
                    if latest is not None:
                        with self._frame_lock:
                            self._latest_frame[0] = latest
                    time.sleep(0.002)

            threading.Thread(target=_poll, daemon=True).start()

        # ── Qt 定时器驱动渲染更新 ─────────────────────────
        def _start_render_timer(self):
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._on_timer)
            self._timer.start(16)   # ~60 fps

            self._fps_timer = QTimer(self)
            self._fps_timer.timeout.connect(self._on_fps_timer)
            self._fps_timer.start(1000)  # 1 秒刷新一次帧率

        def _on_fps_timer(self):
            self._fps_counter.snapshot()
            self._render_fps_overlay.snapshot()
            if self._left_panel is not None:
                self._left_panel.lbl_fps.setText(f"{self._fps_counter.fps()} fps")

        def _on_timer(self):
            # ── CSV 帧推进（时间戳驱动，避免双定时器相互干扰）──
            if APP_MODE == AppMode.CSV_PLAYBACK and self._csv_playing and self._csv_reader is not None:
                now = time.monotonic()
                if now >= self._csv_next_frame_time:
                    fps = self._csv_panel.fps if self._csv_panel is not None else 60
                    # 以固定步长推进，防止因渲染耗时导致的积累误差
                    self._csv_next_frame_time += 1.0 / fps
                    # 若严重滞后（如窗口最小化恢复），重置到当前时刻
                    if now - self._csv_next_frame_time > 1.0:
                        self._csv_next_frame_time = now + 1.0 / fps
                    frame = self._csv_reader.next_frame()
                    if frame is not None:
                        with self._frame_lock:
                            self._latest_frame[0] = frame
                    if self._csv_panel is not None:
                        self._csv_panel.set_frame_index(self._csv_reader.current_index)
                    if self._csv_reader.at_end:
                        self._csv_playing = False
                        if self._csv_panel is not None:
                            self._csv_panel.set_playing(False)
                        self.statusBar().showMessage(self.tr("播放完毕（末帧）"))

            # ── 推送绘图配置（仅在配置变化时）──────────────
            cfg = self._draw_config_widget.current_config()
            if cfg != self._last_applied_config:
                for ja in self._joint_actors:
                    ja.set_radius(cfg.joint_radius)
                    ja.set_sphere_color(*cfg.joint_color)
                    ja.set_axis_length(cfg.axis_length)
                for la in self._link_actors:
                    la.set_color(*cfg.link_color)
                    la.set_line_width(cfg.link_width)
                self._last_applied_config = cfg

            with self._frame_lock:
                frame = self._latest_frame[0]
                drop_event = self._drop_event
                self._drop_event = None

            # 显示丢帧警告（由 _poll 线程检测，主线程在此显示）
            if drop_event is not None:
                first, last, cumulative = drop_event
                self.statusBar().showMessage(
                    f"[丢帧] fn {first}"
                    + (f" ~ {last}" if last > first else "")
                    + f"  丢失 {last - first + 1} 帧（累计 {cumulative}）"
                )

            if frame is not None:
                positions: list = [None] * KHHS42_SKELETON_COUNT

                # 计算每根骨骼的全局四元数（局部四元数沿父链累乘）
                # 数据为 relative 旋转，全局 = parent_global * local
                global_quats: list = [None] * KHHS42_SKELETON_COUNT
                for skel in frame.skeletons:
                    i = skel.bone_index
                    if i < 0 or i >= KHHS42_SKELETON_COUNT:
                        continue
                    if not skel.contains_quat_wxyz:
                        continue
                    lw, lx, ly, lz = skel.quat_wxyz
                    par = _BONE_PARENT[i]
                    if par == -1 or global_quats[par] is None:
                        # 根骨骼或父链断裂：局部即全局
                        global_quats[i] = (lw, lx, ly, lz)
                    else:
                        # 全局 = parent_global * local（四元数左乘）
                        pw, px, py, pz = global_quats[par]
                        global_quats[i] = (
                            pw*lw - px*lx - py*ly - pz*lz,
                            pw*lx + px*lw + py*lz - pz*ly,
                            pw*ly - px*lz + py*lw + pz*lx,
                            pw*lz + px*ly - py*lx + pz*lw,
                        )
                    # End-node bones carry real position but no meaningful rotation
                    if i in _END_BONE_INDICES:
                        global_quats[i] = None

                for skel in frame.skeletons:
                    i = skel.bone_index
                    if i < 0 or i >= KHHS42_SKELETON_COUNT:
                        continue
                    if skel.contains_position and global_quats[i] is not None:
                        positions[i] = skel.position
                    elif skel.contains_position:
                        positions[i] = skel.position

                # 32 节点数据流：为每根手指第三节追加固定 20mm 虚拟末梢点
                if len(frame.skeletons) == 32:
                    for end_idx, third_idx, second_idx in _VIRTUAL_TIP_RULES:
                        p3 = positions[third_idx]
                        if p3 is None:
                            continue
                        p2 = positions[second_idx]
                        direction = None
                        if p2 is not None:
                            direction = _normalize_vec3((p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2]))
                        if direction is None and global_quats[third_idx] is not None:
                            direction = _normalize_vec3(_quat_rotate_vec3(global_quats[third_idx], (0.0, 1.0, 0.0)))
                        if direction is None:
                            continue
                        positions[end_idx] = [
                            p3[0] + direction[0] * _VIRTUAL_TIP_LENGTH_M,
                            p3[1] + direction[1] * _VIRTUAL_TIP_LENGTH_M,
                            p3[2] + direction[2] * _VIRTUAL_TIP_LENGTH_M,
                        ]
                        global_quats[end_idx] = None

                for i, ja in enumerate(self._joint_actors):
                    pos = positions[i]
                    if pos is None:
                        ja.hide()
                    elif global_quats[i] is not None:
                        ja.set_pose(pos, global_quats[i])
                    else:
                        ja.set_position_only(pos)

                for la, (child, parent) in zip(self._link_actors, _BONE_LINKS):
                    pc = positions[child]
                    pp = positions[parent]
                    if pc is not None and pp is not None:
                        la.update(pp, pc)
                    else:
                        la.hide()

                self._vtk_widget.GetRenderWindow().Render()
                self._render_fps_overlay.tick()

            # 更新左侧网络信息面板（UDP 模式）
            if self._left_panel is not None:
                addr = motionGloveSDK.MotionGloveSDK_GetLastRemoteAddr()
                if addr is not None:
                    self._left_panel.lbl_ip.setText(addr[0])
                    self._left_panel.lbl_port.setText(str(addr[1]))
                else:
                    self._left_panel.lbl_ip.setText(self.tr("Waiting..."))
                    self._left_panel.lbl_port.setText("—")
                actor_names = motionGloveSDK.MotionGloveSDK_GetActorNames()
                self._left_panel.lbl_actor_name.setText(", ".join(actor_names) if actor_names else "—")
                if frame is not None and self._last_frame_fn is not None:
                    self._left_panel.lbl_frame_id.setText(str(self._last_frame_fn))
                self._left_panel.lbl_total_frames.setText(str(self._total_frames))

        # ── 右键上下文菜单 ────────────────────────────────
        def eventFilter(self, obj, event):
            if obj is self._vtk_widget:
                t = event.type()
                if t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.RightButton:
                    self._rb_press_pos = event.pos()
                elif t == QEvent.Type.ContextMenu:
                    # 仅在右键短按（未发生拖拽）时弹出菜单
                    # 拖拽判定：按下到弹起的移动距离 > 5 px 则视为缩放操作
                    show = True
                    if self._rb_press_pos is not None:
                        delta = event.pos() - self._rb_press_pos
                        if delta.x() ** 2 + delta.y() ** 2 > 25:
                            show = False
                        self._rb_press_pos = None
                    if show:
                        self._show_context_menu(event.globalPos())
                    return True
            return super().eventFilter(obj, event)

        def _show_context_menu(self, global_pos):
            menu = QMenu(self)

            axes_label = self.tr("隐藏坐标轴") if self._axes_visible else self.tr("显示坐标轴")
            axes_action = menu.addAction(axes_label)

            ground_label = self.tr("隐藏地平面") if self._ground_visible else self.tr("显示地平面")
            ground_action = menu.addAction(ground_label)

            fps_label = self.tr("隐藏渲染帧率") if self._render_fps_overlay.is_visible() else self.tr("显示渲染帧率")
            fps_action = menu.addAction(fps_label)

            menu.addSeparator()
            reset_camera_action = menu.addAction(self.tr("重置视角"))

            action = menu.exec(global_pos)
            rw = self._vtk_widget.GetRenderWindow()

            if action is axes_action:
                self._axes_visible = not self._axes_visible
                self._axes_actor.SetVisibility(self._axes_visible)
                rw.Render()
            elif action is ground_action:
                self._ground_visible = not self._ground_visible
                self._ground_actor.SetVisibility(self._ground_visible)
                rw.Render()
            elif action is fps_action:
                self._render_fps_overlay.set_visible(not self._render_fps_overlay.is_visible())
                rw.Render()
            elif action is reset_camera_action:
                self._reset_camera_cb.reset()

        def _on_language_selected(self, lang_code: str) -> None:
            from PySide6.QtWidgets import QMessageBox, QApplication
            try:
                from src.config_io import read_config, write_config
            except Exception:
                QMessageBox.warning(self, self.tr("错误"), self.tr("无法访问配置模块，语言更改失败"))
                return

            cfg = read_config()
            cur = cfg.get("language", "en")
            if lang_code == cur:
                return
            cfg["language"] = lang_code
            try:
                write_config(cfg)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    self.tr("错误"),
                    self.tr("保存配置失败：{error}").format(error=e),
                )
                return

            # 提示重启
            reply = QMessageBox.question(
                self,
                self.tr("重启以应用语言"),
                self.tr("已更改语言，需要重启应用以生效。现在重启？"),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    subprocess.Popen([sys.executable] + sys.argv)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        self.tr("重启失败"),
                        self.tr("自动重启失败：{error}\n请手动重启应用。").format(error=e),
                    )
                    return
                QApplication.quit()

        # ── 窗口关闭处理 ──────────────────────────────────
        def closeEvent(self, event):
            self._timer.stop()
            self._fps_timer.stop()
            self._csv_playing = False
            self._quit_event.set()
            motionGloveSDK.MotionGloveSDK_CloseUDPPort()
            self._vtk_widget.GetRenderWindow().Finalize()
            self._interactor.TerminateApp()
            super().closeEvent(event)

        # ── CSV 回放控制 ──────────────────────────────────
        def _start_csv_playback(self):
            """CSV 模式初始化：连接面板信号。"""
            from src.csv_frame_reader import CsvFrameReader as _CsvFrameReader
            self._CsvFrameReader = _CsvFrameReader

            panel = self._csv_panel
            if panel is not None:
                panel.file_selected.connect(self._on_csv_file_selected)
                panel.play_pause_clicked.connect(self._on_csv_play_pause)
                panel.reset_clicked.connect(self._on_csv_reset)
                panel.fps_changed.connect(self._on_csv_fps_changed)
                panel.seek_started.connect(self._on_csv_seek_started)
                panel.seek_requested.connect(self._on_csv_seek)

        def _on_csv_file_selected(self, path: str) -> None:
            """用户选择了新的 CSV 文件。"""
            self._csv_playing = False
            if self._csv_panel is not None:
                self._csv_panel.set_playing(False)
            try:
                self._csv_reader = self._CsvFrameReader(path)
            except Exception as e:
                self.statusBar().showMessage(self.tr("加载失败：{error}").format(error=e))
                self._csv_reader = None
                return
            self.statusBar().showMessage(
                self.tr("已加载：{path}  共 {frames} 帧").format(
                    path=path,
                    frames=self._csv_reader.total_frames,
                )
            )
            if self._csv_panel is not None:
                self._csv_panel.set_total_frames(self._csv_reader.total_frames)
            # 渲染第一帧
            frame = self._csv_reader.next_frame()
            if frame is not None:
                with self._frame_lock:
                    self._latest_frame[0] = frame
            self._csv_reader.reset()

        def _on_csv_play_pause(self) -> None:
            """播放/暂停按钮切换。"""
            if self._csv_reader is None:
                return
            if self._csv_playing:
                # 暂停
                self._csv_playing = False
                if self._csv_panel is not None:
                    self._csv_panel.set_playing(False)
            else:
                # 开始/继续：若已到末帧则先重置
                if self._csv_reader.at_end:
                    self._csv_reader.reset()
                fps = self._csv_panel.fps if self._csv_panel is not None else 60
                self._csv_next_frame_time = time.monotonic() + 1.0 / fps
                self._csv_playing = True
                if self._csv_panel is not None:
                    self._csv_panel.set_playing(True)

        def _on_csv_reset(self) -> None:
            """重置到第一帧并停止播放。"""
            self._csv_playing = False
            if self._csv_panel is not None:
                self._csv_panel.set_playing(False)
            if self._csv_reader is not None:
                self._csv_reader.reset()
                frame = self._csv_reader.next_frame()
                if frame is not None:
                    with self._frame_lock:
                        self._latest_frame[0] = frame
                self._csv_reader.reset()
                if self._csv_panel is not None:
                    self._csv_panel.set_frame_index(0)

        def _on_csv_fps_changed(self, _fps: int) -> None:
            pass

        def _on_csv_seek_started(self) -> None:
            """用户按下进度条：暂停推进，不改变按钮状态。"""
            self._csv_playing = False

        def _on_csv_seek(self, target_index: int) -> None:
            """用户拖动进度条后跳转到指定帧（0-based），不自动恢复播放。"""
            if self._csv_reader is None:
                return
            total = self._csv_reader.total_frames
            if total == 0:
                return
            self._csv_playing = False
            if self._csv_panel is not None:
                self._csv_panel.set_playing(False)
            target_index = max(0, min(target_index, total - 1))
            self._csv_reader.seek(target_index)
            frame = self._csv_reader.next_frame()
            if frame is not None:
                with self._frame_lock:
                    self._latest_frame[0] = frame
            if self._csv_panel is not None:
                self._csv_panel.set_frame_index(self._csv_reader.current_index)

        # ── UDP 接收控制 ──────────────────────────────────
        def _on_stop_clicked(self):
            if self._left_panel is None:
                return
            motionGloveSDK.MotionGloveSDK_CloseUDPPort()
            self._fps_counter.reset()
            self._left_panel.set_receiving(False)
            self._left_panel.lbl_ip.setText(self.tr("Waiting..."))
            self._left_panel.lbl_port.setText("—")
            self._left_panel.lbl_actor_name.setText("—")
            self._left_panel.lbl_frame_id.setText("—")
            self._left_panel.lbl_fps.setText("0 fps")

        def _on_start_clicked(self):
            if self._left_panel is None:
                return
            nRet = motionGloveSDK.MotionGloveSDK_ListenUDPPort(RX_PORT)
            if nRet == 0:
                self._total_frames = 0
                self._dropped_frames = 0
                self._last_frame_fn = None
                self._fps_counter.reset()
                self._left_panel.lbl_total_frames.setText("0")
                self._left_panel.lbl_frame_id.setText("—")
                self._left_panel.lbl_fps.setText("0 fps")
                self._left_panel.set_receiving(True)
                self._left_panel.clear_error()
            else:
                from src.port_occupier import find_udp_port_occupier
                lines = find_udp_port_occupier(RX_PORT)
                if not lines:
                    lines = [f"端口 {RX_PORT} 绑定失败"]
                self._left_panel.show_port_error(lines)
                self._left_panel.set_receiving(False)

    app = QApplication.instance() or QApplication(sys.argv)
    translator, lang_code = _install_configured_translator(app)

    window = MotionGloveMainWindow()
    # 保存 translator 与当前语言，供运行时使用
    window._translator = translator
    window._current_language = lang_code
    window.show()
    return app, window


# ─────────────────────────────────────────────
#  入口
# ─────────────────────────────────────────────

def main():
    global APP_MODE

    # ── 命令行参数解析 ──────────────────────────────
    parser = argparse.ArgumentParser(
        prog="motionGloveSDK_example3_3dView.py",
        description="MotionGlove 3D Viewer — 实时 UDP 流或 CSV 文件回放",
    )
    parser.add_argument(
        "--bootmode",
        metavar="MODE",
        default=None,
        help="启动模式：udpstream（实时 UDP，默认）或 csvplayback（CSV 文件回放）",
    )
    args = parser.parse_args()

    def _parse_boot_mode(mode_text: str | None) -> AppMode | None:
        if mode_text is None:
            return None
        normalized = mode_text.strip().lower().replace("_", "").replace("-", "")
        if normalized == "udpstream":
            return AppMode.UDP_STREAM
        if normalized == "csvplayback":
            return AppMode.CSV_PLAYBACK
        return None

    # --bootmode 优先；未传入时读取 config.json 的 default_boot_mode
    cli_mode = _parse_boot_mode(args.bootmode)
    if args.bootmode is not None and cli_mode is None:
        parser.error(f"未知的 --bootmode 值：'{args.bootmode}'，可选：udpstream | csvplayback")

    if cli_mode is not None:
        APP_MODE = cli_mode
    else:
        cfg_mode = None
        try:
            from src.config_io import read_config
            cfg = read_config()
            cfg_mode = _parse_boot_mode(str(cfg.get("default_boot_mode", "")))
        except Exception:
            cfg_mode = None

        # 配置有有效默认启动模式时，直接进入对应功能
        if cfg_mode is not None:
            APP_MODE = cfg_mode
        # 配置为空、缺失或非法时，保留原逻辑：弹出模式选择对话框
        else:
        # CI 环境且不需要渲染时，直接进入 UDP 模式
            if _CI_MODE and not _CI_RENDER_ENABLED:
                APP_MODE = AppMode.UDP_STREAM
            else:
                from PySide6.QtWidgets import QApplication as _QApp
                app = _QApp.instance() or _QApp(sys.argv)
                _install_configured_translator(app)
                # Import the boot dialog lazily to avoid importing PySide6 in headless CI
                from src.boot_mode_dialog import show_boot_mode_dialog
                chosen = show_boot_mode_dialog(AppMode.UDP_STREAM, AppMode.CSV_PLAYBACK)
                if chosen is None:
                    sys.exit(0)  # 用户关闭对话框，直接退出
                APP_MODE = chosen

    # CSV 模式下不绑定 UDP 端口
    _port_error_lines: list[str] = []
    if APP_MODE == AppMode.UDP_STREAM:
        print(f"UDP Bind IP:port: 0.0.0.0:{RX_PORT}")
        nRet = motionGloveSDK.MotionGloveSDK_ListenUDPPort(RX_PORT)
        if nRet == -1:
            print(f"端口 {RX_PORT} 绑定失败，正在查询占用程序…")
            from src.port_occupier import find_udp_port_occupier
            _port_error_lines = find_udp_port_occupier(RX_PORT)
            if not _port_error_lines:
                _port_error_lines = [f"端口 {RX_PORT} 绑定失败"]
            for line in _port_error_lines:
                print(line)
        else:
            print(f"[UDP] 端口 {RX_PORT} 绑定成功，开始接收数据...")

    # ── CI 快速路径：不构建任何 Qt 对象 ──
    if _CI_MODE and not _CI_RENDER_ENABLED:
        _run_ci_no_render()
        return

    # ── CI 离屏渲染路径：设置无头 Qt 平台 ──
    if _CI_MODE and _CI_RENDER_ENABLED:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    app, window = _build_qt_app()

    if APP_MODE == AppMode.UDP_STREAM and window._left_panel is not None:
        if _port_error_lines:
            window._left_panel.show_port_error(_port_error_lines)
            window._left_panel.set_receiving(False)
        else:
            window._left_panel.set_receiving(True)

    if _CI_MODE:
        # CI 渲染冒烟测试：渲染一帧后自动退出
        from PySide6.QtCore import QTimer as _QTimer
        def _ci_exit():
            window._vtk_widget.GetRenderWindow().Render()
            print("[CI] Offscreen render smoke test passed.")
            app.quit()
        _QTimer.singleShot(int(_CI_RENDER_SECONDS * 1000), _ci_exit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
