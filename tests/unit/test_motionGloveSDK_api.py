"""
@file  test_motionGloveSDK_api.py
@brief motionGloveSDK 对外 API 的纯 Python 侧单元测试。
@details
覆盖策略
 - 边界条件：actorName 字节长度上限（C++ 缓冲区 ACTOR_NAME_LEN_MAX 含结尾
   NUL，有效长度 ≤ 63 字节），字节按 UTF-8 计算、中英文同样适用；
 - 异常场景：空字符串 / 超长名称 / 名称超长时调用 is_pending 等接口
   “短路”返回 False，不触发原生后端加载（后端依赖 DLL，测试环境不应触碰）。

不测“名称合法 + 有数据流”——那依赖原生库，属于集成测试范畴，
由 scripts/verify_native_abi.py 或真机/模拟器冒烟脚本覆盖。
"""

import pytest

from src import motionGloveSDK


# ── _is_valid_actor_name 边界 ────────────────────────────────────────────────


def test_Api_EmptyActorNameIsInvalid():
    """@test   motionGloveSDK.EmptyActorNameIsInvalid
    @brief  空字符串不是合法数据流名称。
    @details 目的：C++ 缓冲区的名称以 NUL 结尾，空名无法标识任何数据流。
    @expected _is_valid_actor_name("") == False
    @priority P0
    """
    assert motionGloveSDK._is_valid_actor_name("") is False


def test_Api_AsciiNameAtByteLimitIsValid():
    """@test   motionGloveSDK.AsciiNameAtByteLimitIsValid
    @brief  63 字节 ASCII 名称恰好合法（上限边界值）。
    @details 目的：ACTOR_NAME_LEN_MAX 含结尾 NUL，63 字节恰好填满有效区，
             是必须放行的边界值（错误收窄会破坏现有名称）。
    @expected 63 个 'a' → True
    @priority P0
    """
    assert motionGloveSDK._is_valid_actor_name("a" * 63) is True


def test_Api_AsciiNameOverByteLimitIsInvalid():
    """@test   motionGloveSDK.AsciiNameOverByteLimitIsInvalid
    @brief  64 字节 ASCII 名称超限，必须拒绝（防止 C++ 侧越界写）。
    @details 目的：能通过 Python 校验的名称为 C++ strncpy 提供前置保证，
             64 字节会写穿缓冲区，必须返回 False。
    @expected 64 个 'a' → False
    @priority P0
    """
    assert motionGloveSDK._is_valid_actor_name("a" * 64) is False


def test_Api_Utf8ChineseNameCountsInBytes():
    """@test   motionGloveSDK.Utf8ChineseNameCountsInBytes
    @brief  中文名称按 UTF-8 字节数计（每个汉字 3 字节）而非字符数。
    @details 目的：21 个汉字 = 63 字节恰好合法；22 个汉字 = 66 字节超限。
             Python 侧 str 的 len() 是字符数，必须 encode 后判断。
    @expected 21 个'手' → True；22 个'手' → False
    @priority P1
    """
    assert motionGloveSDK._is_valid_actor_name("手" * 21) is True
    assert motionGloveSDK._is_valid_actor_name("手" * 22) is False


# ── 公开接口的无效名称短路 ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "fn_name",
    [
        "MotionGloveSDK_isGloveNewFramePending",
        "MotionGloveSDK_resetGloveNewFramePending",
    ],
)
def test_Api_InvalidNameShortCircuitsWithoutBackend(fn_name, monkeypatch):
    """@test   motionGloveSDK.InvalidNameShortCircuitsWithoutBackend
    @brief  名称无效时公开接口直接返回 False，绝不触碰原生后端。
    @details 目的：后端加载依赖 DLL；无效名称走短路路径可保证在不带
             原生库的纯 Python 环境（如 CI 单测）也能安全调用。
             用 monkeypatch 把 get_backend 换成抛异常函数做哨兵——
             若实现试图调用后端，测试立即失败。
    @expected 返回 False 且哨兵未被调用
    @priority P0
    """
    # Arrange：哨兵——一旦触碰后端就抛错
    def bomb():
        raise AssertionError("无效名称不应触发后端加载")

    monkeypatch.setattr(motionGloveSDK.native, "get_backend", bomb)

    # Act / Assert
    fn = getattr(motionGloveSDK, fn_name)
    assert fn("") is False
    assert fn("x" * 64) is False


def test_Api_SkeletonFrameTypeInvalidNameReturnsNone(monkeypatch):
    """@test   motionGloveSDK.SkeletonFrameTypeInvalidNameReturnsNone
    @brief  GetSkeletonsFrameType 对无效名称返回 None（区别于 False）。
    @details 目的：该接口返回值是「格式枚举或 None」，无效名称必须返回
             None 而不是枚举值，否则上层会拿到假格式。
    @expected fn("") is None
    @priority P0
    """
    # Arrange
    def bomb():
        raise AssertionError("无效名称不应触发后端加载")

    monkeypatch.setattr(motionGloveSDK.native, "get_backend", bomb)

    # Act / Assert
    assert motionGloveSDK.MotionGloveSDK_GetSkeletonsFrameType("") is None