"""@file  blender_path_detector.py
@brief 从 <repo>/libs 下探测 Blender 可执行文件路径。
@details
依赖独立（不 import bpy），可单元测试。规则：在 libs 目录下寻找名称
含 "blender" 的子目录，取其中 blender.exe。结果以 BlenderDetectionResult
数据类返回（status ∈ found / missing-libs / missing-candidate /
missing-executable / error）。

命令行用法：
  python src/blender_path_detector.py [search_root] [--verbose]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlenderDetectionResult:
    """@brief Blender 探测结果（不可变数据类）。

    @details fields: search_root 搜索根目录；libs_dir libs 目录；
             candidate_dirs 命中的候选子目录；executable_path 找到的
             blender.exe；status 状态标识；error 探测异常信息。
    """

    search_root: Path
    libs_dir: Path
    candidate_dirs: tuple[Path, ...]
    executable_path: Path | None
    status: str
    error: str = ""

    @property
    def found(self) -> bool:
        """@brief 是否找到可执行文件。@return 找到为 True。"""
        return self.executable_path is not None


def detect_blender_executable(search_root: str | Path | None = None) -> BlenderDetectionResult:
    """@brief 在 search_root/libs 下探测 blender.exe。

    @details 查找名称含 "blender" 的子目录（忽略大小写，按名称排序），
             返回其中第一个存在的 blender.exe 的绝对路径。
    @param search_root 搜索根目录；None 时使用当前工作目录。
    @return BlenderDetectionResult：status="found" 时 executable_path
            非空；其他状态见 @file 说明。
    """
    base_dir = Path(search_root) if search_root is not None else Path.cwd()
    base_dir = base_dir.resolve()
    libs_dir = base_dir / "libs"

    if not libs_dir.is_dir():
        return BlenderDetectionResult(
            search_root=base_dir,
            libs_dir=libs_dir,
            candidate_dirs=(),
            executable_path=None,
            status="missing-libs",
        )

    try:
        candidate_dirs = tuple(
            sorted(
                (
                    child
                    for child in libs_dir.iterdir()
                    if child.is_dir() and "blender" in child.name.lower()
                ),
                key=lambda path: path.name.lower(),
            )
        )
    except OSError as exc:
        return BlenderDetectionResult(
            search_root=base_dir,
            libs_dir=libs_dir,
            candidate_dirs=(),
            executable_path=None,
            status="error",
            error=str(exc),
        )

    if not candidate_dirs:
        return BlenderDetectionResult(
            search_root=base_dir,
            libs_dir=libs_dir,
            candidate_dirs=(),
            executable_path=None,
            status="missing-candidate",
        )

    for candidate_dir in candidate_dirs:
        executable_path = candidate_dir / "blender.exe"
        if executable_path.is_file():
            return BlenderDetectionResult(
                search_root=base_dir,
                libs_dir=libs_dir,
                candidate_dirs=candidate_dirs,
                executable_path=executable_path.resolve(),
                status="found",
            )

    return BlenderDetectionResult(
        search_root=base_dir,
        libs_dir=libs_dir,
        candidate_dirs=candidate_dirs,
        executable_path=None,
        status="missing-executable",
    )


def format_detection_message(result: BlenderDetectionResult) -> str:
    """@brief 把探测结果格式化为人类可读的英文描述。

    @param result detect_blender_executable 的返回值。
    @return 描述字符串（found 时含可执行文件路径）。
    """
    if result.status == "found" and result.executable_path is not None:
        return f"Found Blender executable: {result.executable_path}"
    if result.status == "missing-libs":
        return f"libs directory not found: {result.libs_dir}"
    if result.status == "missing-candidate":
        return f"No subdirectory containing 'blender' was found under: {result.libs_dir}"
    if result.status == "missing-executable":
        return (
            "No blender.exe found in candidate directories under: "
            f"{result.libs_dir}"
        )
    if result.status == "error":
        return f"Failed to inspect Blender directories: {result.error}"
    return "Unknown Blender detection state"


def main(argv: list[str] | None = None) -> int:
    """@brief 命令行入口：打印探测结果。

    @param argv 命令行参数列表；None 时使用 sys.argv。
    @return 0 找到可执行文件；1 未找到（结果打到 stderr）。
    """
    parser = argparse.ArgumentParser(
        prog="blender_path_detector.py",
        description="Detect blender.exe from the current working directory's libs folder.",
    )
    parser.add_argument(
        "search_root",
        nargs="?",
        default=None,
        help="Optional search root. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print candidate directories that were inspected.",
    )
    args = parser.parse_args(argv)

    result = detect_blender_executable(args.search_root)
    message = format_detection_message(result)

    if args.verbose and result.candidate_dirs:
        print("Candidate directories:")
        for candidate_dir in result.candidate_dirs:
            print(candidate_dir)

    output = str(result.executable_path) if result.found and result.executable_path is not None else message
    stream = sys.stdout if result.found else sys.stderr
    print(output, file=stream)
    return 0 if result.found else 1


if __name__ == "__main__":
    raise SystemExit(main())