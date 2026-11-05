"""数值回归：为 quat_to_euler_degree 的 6 个旋转序拟合标准提取公式。

方法：对每个序，用被测 euler_degree_to_quat_wxyz 生成 N 组随机角度的四元数，
转成独立旋转矩阵 M（quat_to_matrix，标准公式），然后从 M 中数值反解三个
欧拉角的表达式，搜索顺序：
  1) atan2(±m_ij, ±m_kl) 直接相等（最干净）；
  2) asin(±m_ij) 直接相等；
  3) atan2(±m_ij, cb·±m_kl + sb·±m_mn)（剥第二角型，cb/sb 为第二角余弦/正弦）。
输出可用于替换 xsqeconverter.quat_to_euler_degree 的实现。
"""
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.xsqeconverter import euler_degree_to_quat_wxyz

ORDER_AXES = {0: "XYZ", 1: "XZY", 2: "YXZ", 3: "YZX", 4: "ZXY", 5: "ZYX"}


def quat_to_matrix(q):
    w, x, y, z = q
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ]


def samples_for(order, n=240, seed=11):
    rnd = random.Random(seed + order)
    out = []
    for _ in range(n):
        a, b, c = (rnd.uniform(-85, 85) for _ in range(3))
        q = euler_degree_to_quat_wxyz(a, b, c, order)
        M = quat_to_matrix(q)
        out.append((M, math.radians(a), math.radians(b), math.radians(c)))
    return out


def matches(func, samples, target_idx):
    """func(M) -> float；与目标角(target_idx 0/1/2)的误差总和是否 ~0。"""
    err = 0.0
    for M, a, b, c in samples:
        target = (a, b, c)[target_idx]
        v = func(M)
        d = (v - target + math.pi) % (2 * math.pi) - math.pi  # 角度差到 [-pi,pi]
        err += d * d
    return err


def find_at_atan2(samples, target_idx):
    """搜索 atan2(±m_ij, ±m_kl)。返回 (err, 描述, (i,j,k,l,sg1,sg2)) 或 None。"""
    best = None
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(3):
                    for s1 in (1.0, -1.0):
                        for s2 in (1.0, -1.0):
                            f = lambda M, i=i, j=j, k=k, l=l, s1=s1, s2=s2: \
                                math.atan2(s1 * M[i][j], s2 * M[k][l])
                            e = matches(f, samples, target_idx)
                            if best is None or e < best[0]:
                                best = (e, f"atan2({'+-'[s1<0]}m{i}{j}, {'+-'[s2<0]}m{k}{l})")
                            if e == 0.0:
                                best = (e, f"atan2({'+-'[s1<0]}m{i}{j}, {'+-'[s2<0]}m{k}{l})")
                                return e, best[1]
    return best


def find_asin(samples, target_idx):
    """搜索 asin(±m_ij)。"""
    best = None
    for i in range(3):
        for j in range(3):
            for s in (1.0, -1.0):
                f = lambda M, i=i, j=j, s=s: \
                    math.asin(max(-1.0, min(1.0, s * M[i][j])))
                e = matches(f, samples, target_idx)
                if best is None or e < best[0]:
                    best = (e, f"asin({'+-'[s<0]}m{i}{j})")
    return best


def find_peel(samples, target_idx):
    """搜索 atan2(±m_ij, cb·±m_kl + sb·±m_mn)，cb/sb 由第二角样本提供。
    不通用（依赖 second 角），先做 asin 型尝试。"""
    # 返回 None——该级由"atan2(±m_ij, ±m_kl·cf + ±m_mn·sf)" 需要第二角，暂不在
    # 这里自动搜（先看前两级能否覆盖）。
    return None, None


def fit(order):
    samples = samples_for(order)
    print(f"order={order} ({ORDER_AXES[order]})")
    for idx, name in ((0, "a"), (1, "b"), (2, "c")):
        got = find_at_atan2(samples, idx)
        if got is not None and got[0] < 1e-12:
            print(f"  θ_{name}: {got[1]}   (exact)")
            continue
        got2 = find_asin(samples, idx)
        if got2 is not None and got2[0] < 1e-12:
            print(f"  θ_{name}: {got2[1]}   (exact)")
            continue
        print(f"  θ_{name}: 未找到纯 atan2/asin 形式 (atan2 best err={got[0] if got else '-'}, "
              f"asin best err={got2[0] if got2 else '-'})")


def main():
    for order in range(6):
        fit(order)


if __name__ == "__main__":
    main()