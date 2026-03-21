#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("timeout", ("timeout after", "timed out")),
    ("tooling-missing", ("command not found", "no such file or directory")),
    ("compile-error", ("syntaxerror", "build failed", "compilation failed", "compiledebugkotlin")),
    ("test-failure", ("test failed", "assert", "failed tests", "failures:")),
    ("network-or-url", ("http 403", "http 404", "unable to resolve host", "network is unreachable")),
]


def classify(text: str) -> str:
    lowered = text.lower()
    if lowered.strip() == "skipped":
        return "skipped"

    failure_hint = bool(re.search(r"(^|[^a-z])(fail|failed|error|exception|traceback)([^a-z]|$)", lowered))
    for name, keys in PATTERNS:
        if any(key in lowered for key in keys) and failure_hint:
            return name
    return "pass-or-info"


def analyze(log_dir: Path) -> list[tuple[Path, str, str]]:
    rows: list[tuple[Path, str, str]] = []
    for path in sorted(log_dir.rglob("*.log")):
        content = path.read_text(encoding="utf-8", errors="replace")
        category = classify(content)
        first_line = content.splitlines()[0] if content.splitlines() else ""
        rows.append((path, category, first_line[:200]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze CI logs and classify failure categories.")
    parser.add_argument("--log-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.log_dir.exists():
        print(f"log dir not found: {args.log_dir}")
        return 1

    rows = analyze(args.log_dir)
    if not rows:
        print("no log files found")
        return 0

    print(f"Analyzed logs: {len(rows)}")
    for path, category, summary in rows:
        print(f"- {path}: {category} :: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
