# /*******motionGloveSDK_example1*********/
# 用来测试MotionGloveSDK 的数据转发，默认使用UDP监听本地5001端口
# 使用流程：1、打开MotionGlove软件，并且手套连接正常
# 2、确保在软件菜单栏->设置->插件->数据转发中添加了127.0.0.1端口5001（软件默认已添加）
# 如果运行正常，会打印出收到数据帧的帧序号，每秒60帧
# /*******************************************/

import time
import threading
import motionGloveSDK

# 绑定本机的5001端口 开始读取数据
# 端口号要与MotionGlove中 设置->选项->插件->数据转发 中的端口号一致
rxPortDefault = 5001

print(f"UDP Bind IP:port: 127.0.0.1:{rxPortDefault}")
nRet = motionGloveSDK.MotionGloveSDK_ListenUDPPort(rxPortDefault)

if nRet == -1:
    print(f"Error code {nRet}, any key to exit.")
    input()
else:
    print(f"[UDP]Bind port {rxPortDefault} success. Start Reading Data...")

gloveName    = "Glove1"
frameCounter = 0

# 用独立线程等待 Enter，避免阻塞主循环
_quit = threading.Event()
threading.Thread(target=lambda: (input(), _quit.set()), daemon=True).start()
print("按 Enter 键退出程序")

while not _quit.is_set():
    # 接收到的数据包为60Hz
    if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending(gloveName):
        print(f"[{frameCounter}]New frame received")
        frameCounter += 1
        motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending(gloveName)

    time.sleep(0.01)  # 10ms，对应 C++ Sleep(10) / usleep(10000)

motionGloveSDK.MotionGloveSDK_CloseUDPPort()
print("程序退出。")
