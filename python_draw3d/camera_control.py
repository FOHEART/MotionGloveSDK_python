"""相机控制工具：键盘事件绑定"""


def setup_camera(renderer, render_window,
                 position=(0.0, 0.0, 0.4),
                 focal_point=(0.0, 0.08, 0.0),
                 view_up=(0.0, 1.0, 0.0)):
    """
    设置相机初始位置。
    默认视角：Z 轴正方向朝向屏幕外，Y 轴向上。
    需在 render_window.Render() 之后、bind_space_reset_camera() 之前调用。
    """
    cam = renderer.GetActiveCamera()
    cam.SetPosition(*position)
    cam.SetFocalPoint(*focal_point)
    cam.SetViewUp(*view_up)
    renderer.ResetCameraClippingRange()
    render_window.Render()


class SpaceResetCameraCallback:
    """按下空格键时重置相机到初始状态"""

    def __init__(self, renderer, render_window, initial_camera_state):
        self.renderer = renderer
        self.render_window = render_window
        self.initial_state = initial_camera_state  # dict，记录初始相机参数

    def reset(self):
        cam = self.renderer.GetActiveCamera()
        s = self.initial_state
        cam.SetPosition(*s["position"])
        cam.SetFocalPoint(*s["focal_point"])
        cam.SetViewUp(*s["view_up"])
        cam.SetViewAngle(s["view_angle"])
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        print("  [相机] 已重置视角")

    def __call__(self, obj, event):
        if event != "KeyPressEvent":
            return
        if obj.GetKeySym() != "space":
            return
        self.reset()


def bind_space_reset_camera(interactor, renderer, render_window):
    """记录当前相机状态，并将空格键重置绑定到 interactor。
    需在 render_window.Render() + renderer.ResetCamera() 之后调用，
    以捕获正确的初始视角。
    """
    cam = renderer.GetActiveCamera()
    initial_state = {
        "position":    cam.GetPosition(),
        "focal_point": cam.GetFocalPoint(),
        "view_up":     cam.GetViewUp(),
        "view_angle":  cam.GetViewAngle(),
    }
    cb = SpaceResetCameraCallback(renderer, render_window, initial_state)
    interactor.AddObserver("KeyPressEvent", cb, 1.0)
    return cb
