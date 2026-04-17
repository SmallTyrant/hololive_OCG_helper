#!/usr/bin/env python3

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from dataclasses import dataclass
from typing import Iterable


SCOPES = ("android", "ios", "db", "tools", "builder")

DB_FILE = "app/assets/hololive_ocg.sqlite"

SCOPE_PATTERNS: dict[str, tuple[str, ...]] = {
    "android": (
        "mobile/android/native/**",
        "mobile/android/native-app/**",
    ),
    "ios": (
        "mobile/ios/native/**",
        "mobile/ios/native-app/**",
    ),
    "db": (
        DB_FILE,
    ),
    "tools": (
        "app/**",
        "tools/**",
        "scripts/**",
        "**/*.py",
        "pyproject.toml",
        "requirements*.txt",
    ),
    "builder": (
        ".github/workflows/**",
        ".github/actions/**",
    ),
}


@dataclass(frozen=True)
class ScopeResult:
    scope: str
    scopes: tuple[str, ...]
    files: tuple[str, ...]

    @property
    def flags(self) -> dict[str, str]:
        return {
            "scope": self.scope,
            "android": str(self.scope == "android").lower(),
            "ios": str(self.scope == "ios").lower(),
            "db": str(self.scope == "db").lower(),
            "tools": str(self.scope == "tools").lower(),
            "builder": str(self.scope == "builder").lower(),
            "mixed": str(self.scope == "mixed").lower(),
            "none": str(self.scope == "none").lower(),
        }


def normalize_path(path: str) -> str:
    value = path.strip().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    while "//" in value:
        value = value.replace("//", "/")
    return value


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return path.startswith(pattern[:-3])
    return fnmatch.fnmatch(path, pattern)


def classify_file(path: str) -> str | None:
    normalized = normalize_path(path)
    if not normalized:
        return None

    if normalized == DB_FILE:
        return "db"

    for scope in ("android", "ios", "builder", "tools"):
        if any(matches(normalized, pattern) for pattern in SCOPE_PATTERNS[scope]):
            return scope
    return None


def detect_scope(paths: Iterable[str]) -> ScopeResult:
    normalized_files = tuple(normalize_path(path) for path in paths if normalize_path(path))
    scopes = tuple(
        sorted(
            {
                scope
                for scope in (classify_file(path) for path in normalized_files)
                if scope is not None
            }
        )
    )

    if not scopes:
        scope = "none"
    elif len(scopes) == 1:
        scope = scopes[0]
    else:
        scope = "mixed"

    return ScopeResult(scope=scope, scopes=scopes, files=normalized_files)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect the canonical CI scope for a changed-files set.")
    parser.add_argument("files", nargs="*", help="Changed files. If omitted, read newline-delimited paths from stdin.")
    parser.add_argument(
        "--github-output",
        help="Optional path to the GitHub Actions output file. When set, key=value outputs are appended.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print classified scopes and files for debugging.",
    )
    return parser.parse_args()


def write_github_output(path: str, result: ScopeResult) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in result.flags.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    args = parse_args()
    files = args.files or [line.rstrip("\n") for line in sys.stdin]
    result = detect_scope(files)

    if args.github_output:
        write_github_output(args.github_output, result)

    if args.verbose:
        print(f"scope={result.scope}")
        print(f"scopes={','.join(result.scopes) if result.scopes else '(none)'}")
        for path in result.files:
            print(f"{path}: {classify_file(path) or 'unmatched'}")
    else:
        for key, value in result.flags.items():
            print(f"{key}={value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
