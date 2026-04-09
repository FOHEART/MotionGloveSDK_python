"""帧率统计器

整秒桶计数：tick() 每帧调用一次，snapshot() 由外部 1s 定时器调用。
snapshot() 用实际经过时间做除法，消除定时器精度误差导致的 ±1 抖动。
"""

import time


class FpsCounter:
    """整秒桶计数帧率统计器。

    调用方每帧调用 tick()，每秒调用一次 snapshot() 触发更新；
    调用 fps() 获取最近一次 snapshot() 保存的帧率（稳定整数）。
    """

    def __init__(self) -> None:
        self._count = 0           # 当前桶内累计帧数
        self._last_fps = 0        # 上一桶的帧率快照
        self._bucket_start = time.monotonic()

    def tick(self) -> None:
        """记录一帧到达。在每个新帧到来时调用一次。"""
        self._count += 1

    def snapshot(self) -> None:
        """每秒调用一次：用实际经过时间计算帧率并归零桶，由外部 1s 定时器驱动。"""
        now = time.monotonic()
        elapsed = now - self._bucket_start
        if elapsed > 0:
            self._last_fps = round(self._count / elapsed)
        self._count = 0
        self._bucket_start = now

    def fps(self) -> int:
        """返回最近整秒的帧率（稳定整数）。"""
        return self._last_fps

    def reset(self) -> None:
        """清空统计，用于重新开始接收时重置帧率。"""
        self._count = 0
        self._last_fps = 0
        self._bucket_start = time.monotonic()
