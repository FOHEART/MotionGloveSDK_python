# /*******motionGloveSDK_example2*********/
# 本程序用来测试左右手手掌的角度
# /*******************************************/

import time
import threading
import motionGloveSDK
from src.definitions import BoneIndex

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

gloveName = "Glove1"

# 用独立线程等待 Enter，避免阻塞主循环
_quit = threading.Event()
threading.Thread(target=lambda: (input(), _quit.set()), daemon=True).start()
print("按 Enter 键退出程序")

while not _quit.is_set():
    # 接收到的数据包为60Hz
    if motionGloveSDK.MotionGloveSDK_isGloveNewFramePending(gloveName):

        frame = motionGloveSDK.MotionGloveSDK_GetGloveSkeletonsFrame(gloveName)
        if frame is not None:
            leftPalm  = frame.skeletons[BoneIndex.LeftHand]
            rightPalm = frame.skeletons[BoneIndex.RightHand]
            print(
                f" Left Palm Euler Angle: [{leftPalm.euler_degree[0]:.2f}, {leftPalm.euler_degree[1]:.2f}, {leftPalm.euler_degree[2]:.2f}]  "
                f" Right Palm Euler Angle: [{rightPalm.euler_degree[0]:.2f}, {rightPalm.euler_degree[1]:.2f}, {rightPalm.euler_degree[2]:.2f}]"
            )
        else:
            print("Get glove skeleton frame failed!")

        motionGloveSDK.MotionGloveSDK_resetGloveNewFramePending(gloveName)

    time.sleep(0.01)  # 10ms，对应 C++ Sleep(10) / usleep(10000)

motionGloveSDK.MotionGloveSDK_CloseUDPPort()
print("程序退出。")
