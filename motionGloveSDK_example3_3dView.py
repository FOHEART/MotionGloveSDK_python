# /*******motionGloveSDK_example3_3dView*********/
# 将左右手所有骨骼的位置数据 实时显示为3D场景中的小球
# 每个关节叠加三坐标轴线段表示旋转姿态
# 每帧动态更新球体位置和坐标轴方向
# /*******************************************/

import sys
import os
import threading
import time

# ── 路径：libs/ 和 python_draw3d/ 均在当前目录 ──
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_LIBS_DIR   = os.path.join(_SCRIPT_DIR, "libs")
_DRAW3D_DIR = os.path.join(_SCRIPT_DIR, "python_draw3d")
sys.path.insert(0, _DRAW3D_DIR)
sys.path.insert(0, _LIBS_DIR)

import vtk
from vtk_axes import add_axes_to_renderer
from camera_control import bind_space_reset_camera, setup_camera
from bone_joint_actor import BoneJointActor
from overlay_text import add_overlay_text

from src import motionGloveSDK
from src.definitions import BoneIndex, KHHS32_SKELETON_COUNT, GloveFrame

# ─────────────────────────────────────────────
#  配置
# ─────────────────────────────────────────────

RX_PORT      = 5001
GLOVE_NAME   = "Glove1"
WINDOW_WIDTH  = 1366
WINDOW_HEIGHT = 768

SPHERE_RADIUS_PALM   = 0.005   # 手掌根节球体半径
SPHERE_RADIUS_FINGER = 0.005   # 手指关节球体半径

COLOR_RIGHT = (0.3, 0.8, 1.0)   # 右手：青蓝
COLOR_LEFT  = (1.0, 0.5, 0.2)   # 左手：橙

# CI/无界面环境下用于自动化冒烟测试：渲染一帧后退出
_CI_MODE = os.environ.get("MOTIONGLOVE_CI", "").strip().lower() in ("1", "true", "yes") or \
           os.environ.get("CI", "").strip().lower() in ("1", "true", "yes")
_CI_RENDER_SECONDS = float(os.environ.get("MOTIONGLOVE_CI_SECONDS", "0.5"))

# ─────────────────────────────────────────────


def _bone_radius(bone_idx):
    if bone_idx in (BoneIndex.RightHand, BoneIndex.LeftHand):
        return SPHERE_RADIUS_PALM
    return SPHERE_RADIUS_FINGER


def _bone_color(bone_idx):
    return COLOR_RIGHT if bone_idx < BoneIndex.LeftHand else COLOR_LEFT


def main():
    # ── 初始化 SDK ──
    print(f"UDP Bind IP:port: 127.0.0.1:{RX_PORT}")
    nRet = motionGloveSDK.MotionGloveSDK_ListenUDPPort(RX_PORT)
    if nRet == -1:
        print(f"端口 {RX_PORT} 绑定失败，按 Enter 退出。")
        input()
        return
    print(f"[UDP] 端口 {RX_PORT} 绑定成功，开始接收数据...")

    # ── 构建渲染场景 ──
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.10, 0.10, 0.16)

    # 为 32 个骨骼各创建一个 BoneJointActor
    joint_actors = [
        BoneJointActor(renderer,
                       radius=_bone_radius(i),
                       sphere_color=_bone_color(i))
        for i in range(KHHS32_SKELETON_COUNT)
    ]

    add_axes_to_renderer(renderer, length=0.05)

    # ── 界面操作提示文字 ──
    _font_file = os.path.join(_SCRIPT_DIR, "fonts", "HarmonyOS_Sans_SC_Regular.ttf")
    if not os.path.isfile(_font_file):
        _font_file = None
    add_overlay_text(
        renderer,
        text="鼠标左键 旋转    鼠标右键 缩放    鼠标中键 平移    空格 重置视角",
        font_file=_font_file,
        font_size=15,
        color=(0.75, 0.75, 0.75),
        position=(0.5, 0.97),
        justification="center",
    )

    # ── 窗口与交互 ──
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    render_window.SetWindowName(
        "MotionGlove 3D Viewer"
    )
    if _CI_MODE:
        render_window.SetOffScreenRendering(1)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

    render_window.Render()

    setup_camera(renderer, render_window)
    bind_space_reset_camera(interactor, renderer, render_window)

    if _CI_MODE:
        try:
            interactor.Initialize()
            render_window.Render()
            time.sleep(max(0.0, _CI_RENDER_SECONDS))
            render_window.Render()
            print("[CI] Offscreen render smoke test passed.")
        finally:
            motionGloveSDK.MotionGloveSDK_CloseUDPPort()
        return

    # ── 用于线程间传递最新帧的容器 ──
    _latest_frame: list[GloveFrame | None] = [None]
    _lock = threading.Lock()

    # ── 后台线程：持续轮询 SDK 新帧 ──
    _quit = threading.Event()

    def _sdk_poll():
        while not _quit.is_set():
            if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending(GLOVE_NAME):
                frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame(GLOVE_NAME)
                motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending(GLOVE_NAME)
                if frame is not None:
                    with _lock:
                        _latest_frame[0] = frame
            time.sleep(0.002)

    threading.Thread(target=_sdk_poll, daemon=True).start()

    # ── Enter 键退出线程 ──
    threading.Thread(
        target=lambda: (input("按 Enter 键退出程序\n"), _quit.set()),
        daemon=True,
    ).start()

    # ── 定时器回调：更新各关节姿态并重绘 ──
    def _on_timer(*_):
        with _lock:
            frame = _latest_frame[0]
        if frame is None:
            return

        for i, skel in enumerate(frame.skeletons):
            ja = joint_actors[i]
            if skel.contains_position and skel.contains_quat_wxyz:
                ja.set_pose(skel.position, skel.quat_wxyz)
            elif skel.contains_position:
                ja.set_position_only(skel.position)
            else:
                ja.hide()

        render_window.Render()

        if _quit.is_set():
            interactor.GetRenderWindow().Finalize()
            interactor.TerminateApp()

    interactor.AddObserver("TimerEvent", _on_timer)
    interactor.Initialize()
    interactor.CreateRepeatingTimer(16)   # ~60fps

    interactor.Start()

    # ── 清理 ──
    _quit.set()
    motionGloveSDK.MotionGloveSDK_CloseUDPPort()
    print("程序退出。")


if __name__ == "__main__":
    main()
