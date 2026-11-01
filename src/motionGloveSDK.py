"""
@file  motionGloveSDK.py
@brief MotionGloveSDK Python 对外公共接口（函数名与 C++ motionGloveSDK.h 一致）。
@details
═══════════════════════════════════════════════════════════════════════════
  数据流解析已全部交给 C++ 库（third_party/MotionGloveSDK_cpp）完成：
  UDP 接收、分包重组、CSV 解析、帧缓存都在 MotionGloveSDK.dll / .so 内部，
  Python 侧只通过 src/native 转接层（ctypes）取回已解析好的帧。
  Python 不再解析任何数据流——C++ 工程改动时只需要维护 src/native。
═══════════════════════════════════════════════════════════════════════════

C++ 接口 → Python 接口对照表：
  MotionGloveSDK_getVersion()                 → MotionGloveSDK_getVersion()
  MotionGloveSDK_ListenUDPPort(nPort)         → MotionGloveSDK_ListenUDPPort(nPort)
  MotionGloveSDK_CloseUDPPort()               → MotionGloveSDK_CloseUDPPort()
  MotionGloveSDK_isGloveNewFramePending(name) → MotionGloveSDK_isGloveNewFramePending(name)
  MotionGloveSDK_resetGloveNewFramePending()  → MotionGloveSDK_resetGloveNewFramePending(name)
  MotionGloveSDK_GetSkeletonsFrameType()      → MotionGloveSDK_GetSkeletonsFrameType(name)
  MotionGloveSDK_GetSkeletons42Frame()        ┐
  MotionGloveSDK_GetSkeletons32Frame()        ┴→ MotionGloveSDK_GetGloveSkeletonsFrame(name)

  Python 额外提供的便捷接口（C++ 侧没有对应函数）：
  MotionGloveSDK_GetActorNames()        已确认存在的数据流名称
  MotionGloveSDK_GetLastRemoteAddr()    最近取回的帧的发送方地址
  MotionGloveSDK_GetBackendName()       当前后端（固定为 "native"）
  MotionGloveSDK_GetNativeLibraryPath() 已加载的原生库路径

使用方式：
  from src import motionGloveSDK

  motionGloveSDK.MotionGloveSDK_ListenUDPPort(5001)

  while True:
      if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending("Glove1"):
          frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame("Glove1")
          motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending("Glove1")

名称约束：所有含 actorName 参数的接口在进入后端前先经 _is_valid_actor_name()
校验（UTF-8 字节数 ≤ 63，即 C++ 缓冲区 ACTOR_NAME_LEN_MAX 含结尾 NUL），
无效名称直接短路返回，不触碰原生库。
"""

from __future__ import annotations

from . import native
from .definitions import ACTOR_NAME_LEN_MAX, GloveFrame
from .native import MotionGloveNativeError
from .port_occupier import print_udp_port_occupier

__all__ = [
    "MotionGloveNativeError",
    "MotionGloveSDK_CloseUDPPort",
    "MotionGloveSDK_GetActorNames",
    "MotionGloveSDK_GetBackendName",
    "MotionGloveSDK_GetGloveSkeletonsFrame",
    "MotionGloveSDK_GetLastRemoteAddr",
    "MotionGloveSDK_GetNativeLibraryPath",
    "MotionGloveSDK_GetSkeletonsFrameType",
    "MotionGloveSDK_IsAvailable",
    "MotionGloveSDK_ListenUDPPort",
    "MotionGloveSDK_getVersion",
    "MotionGloveSDK_isGloveNewFramePending",
    "MotionGloveSDK_resetGloveNewFramePending",
]

# 名称长度校验：C++ 侧缓冲区 ACTOR_NAME_LEN_MAX 含结尾 NUL，有效长度 ≤ 63 字节
_MAX_ACTOR_NAME_BYTES = ACTOR_NAME_LEN_MAX - 1


def _is_valid_actor_name(actorName: str) -> bool:
    """@brief 校验数据流名称是否为合法的 UTF-8 字节长度。

    @details C++ 侧缓冲区 ACTOR_NAME_LEN_MAX 含结尾 NUL，有效长度 ≤ 63 字节；
             按 UTF-8 字节数（非字符数）判断，中英文名同样适用。
    @param actorName 待校验的数据流名称（Python str）。
    @return True 长度为 1~63 字节；False 为空或超过 63 字节。
    """
    if not actorName:
        return False
    return len(actorName.encode("utf-8", errors="replace")) <= _MAX_ACTOR_NAME_BYTES


def _safe_print(message: str) -> None:
    """@brief 打印中文诊断信息，控制台编码不支持时降级为 ASCII。

    @details 保证打印失败不会破坏接口的返回值约定。
    @param message 要输出的诊断文本。
    @return 无（None）。
    """
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode("ascii"))


# ---------------------------------------------------------------------------
# 后端信息
# ---------------------------------------------------------------------------

def MotionGloveSDK_IsAvailable() -> bool:
    """@brief 原生库是否可用（不会抛异常）。

    @return True 原生库已能加载；False 缺库 / ABI 不匹配。
    """
    return native.is_available()


def MotionGloveSDK_GetBackendName() -> str:
    """@brief 当前数据流后端名称。

    @return 字符串，固定为 "native"。
    """
    return native.backend_name()


