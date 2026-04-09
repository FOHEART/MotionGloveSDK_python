import sys
import os
import threading
import time


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

from src import motionGloveSDK
from src.definitions import BoneIndex, KHHS32_SKELETON_COUNT, GloveFrame

# ─────────────────────────────────────────────
#  配置
# ─────────────────────────────────────────────

RX_PORT      = 5001
GLOVE_NAME   = "Glove1"
WINDOW_WIDTH  = 1366
WINDOW_HEIGHT = 768

SPHERE_RADIUS_PALM   = 0.005
SPHERE_RADIUS_FINGER = 0.005

COLOR_RIGHT = (0.3, 0.8, 1.0)
COLOR_LEFT  = (1.0, 0.5, 0.2)

BONE_LINK_COLOR_RIGHT = (0.3, 0.8, 1.0)
BONE_LINK_COLOR_LEFT  = (1.0, 0.5, 0.2)
BONE_LINK_WIDTH       = 3.0

_BONE_LINKS: list[tuple[int, int]] = [
    # 右手
    (BoneIndex.RightHandThumb1,  BoneIndex.RightHand),
    (BoneIndex.RightHandThumb2,  BoneIndex.RightHandThumb1),
    (BoneIndex.RightHandThumb3,  BoneIndex.RightHandThumb2),
    (BoneIndex.RightHandIndex1,  BoneIndex.RightHand),
    (BoneIndex.RightHandIndex2,  BoneIndex.RightHandIndex1),
    (BoneIndex.RightHandIndex3,  BoneIndex.RightHandIndex2),
    (BoneIndex.RightHandMiddle1, BoneIndex.RightHand),
    (BoneIndex.RightHandMiddle2, BoneIndex.RightHandMiddle1),
    (BoneIndex.RightHandMiddle3, BoneIndex.RightHandMiddle2),
    (BoneIndex.RightHandRing1,   BoneIndex.RightHand),
    (BoneIndex.RightHandRing2,   BoneIndex.RightHandRing1),
    (BoneIndex.RightHandRing3,   BoneIndex.RightHandRing2),
    (BoneIndex.RightHandPinky1,  BoneIndex.RightHand),
    (BoneIndex.RightHandPinky2,  BoneIndex.RightHandPinky1),
    (BoneIndex.RightHandPinky3,  BoneIndex.RightHandPinky2),
    # 左手
    (BoneIndex.LeftHandThumb1,   BoneIndex.LeftHand),
    (BoneIndex.LeftHandThumb2,   BoneIndex.LeftHandThumb1),
    (BoneIndex.LeftHandThumb3,   BoneIndex.LeftHandThumb2),
    (BoneIndex.LeftHandIndex1,   BoneIndex.LeftHand),
    (BoneIndex.LeftHandIndex2,   BoneIndex.LeftHandIndex1),
    (BoneIndex.LeftHandIndex3,   BoneIndex.LeftHandIndex2),
    (BoneIndex.LeftHandMiddle1,  BoneIndex.LeftHand),
    (BoneIndex.LeftHandMiddle2,  BoneIndex.LeftHandMiddle1),
    (BoneIndex.LeftHandMiddle3,  BoneIndex.LeftHandMiddle2),
    (BoneIndex.LeftHandRing1,    BoneIndex.LeftHand),
    (BoneIndex.LeftHandRing2,    BoneIndex.LeftHandRing1),
    (BoneIndex.LeftHandRing3,    BoneIndex.LeftHandRing2),
    (BoneIndex.LeftHandPinky1,   BoneIndex.LeftHand),
    (BoneIndex.LeftHandPinky2,   BoneIndex.LeftHandPinky1),
    (BoneIndex.LeftHandPinky3,   BoneIndex.LeftHandPinky2),
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
    from PySide6.QtCore import QTimer, QEvent, Qt
    from PySide6.QtGui import QAction
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    from left_panel_widget import LeftPanelWidget

    class MotionGloveMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("MotionGlove 3D Viewer")
            self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

            self._quit_event = threading.Event()
            self._latest_frame: list[GloveFrame | None] = [None]
            self._frame_lock = threading.Lock()
            self._axes_visible = True
            self._ground_visible = False
            self._rb_press_pos = None   # 记录右键按下时的位置，用于判断是否发生了拖拽
            self._total_frames = 0       # 本次接收会话的累计帧数
            self._dropped_frames = 0     # 本次接收会话的累计丢失帧数
            self._last_frame_fn = None   # 上一次消费的帧序号（在 _poll 线程中更新）
            self._drop_event: tuple[int, int, int] | None = None  # (first_lost_fn, last_lost_fn, cumulative)
            self._fps_counter = FpsCounter()

            self._build_menu()
            self._build_central()
            self._build_status_bar()
            self._build_vtk_scene()
            self._start_sdk_poll()
            self._start_render_timer()

        # ── 菜单栏 ────────────────────────────────────────
        def _build_menu(self):
            menu_bar = self.menuBar()

            file_menu = menu_bar.addMenu("文件(&F)")
            exit_action = QAction("退出(&X)", self)
            exit_action.triggered.connect(QApplication.quit)
            file_menu.addAction(exit_action)

            help_menu = menu_bar.addMenu("帮助(&H)")
            about_qt_action = QAction("关于 Qt(&Q)", self)
            about_qt_action.triggered.connect(lambda: QMessageBox.aboutQt(self))
            help_menu.addAction(about_qt_action)

            oss_action = QAction("开源声明(&O)", self)
            oss_action.triggered.connect(self._show_oss_dialog)
            help_menu.addAction(oss_action)

        # ── 状态栏 ────────────────────────────────────────
        def _build_status_bar(self):
            self.statusBar().showMessage("就绪")

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

            # ── 左侧信息面板（从 ui/left_panel.ui 加载）──
            self._left_panel = LeftPanelWidget()
            self._left_panel.btn_start.clicked.connect(self._on_start_clicked)
            self._left_panel.btn_stop.clicked.connect(self._on_stop_clicked)
            h_layout.addWidget(self._left_panel)

            # ── VTK 视口 ──
            self._vtk_widget = QVTKRenderWindowInteractor(central)
            self._vtk_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._vtk_widget.installEventFilter(self)
            h_layout.addWidget(self._vtk_widget)

        # ── VTK 场景 ──────────────────────────────────────
        def _build_vtk_scene(self):
            self._renderer = vtk.vtkRenderer()
            self._renderer.SetBackground(0.10, 0.10, 0.16)

            render_window = self._vtk_widget.GetRenderWindow()
            render_window.AddRenderer(self._renderer)

            self._interactor = render_window.GetInteractor()
            self._interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

            # 32 个关节演员
            self._joint_actors = [
                BoneJointActor(self._renderer,
                               radius=_bone_radius(i),
                               sphere_color=_bone_color(i))
                for i in range(KHHS32_SKELETON_COUNT)
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

            self._axes_actor = add_axes_to_renderer(self._renderer, length=0.05)

            # 地平面网格（默认隐藏）
            self._ground_actor = build_ground_plane_actor(extent=0.30, spacing=0.05)
            self._ground_actor.SetVisibility(False)
            self._renderer.AddActor(self._ground_actor)

            _font_file = os.path.join(_SCRIPT_DIR, "fonts", "HarmonyOS_Sans_SC_Regular.ttf")
            if not os.path.isfile(_font_file):
                _font_file = None
            add_overlay_text(
                self._renderer,
                text="鼠标左键 旋转    鼠标右键 缩放    鼠标中键 平移    空格 重置视角",
                font_file=_font_file,
                font_size=15,
                color=(0.75, 0.75, 0.75),
                position=(0.5, 0.97),
                justification="center",
            )

            self._vtk_widget.Initialize()
            setup_camera(self._renderer, render_window)
            bind_space_reset_camera(self._interactor, self._renderer, render_window)

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
            self._left_panel.lbl_fps.setText(f"{self._fps_counter.fps()} fps")

        def _on_timer(self):
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
                positions: list = [None] * KHHS32_SKELETON_COUNT
                for i, skel in enumerate(frame.skeletons):
                    ja = self._joint_actors[i]
                    if skel.contains_position and skel.contains_quat_wxyz:
                        ja.set_pose(skel.position, skel.quat_wxyz)
                        positions[i] = skel.position
                    elif skel.contains_position:
                        ja.set_position_only(skel.position)
                        positions[i] = skel.position
                    else:
                        ja.hide()

                for la, (child, parent) in zip(self._link_actors, _BONE_LINKS):
                    pc = positions[child]
                    pp = positions[parent]
                    if pc is not None and pp is not None:
                        la.update(pp, pc)
                    else:
                        la.hide()

                self._vtk_widget.GetRenderWindow().Render()

            # 更新左侧网络信息面板
            addr = motionGloveSDK.MotionGloveSDK_GetLastRemoteAddr()
            if addr is not None:
                self._left_panel.lbl_ip.setText(addr[0])
                self._left_panel.lbl_port.setText(str(addr[1]))
            else:
                self._left_panel.lbl_ip.setText("等待中…")
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

            axes_label = "隐藏坐标轴" if self._axes_visible else "显示坐标轴"
            axes_action = menu.addAction(axes_label)

            ground_label = "隐藏地平面" if self._ground_visible else "显示地平面"
            ground_action = menu.addAction(ground_label)

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

        # ── 窗口关闭处理 ──────────────────────────────────
        def closeEvent(self, event):
            self._timer.stop()
            self._fps_timer.stop()
            self._quit_event.set()
            motionGloveSDK.MotionGloveSDK_CloseUDPPort()
            self._vtk_widget.GetRenderWindow().Finalize()
            self._interactor.TerminateApp()
            super().closeEvent(event)

        # ── UDP 接收控制 ──────────────────────────────────
        def _on_stop_clicked(self):
            motionGloveSDK.MotionGloveSDK_CloseUDPPort()
            self._fps_counter.reset()
            self._left_panel.set_receiving(False)
            self._left_panel.lbl_ip.setText("等待中…")
            self._left_panel.lbl_port.setText("—")
            self._left_panel.lbl_actor_name.setText("—")
            self._left_panel.lbl_frame_id.setText("—")
            self._left_panel.lbl_fps.setText("0 fps")

        def _on_start_clicked(self):
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
    window = MotionGloveMainWindow()
    window.show()
    return app, window


# ─────────────────────────────────────────────
#  入口
# ─────────────────────────────────────────────

def main():
    print(f"UDP Bind IP:port: 0.0.0.0:{RX_PORT}")
    nRet = motionGloveSDK.MotionGloveSDK_ListenUDPPort(RX_PORT)
    _port_error_lines: list[str] = []
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
