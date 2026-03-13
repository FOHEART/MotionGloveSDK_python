"""
motionGloveSDK.py - MotionGloveSDK Python
对外公共接口，与 motionGloveSDK.h 中的 C++ 接口名称和语义完全对应

C++ 接口 → Python 接口对照表：
  MotionGloveSDK_getVersion()              → MotionGloveSDK_getVersion()
  MotionGloveSDK_ListenUDPPort(nPort)      → MotionGloveSDK_ListenUDPPort(nPort)
  MotionGloveSDK_CloseUDPPort()            → MotionGloveSDK_CloseUDPPort()
  MotionGloveSDK_isGloveNewFramePending()  → MotionGloveSDK_isGloveNewFramePending()
  MotionGloveSDK_resetGloveNewFramePending()→ MotionGloveSDK_resetGloveNewFramePending()
  MotionGloveSDK_GetGloveSkeletonsFrame()  → MotionGloveSDK_GetGloveSkeletonsFrame()

使用方式：
  import motionGloveSDK

  motionGloveSDK.MotionGloveSDK_ListenUDPPort(5001)

  while True:
      if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending("Glove1"):
          frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame("Glove1")
          motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending("Glove1")
"""

import threading
import socket
from src.definitions import (
    GloveFrame,
    ACTOR_NAME_LEN_MAX,
)
from src.glove_frame_assembler import GloveFrameAssembler
from src.decode_glove_csv import decode_glove_csv
from src.port_occupier import print_udp_port_occupier

# ---------------------------------------------------------------------------
# SDK 版本，对应 C++ MotionGloveSDK_getVersion() 中的 mainVersion/subVersion/patchVersion
# ---------------------------------------------------------------------------
_MAIN_VERSION  = 0
_SUB_VERSION   = 0
_PATCH_VERSION = 9

# ---------------------------------------------------------------------------
# 内部全局状态
# ---------------------------------------------------------------------------

# SDK 状态枚举（对应 C++ SDK_Status_TypeDef）
_STATUS_NONE           = 0
_STATUS_OPEN_UDP       = 1
_STATUS_THREAD_RUNNING = 2

_sdk_status: int = _STATUS_NONE
_sock: socket.socket | None = None
_recv_thread: threading.Thread | None = None

# Actor 数据存储：{actor_name: {"frame": GloveFrame | None, "pending": bool}}
_SUIT_MGR_MAXLEN = 32
_actor_store: dict[str, dict] = {}
_store_lock = threading.RLock()

_MAX_FRAME_LEN = 32 * 1024
_assembler: GloveFrameAssembler | None = None


# ---------------------------------------------------------------------------
# 内部：后台接收线程
# ---------------------------------------------------------------------------

def _recv_loop() -> None:
    global _sock, _sdk_status

    while True:
        if _sock is None:
            break
        try:
            data, addr = _sock.recvfrom(_MAX_FRAME_LEN)
        except OSError:
            break

        try:
            text = data.decode("utf-8", errors="replace")
        except Exception:
            continue

        if _assembler is not None:
            _assembler.feed(text)


def _on_complete_frame(actor: str, fn: int, body_csv: str, header_tokens: list) -> None:
    """分包拼接完成后由 GloveFrameAssembler 回调，解析并存入 _actor_store。"""
    frame = decode_glove_csv(actor, fn, body_csv, header_tokens)
    if frame is None:
        return

    with _store_lock:
        if actor not in _actor_store:
            if len(_actor_store) >= _SUIT_MGR_MAXLEN:
                return
            _actor_store[actor] = {"frame": None, "pending": False}
        _actor_store[actor]["frame"]   = frame
        _actor_store[actor]["pending"] = True


# ---------------------------------------------------------------------------
# 公共接口（与 motionGloveSDK.h 接口名称完全一致）
# ---------------------------------------------------------------------------

