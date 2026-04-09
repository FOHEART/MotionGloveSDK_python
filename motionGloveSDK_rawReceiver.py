"""
UDP Raw Data Receiver - MotionGloveSDK Python
验证能否收到来自 MotionGlove 软件的原始 UDP 数据

使用方法：
  python udp_raw_receiver.py
  python udp_raw_receiver.py --port 5001

对应 C++ 实现：MotionGloveSDK/src/motionGloveSDK.cpp - ThreadProc()

默认监听 127.0.0.1:5001（与 C++ 示例一致）
MotionGlove 软件设置：菜单栏 -> 设置 -> 插件 -> 数据转发 -> 127.0.0.1:5001
"""

import socket
import threading
import argparse
from src.glove_frame_assembler import GloveFrameAssembler
from src.decode_glove_csv import decode_glove_csv
from src.definitions import BoneIndex
from src.port_occupier import print_udp_port_occupier

# 接收缓冲区大小，与 C++ maxFrameLen 保持一致
MAX_FRAME_LEN = 32 * 1024  # 32 KB
UDP_PORT_DEFAULT = 5001


class UDPRawReceiver:
    """
    后台线程 UDP 接收器，打印原始数据帧信息。
    对应 C++ ThreadProc() 的核心接收逻辑（不含解码）。
    """
  
    def __init__(self, port: int = UDP_PORT_DEFAULT, print_raw: bool = False):
        self._port = port
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._print_raw = print_raw  # True: 打印每个原始 UDP 包；False: 静默

        self._udp_packet_count = 0
        self._dropped_frames = 0
        self._lock = threading.Lock()
        self._assembler = GloveFrameAssembler(on_complete_frame=self._on_complete_frame)
        self._last_fn: int | None = None  # 上一个完整帧的帧序号

    def start(self) -> int:
        """
        绑定端口并启动后台接收线程。
        返回 0 表示成功，-1 表示失败（对应 C++ MotionGloveSDK_ListenUDPPort 返回值）
        """
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 接收缓冲区设为 32KB，与 C++ setsockopt SO_RCVBUF 一致
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 32 * 1024)
            self._sock.bind(("0.0.0.0", self._port))
        except OSError as e:
            print(f"[错误] 绑定端口 {self._port} 失败: {e}")
            print_udp_port_occupier(self._port)
            if self._sock:
                self._sock.close()
                self._sock = None
            return -1

        self._running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True, name="udp-recv")
        self._thread.start()
        return 0

    def stop(self):
        """
        关闭 socket 并等待后台线程结束。
        对应 C++ MotionGloveSDK_CloseUDPPort()
        """
        self._running = False
        if self._sock:
            self._sock.close()
            self._sock = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _recv_loop(self):
        """
        后台接收线程主循环。
        对应 C++ ThreadProc() 中的 while(1) recvfrom 循环。
        """
        print(f"[线程] 后台接收线程已启动，监听端口 {self._port}")

        while self._running:
            if self._sock is None:
                break
            try:
                data, addr = self._sock.recvfrom(MAX_FRAME_LEN)
            except OSError:
                # socket 被 stop() 关闭时会触发此异常，正常退出
                break

            remote_ip, remote_port = addr
            frame_len = len(data)

            with self._lock:
                self._udp_packet_count += 1
                count = self._udp_packet_count

            # 尝试将数据解码为字符串（CSV 格式为可打印文本）
            try:
                text = data.decode("utf-8", errors="replace")
                # 只取第一行（header 行）用于展示
                first_line = text.split(",")[0].strip()
                is_text = True
            except Exception:
                text = None
                first_line = "<binary>"
                is_text = False

            if self._print_raw:
                print(
                    f"[UDP包 {count:>6d}] "
                    f"来源: {remote_ip}:{remote_port}  "
                    f"长度: {frame_len:>6d} 字节  "
                    f"{'文本' if is_text else '二进制'}  "
                    f"内容头: {first_line[:80]}"
                )

            if text is not None:
                self._assembler.feed(text)

        print("[线程] 后台接收线程已退出")

    def _check_fn_continuity(self, fn: int) -> None:
        """检查帧序号是否连续，不连续时打印丢失帧范围。"""
        if self._last_fn is None:
            self._last_fn = fn
            return
        expected = self._last_fn + 1
        if fn != expected:
            lost = fn - expected
            if lost > 0:
                print(
                    f"  [警告] 帧序号不连续：期望 {expected}，收到 {fn}"
                    f"  丢失 {lost} 帧（fn {expected} ~ {fn - 1}）"
                )
                self._dropped_frames += lost
            else:
                # fn 回绕或乱序（罕见）
                print(f"  [警告] 帧序号回绕或乱序：期望 {expected}，收到 {fn}")
        self._last_fn = fn

    def _on_complete_frame(self, actor: str, fn: int, body_csv: str, header_tokens: list):
        """由 GloveFrameAssembler 在完整帧拼接完成后回调，调用 decode_glove_csv 解析数据。"""
        self._check_fn_continuity(fn)
        complete = self._assembler.complete_frame_count

        frame = decode_glove_csv(actor, fn, body_csv, header_tokens)
        if frame is None:
            print(f"  -> [完整帧 {complete:>6d}]  actor: {actor}  fn: {fn}  [解析失败]")
            return

        hdr  = frame.header
        rh   = frame.skeletons[BoneIndex.RightHand]
        lh   = frame.skeletons[BoneIndex.LeftHand]

        lh_euler_str = f"  euler={[f'{v:.1f}' for v in lh.euler_degree]}" if lh.contains_euler_degree else ""
        lh_quat_str  = f"  quat={[f'{v:.3f}' for v in lh.quat_wxyz]}"    if lh.contains_quat_wxyz   else ""
        lh_pos_str   = f"  pos={[f'{v:.3f}' for v in lh.position]}"       if lh.contains_position    else ""

        rh_euler_str = f"  euler={[f'{v:.1f}' for v in rh.euler_degree]}" if rh.contains_euler_degree else ""
        rh_quat_str  = f"  quat={[f'{v:.3f}' for v in rh.quat_wxyz]}"    if rh.contains_quat_wxyz   else ""
        rh_pos_str   = f"  pos={[f'{v:.3f}' for v in rh.position]}"       if rh.contains_position    else ""

        print(
            f"  -> [完整帧 {complete:>6d}]  actor: {actor}  fn: {fn}"
            #f"  pos={hdr.skeleton_position.name}"
            #f"  att={hdr.skeleton_attitude.name}"
            #f"  order={hdr.channel_order.name}"
            #f"  gesture L/R={hdr.left_hand_gesture.value}/{hdr.right_hand_gesture.value}"
            #f"\n       {rh.bone_name}{rh_pos_str}{rh_euler_str}{rh_quat_str}"
           # f"  quat={[f'{v:.3f}' for v in rh.quat_wxyz]}"
            #f"\n       {lh.bone_name}{lh_pos_str}{lh_euler_str}{lh_quat_str}"
        )


