#!/usr/bin/env python3
"""
@file  sync_agent_harness.py
@brief 把 agent-harness/ 与仓库根 SKILL.md 同步到安装目录/分发包。
@details
跨平台纯 Python（由 sync_agent_harness.bat 双解释器包装，也被 buildDeploy.bat 调用）。
排除 __pycache__ / .pytest_cache / *.egg-info / *.pyc；支持 --check 做解包后自检。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def _force_utf8_stdio() -> None:
    """@brief 控制台默认可能是 cp1252，中文结果输出前统一切 UTF-8。"""
    for name in ("stdout", "stderr", "stdin"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


_force_utf8_stdio()

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "agent-harness"
SKILL = ROOT / "SKILL.md"
DEFAULT_DIST = ROOT / "dist" / "MotionGlove3DViewer"

IGNORE = shutil.ignore_patterns(
    "__pycache__", "*.pyc", "*.pyo", ".pytest_cache",
    "*.egg-info", ".mypy_cache", ".git",
)

REQUIRED = (
    "agent-harness/cli_anything/motionglove/_cli.py",
    "agent-harness/cli_anything/motionglove/utils/backend.py",
    "agent-harness/cli_anything/motionglove/utils/repl_skin.py",
    "agent-harness/cli_anything/motionglove/setup.py",
    "agent-harness/cli_anything/motionglove/tests/test_core.py",
    "agent-harness/cli_anything/motionglove/tests/test_full_e2e.py",
    "SKILL.md",
)


def verify(dest: Path) -> list[str]:
    """@brief 自检分发目录：返回缺失文件列表。

    @param dest 分发/安装目录。
    @return 缺失的相对路径列表；空列表表示完整。
    """
    missing = [rel for rel in REQUIRED if not (dest / rel).is_file()]
    # 只检查 harness 子树：安装目录里还有 PyInstaller 的 _internal/ 等
    # 无关产物，全盘 rglob 会把别人遗留的 __pycache__ 误判为同步失败。
    harness = dest / "agent-harness"
    if harness.is_dir():
        for stray in harness.rglob("*"):
            if stray.is_dir() and (
                stray.name in ("__pycache__", ".pytest_cache", ".mypy_cache")
                or stray.name.endswith(".egg-info")
            ):
                missing.append(f"不应存在的缓存/构建残留：{stray.relative_to(dest)}")
        # SKILL.md 单一来源：harness 内不允许出现副本
        for duplicate in harness.rglob("SKILL.md"):
            missing.append(f"harness 内不应含 SKILL.md 副本：{duplicate.relative_to(dest)}")
    return missing


def sync(dest: Path) -> dict[str, object]:
    """@brief 同步 harness 与 SKILL.md 到目标目录并自检。

    @param dest 目标目录（不存在则创建）。
    @return 同步结果摘要。
    @exception FileNotFoundError 源目录或 SKILL.md 缺失。
    @exception RuntimeError 同步后自检失败。
    """
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"未找到源目录：{SOURCE}")
    if not SKILL.is_file():
        raise FileNotFoundError(f"未找到唯一一份 SKILL.md：{SKILL}")

    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "agent-harness"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SOURCE, target, ignore=IGNORE)
    shutil.copy2(SKILL, dest / "SKILL.md")

    missing = verify(dest)
    if missing:
        raise RuntimeError("同步后自检失败：" + "; ".join(missing))

    copied = sum(1 for p in target.rglob("*") if p.is_file())
    return {
        "dest": str(dest),
        "harness_files": copied,
        "skill": str(dest / "SKILL.md"),
        "skill_unique": True,
    }


def main(argv: list[str] | None = None) -> int:
    """@brief 命令行入口。

    @param argv 参数列表（不含程序名）。
    @return 0 成功，1 失败。
    """
    parser = argparse.ArgumentParser(
        description="同步 agent-harness 与 SKILL.md 到安装/分发目录"
    )
    parser.add_argument(
        "--dist", default=str(DEFAULT_DIST), help="目标目录（默认 dist/MotionGlove3DViewer）"
    )
    parser.add_argument(
        "--check", action="store_true", help="只自检、不复制（分发包解包后使用）"
    )
    args = parser.parse_args(argv)
    dest = Path(args.dist).expanduser().resolve()

    try:
        if args.check:
            missing = verify(dest)
            if missing:
                for item in missing:
                    print(f"[error] {item}")
                return 1
            print(f"[ok] 分发目录自检通过：{dest}")
            print("[ok] 含 agent-harness 与唯一一份 SKILL.md，且无缓存目录")
            return 0
        result = sync(dest)
    except (OSError, RuntimeError) as exc:
        print(f"[error] agent-harness 同步失败：{exc}", file=sys.stderr)
        return 1

    print(f"[ok] agent-harness 已同步：{result['harness_files']} 个文件")
    print(f"[ok] 目标目录：{result['dest']}")
    print(f"[ok] SKILL.md：{result['skill']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
