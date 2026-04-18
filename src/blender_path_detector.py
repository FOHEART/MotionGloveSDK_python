from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BlenderDetectionResult:
    search_root: Path
    libs_dir: Path
    candidate_dirs: tuple[Path, ...]
    executable_path: Path | None
    status: str
    error: str = ""

    @property
    def found(self) -> bool:
        return self.executable_path is not None


def detect_blender_executable(search_root: str | Path | None = None) -> BlenderDetectionResult:
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