def MotionGloveSDK_GetNativeLibraryPath() -> str | None:
    """@brief 已加载的原生库绝对路径。

    @return 库文件绝对路径（首次调用会触发加载）；原生库不可用时抛
            MotionGloveNativeError；尚未加载且不可用返回 None。
    """
    return native.library_path()


def MotionGloveSDK_getVersion() -> int:
    """@brief 返回原生 SDK 版本号。

    @return 32 位整数，编码为 (mainVersion << 16) | (subVersion << 8) | patchVersion。
    """
    return native.get_backend().version()


# ---------------------------------------------------------------------------
# UDP 生命周期
# ---------------------------------------------------------------------------

def MotionGloveSDK_ListenUDPPort(nPort: int = 5001) -> int:
    """@brief 绑定本机 UDP 端口并在 C++ 侧启动后台接收线程。

    @details 对应 C++ MotionGloveSDK_ListenUDPPort()。绑定失败时会尝试
             打印占用该端口的进程信息（print_udp_port_occupier）。
    @param nPort 端口号，1024~65535，默认 5001。
    @return 0 成功；-1 失败（端口被占用、原生库不可用等）。
    """
    try:
        backend = native.get_backend()
    except MotionGloveNativeError as exc:
        _safe_print(f"[MotionGloveSDK] 原生库不可用，无法监听端口 {nPort}：\n{exc}")
        return -1

    ret = backend.listen(nPort)
    if ret != 0:
        _safe_print(f"[MotionGloveSDK] 绑定端口 {nPort} 失败")
        try:
            print_udp_port_occupier(nPort)
        except UnicodeEncodeError:
            pass
    return ret


def MotionGloveSDK_CloseUDPPort() -> int:
    """@brief 关闭 UDP 连接并等待 C++ 接收线程退出。

    @details 对应 C++ MotionGloveSDK_CloseUDPPort()。
    @return 0 成功；-1 失败（未处于打开状态或原生库不可用）。
    """
    try:
        backend = native.get_backend()
    except MotionGloveNativeError:
        return -1
    return backend.close()


# ---------------------------------------------------------------------------
# 帧轮询
# ---------------------------------------------------------------------------

def MotionGloveSDK_isGloveNewFramePending(actorName: str) -> bool:
    """@brief 查询指定数据流是否有新帧到达。

    @details 对应 C++ MotionGloveSDK_isGloveNewFramePending()；名称无效时
             短路返回 False，不触碰原生库。
    @param actorName 数据流名称（UTF-8 ≤ 63 字节），例如 "Glove1"。
    @return True 有新帧；False 无新帧或名称无效。
    """
    if not _is_valid_actor_name(actorName):
        return False
    return native.get_backend().is_pending(actorName)


def MotionGloveSDK_resetGloveNewFramePending(actorName: str) -> bool:
    """@brief 清除指定数据流的新帧标志。

    @details 对应 C++ MotionGloveSDK_resetGloveNewFramePending()；名称无效时
             短路返回 False。
    @param actorName 数据流名称（UTF-8 ≤ 63 字节）。
    @return True 清除成功；False 名称无效或未找到。
    """
    if not _is_valid_actor_name(actorName):
        return False
    return native.get_backend().reset_pending(actorName)


def MotionGloveSDK_GetSkeletonsFrameType(actorName: str) -> int | None:
    """@brief 查询指定数据流缓存帧的骨骼格式。

    @details 对应 C++ MotionGloveSDK_GetSkeletonsFrameType()。
    @param actorName 数据流名称（UTF-8 ≤ 63 字节）。
    @return native.abi.SkeletonFormat.SKELETON_32 / SKELETON_42 / OPENXR；
            None 名称无效、数据流未知或该版本库不提供此接口。
    """
    if not _is_valid_actor_name(actorName):
        return None
    return native.get_backend().get_frame_format(actorName)


def MotionGloveSDK_GetGloveSkeletonsFrame(actorName: str) -> GloveFrame | None:
    """@brief 获取指定数据流最新一帧的骨骼数据（32/42 段自动分派）。

    @details 对应 C++ MotionGloveSDK_GetSkeletons42Frame() /
             GetSkeletons32Frame()。frame.skeletons 的长度与数据流格式
             一致（32 或 42），bone_index 统一为 42 段索引，与旧版
             Python 解析结果保持一致。
    @param actorName 数据流名称（UTF-8 ≤ 63 字节）。
    @return GloveFrame 对象（成功）；None 名称无效、数据流未知或数据尚未到达。
    """
    if not _is_valid_actor_name(actorName):
        return None
    return native.get_backend().get_frame(actorName)


# ---------------------------------------------------------------------------
# Python 额外接口
# ---------------------------------------------------------------------------

def MotionGloveSDK_GetLastRemoteAddr() -> tuple[str, int] | None:
    """@brief 返回最近一次成功取回的帧的发送方地址。

    @return (ip_str, port_int) 至少取回过一帧时；None 尚未取到任何帧。
    """
    return native.get_backend().get_last_remote_addr()


def MotionGloveSDK_GetActorNames() -> list[str]:
    """@brief 返回当前已确认存在的数据流名称列表。

    @details C++ SDK 没有枚举数据流的接口，因此这里收集的是「查询到有
             新帧」以及「成功取到帧」的数据流名称，按首次发现顺序排列。
    @return list[str] 数据流名称列表；尚未发现任何数据流时为空列表。
    """
    return native.get_backend().get_actor_names()