def main():
    """
    程序入口，解析命令行参数并启动 UDP 接收器。

    命令行参数：
      --port <int>    监听的 UDP 端口号，默认 5001
                      示例：python udp_raw_receiver.py --port 5002

      --print-raw     开启原始 UDP 包打印（默认关闭，只打印完整帧）
                      示例：python udp_raw_receiver.py --print-raw

    组合示例：
      python udp_raw_receiver.py --port 5001 --print-raw
    """
    parser = argparse.ArgumentParser(
        description="MotionGloveSDK - UDP 原始数据接收验证工具"
    )
    parser.add_argument(
        "--port", type=int, default=UDP_PORT_DEFAULT,
        help=f"监听的 UDP 端口号（默认 {UDP_PORT_DEFAULT}）",
    )
    parser.add_argument(
        "--print-raw", action="store_true",
        help="打印每个原始 UDP 包信息（默认关闭）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("MotionGloveSDK Python - UDP 原始数据接收验证")
    print("=" * 60)
    print(f"监听地址 : 0.0.0.0:{args.port}")
    print("停止方法 : 按 Enter 键 或 Ctrl+C")
    print()
    print("请确认 MotionGlove 软件已启动并开启数据转发：")
    print(f"  菜单栏 -> 设置 -> 插件 -> 数据转发 -> 127.0.0.1:{args.port}")
    print("=" * 60)
    print()

    receiver = UDPRawReceiver(port=args.port, print_raw=args.print_raw)
    ret = receiver.start()
    if ret != 0:
        print("启动失败，程序退出。")
        return

    print(f"[成功] 端口 {args.port} 绑定成功，等待数据...")
    print("按 Enter 键退出程序")
    print()

    try:
        input()
    except KeyboardInterrupt:
        print()

    print("[停止] 正在关闭...")

    receiver.stop()

    print(f"\n[统计] 收到 UDP 包: {receiver._udp_packet_count}  完整帧: {receiver._assembler.complete_frame_count}  丢失帧: {receiver._dropped_frames}")
    print("程序退出。")


if __name__ == "__main__":
    main()
