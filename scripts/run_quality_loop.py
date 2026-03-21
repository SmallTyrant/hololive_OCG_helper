#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / ".artifacts" / "quality-loop"


@dataclass
class CheckSpec:
    name: str
    command: list[str]
    cwd: Path
    timeout: int
    enabled: bool = True


@dataclass
class CheckResult:
    name: str
    success: bool
    return_code: int
    duration_sec: float
    output_path: Path
    summary: str
    category: str


def run(cmd: list[str], cwd: Path, timeout: int) -> tuple[bool, int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, 124, f"TIMEOUT after {timeout}s"
    except FileNotFoundError:
        return False, 127, f"COMMAND NOT FOUND: {cmd[0]}"

    merged = "\n".join(x for x in [proc.stdout, proc.stderr] if x).strip()
    if not merged:
        merged = f"exit={proc.returncode}"
    return proc.returncode == 0, proc.returncode, merged


def classify_failure(text: str) -> str:
    lowered = text.lower()
    if "timeout" in lowered:
        return "timeout"
    if "command not found" in lowered or "no such file or directory" in lowered:
        return "tooling-missing"
    if "syntaxerror" in lowered or "compile" in lowered and "failed" in lowered:
        return "compile-error"
    if "assert" in lowered or "test" in lowered and "failed" in lowered:
        return "test-failure"
    if "403" in lowered or "404" in lowered or "http" in lowered and "error" in lowered:
        return "network-or-url"
    return "unknown"


def git_diff_summary() -> dict[str, str]:
    data: dict[str, str] = {}
    cmds = {
        "status": ["git", "status", "--short"],
        "stat": ["git", "diff", "--stat"],
        "names": ["git", "diff", "--name-only"],
    }
    for key, cmd in cmds.items():
        ok, _, out = run(cmd, ROOT, timeout=60)
        data[key] = out if ok or out else ""
    return data


def build_checks(args: argparse.Namespace) -> list[CheckSpec]:
    checks: list[CheckSpec] = [
        CheckSpec(
            name="python-compile",
            command=["python3", "scripts/python_syntax_check.py"],
            cwd=ROOT,
            timeout=240,
            enabled=not args.skip_python,
        ),
    ]

    audit_deck = ROOT / "tools" / "audit_deck_limits.py"
    if audit_deck.exists():
        checks.append(
            CheckSpec(
                name="audit-deck-limits",
                command=["python3", str(audit_deck)],
                cwd=ROOT,
                timeout=240,
                enabled=not args.skip_python,
            )
        )

    audit_hy = ROOT / "tools" / "audit_hy_images.py"
    if audit_hy.exists():
        checks.append(
            CheckSpec(
                name="audit-hy-images",
                command=["python3", str(audit_hy)],
                cwd=ROOT,
                timeout=240,
                enabled=not args.skip_python,
            )
        )

    checks.append(
        CheckSpec(
            name="android-unit",
            command=["./gradlew", "test"],
            cwd=ROOT / "mobile" / "android" / "native-app",
            timeout=1800,
            enabled=not args.skip_android,
        )
    )

    ios_enabled = (not args.skip_ios) and platform.system() == "Darwin"
    checks.append(
        CheckSpec(
            name="ios-build",
            command=[
                "xcodebuild",
                "-project",
                "HocgNative.xcodeproj",
                "-scheme",
                "HocgNative",
                "-configuration",
                "Debug",
                "-destination",
                "generic/platform=iOS Simulator",
                "CODE_SIGNING_ALLOWED=NO",
                "build",
            ],
            cwd=ROOT / "mobile" / "ios" / "native-app",
            timeout=2400,
            enabled=ios_enabled,
        )
    )
    return checks


def execute_checks(checks: list[CheckSpec], out_dir: Path) -> list[CheckResult]:
    active = [c for c in checks if c.enabled]
    results: list[CheckResult] = []

    def _run_one(spec: CheckSpec) -> CheckResult:
        start = time.time()
        ok, code, output = run(spec.command, spec.cwd, spec.timeout)
        duration = time.time() - start
        out_path = out_dir / f"{spec.name}.log"
        out_path.write_text(output, encoding="utf-8")
        summary_line = output.splitlines()[0] if output else f"exit={code}"
        return CheckResult(
            name=spec.name,
            success=ok,
            return_code=code,
            duration_sec=duration,
            output_path=out_path,
            summary=summary_line[:200],
            category="ok" if ok else classify_failure(output),
        )

    with ThreadPoolExecutor(max_workers=max(1, len(active))) as executor:
        future_map = {executor.submit(_run_one, spec): spec.name for spec in active}
        for future in as_completed(future_map):
            results.append(future.result())

    disabled = [c for c in checks if not c.enabled]
    for spec in disabled:
        out_path = out_dir / f"{spec.name}.log"
        out_path.write_text("SKIPPED\n", encoding="utf-8")
        results.append(
            CheckResult(
                name=spec.name,
                success=True,
                return_code=0,
                duration_sec=0.0,
                output_path=out_path,
                summary="SKIPPED",
                category="skipped",
            )
        )

    return sorted(results, key=lambda r: r.name)


def write_report(
    report_path: Path,
    attempt: int,
    results: list[CheckResult],
    diff: dict[str, str],
    fix_command: str | None,
) -> None:
    payload = {
        "attempt": attempt,
        "timestamp": int(time.time()),
        "results": [
            {
                "name": r.name,
                "success": r.success,
                "return_code": r.return_code,
                "duration_sec": round(r.duration_sec, 2),
                "summary": r.summary,
                "category": r.category,
                "log": str(r.output_path),
            }
            for r in results
        ],
        "diff": diff,
        "fix_command": fix_command,
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Repeatable quality loop: run checks in parallel, analyze failures, "
            "optionally run fix command, and retry."
        )
    )
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--fix-command", type=str, default="")
    parser.add_argument("--skip-python", action="store_true")
    parser.add_argument("--skip-android", action="store_true")
    parser.add_argument("--skip-ios", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)

    fix_command = args.fix_command.strip() or None
    max_attempts = max(1, args.max_attempts)

    for attempt in range(1, max_attempts + 1):
        attempt_dir = ARTIFACT_ROOT / f"attempt-{attempt:02d}"
        attempt_dir.mkdir(parents=True, exist_ok=True)

        checks = build_checks(args)
        diff = git_diff_summary()
        results = execute_checks(checks, attempt_dir)
        report_file = attempt_dir / "report.json"
        write_report(report_file, attempt, results, diff, fix_command)

        failed = [r for r in results if not r.success]
        print(f"Attempt {attempt}/{max_attempts}")
        for row in results:
            status = "PASS" if row.success else "FAIL"
            print(f"  [{status}] {row.name} ({row.category}) {row.summary}")
        print(f"  Report: {report_file}")

        if not failed:
            print("Quality loop result: PASS")
            return 0

        if not fix_command or attempt == max_attempts:
            print("Quality loop result: FAIL")
            return 1

        print(f"Running fix command: {fix_command}")
        ok, code, out = run(["bash", "-lc", fix_command], ROOT, timeout=3600)
        fix_log = attempt_dir / "fix-command.log"
        fix_log.write_text(out, encoding="utf-8")
        if not ok:
            print(f"Fix command failed (exit={code}). See: {fix_log}")
            return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