def MotionGloveSDK_getVersion() -> int:
    """
    返回 SDK 版本号（32 位整数）。
    对应 C++ MotionGloveSDK_getVersion()。
    版本编码：(mainVersion << 16) | (subVersion << 8) | patchVersion
    """
    return (_MAIN_VERSION << 16) | (_SUB_VERSION << 8) | _PATCH_VERSION


def MotionGloveSDK_ListenUDPPort(nPort: int = 5001) -> int:
    """
    绑定本机 UDP 端口并启动后台接收线程。
    对应 C++ MotionGloveSDK_ListenUDPPort()。

    参数：
      nPort : 端口号（1024~65535），默认 5001

    返回：
      0  成功
     -1  失败（端口被占用等）
    """
    global _sdk_status, _sock, _recv_thread, _assembler

    if _sdk_status == _STATUS_THREAD_RUNNING:
        return 0

    _assembler = GloveFrameAssembler(on_complete_frame=_on_complete_frame)

    try:
        _sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32 * 1024)
        _sock.bind(("0.0.0.0", nPort))
    except OSError as e:
        print(f"[MotionGloveSDK] 绑定端口 {nPort} 失败: {e}")
        print_udp_port_occupier(nPort)
        if _sock:
            _sock.close()
            _sock = None
        return -1

    _sdk_status = _STATUS_OPEN_UDP

    _recv_thread = threading.Thread(target=_recv_loop, daemon=True, name="mgsdk-recv")
    _recv_thread.start()
    _sdk_status = _STATUS_THREAD_RUNNING

    return 0


def MotionGloveSDK_CloseUDPPort() -> int:
    """
    关闭 UDP 连接并等待后台线程退出。
    对应 C++ MotionGloveSDK_CloseUDPPort()。

    返回：
      0  成功
     -1  失败（未处于打开状态）
    """
    global _sdk_status, _sock, _recv_thread

    if _sdk_status not in (_STATUS_OPEN_UDP, _STATUS_THREAD_RUNNING):
        return -1

    if _sock is not None:
        _sock.close()
        _sock = None

    if _recv_thread is not None and _recv_thread.is_alive():
        _recv_thread.join(timeout=2.0)
        _recv_thread = None

    _sdk_status = _STATUS_NONE
    return 0


def MotionGloveSDK_isGloveNewFramePending(actorName: str) -> bool:
    """
    查询指定数据流是否有新帧到达。
    对应 C++ MotionGloveSDK_isGloveNewFramePending()。

    参数：
      actorName : 数据流名称（最大 64 字节），例如 "Glove1"

    返回：
      True  有新帧
      False 无新帧或名称无效
    """
    if not actorName or len(actorName) > ACTOR_NAME_LEN_MAX:
        return False

    with _store_lock:
        entry = _actor_store.get(actorName)
        if entry is None:
            return False
        return entry["pending"]


def MotionGloveSDK_resetGloveNewFramePending(actorName: str) -> bool:
    """
    清除指定数据流的新帧标志。
    对应 C++ MotionGloveSDK_resetGloveNewFramePending()。

    参数：
      actorName : 数据流名称

    返回：
      True  清除成功
      False 名称无效或未找到
    """
    if not actorName or len(actorName) > ACTOR_NAME_LEN_MAX:
        return False

    with _store_lock:
        entry = _actor_store.get(actorName)
        if entry is None:
            return False
        entry["pending"] = False
        return True


def MotionGloveSDK_GetGloveSkeletonsFrame(actorName: str) -> GloveFrame | None:
    """
    获取指定数据流最新一帧的骨骼数据。
    对应 C++ MotionGloveSDK_GetGloveSkeletonsFrame()。

    参数：
      actorName : 数据流名称

    返回：
      GloveFrame 对象（成功）
      None       名称无效或数据尚未到达
    """
    if not actorName or len(actorName) > ACTOR_NAME_LEN_MAX:
        return None

    with _store_lock:
        entry = _actor_store.get(actorName)
        if entry is None:
            return None
        return entry["frame"]
