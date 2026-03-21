#!/usr/bin/env python3

from __future__ import annotations

import argparse
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIRS = [ROOT / "app", ROOT / "tools", ROOT / "scripts"]
SKIP_PARTS = {".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".artifacts"}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def collect_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for base in paths:
        if not base.exists():
            continue
        for file_path in base.rglob("*.py"):
            if should_skip(file_path):
                continue
            files.append(file_path)
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile python files while skipping build artifacts.")
    parser.add_argument("paths", nargs="*", help="Optional paths (default: app tools scripts)")
    args = parser.parse_args()

    targets = [ROOT / p for p in args.paths] if args.paths else DEFAULT_DIRS
    files = collect_files(targets)
    if not files:
        print("No Python files found.")
        return 0

    failed = 0
    for file_path in files:
        try:
            py_compile.compile(str(file_path), doraise=True)
        except py_compile.PyCompileError as exc:
            failed += 1
            print(f"FAIL: {file_path}")
            print(str(exc))

    if failed:
        print(f"Python syntax check failed: {failed} file(s)")
        return 1

    print(f"Python syntax check passed: {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
