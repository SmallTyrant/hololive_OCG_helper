#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ANDROID_APP_DIR = ROOT / "mobile" / "android" / "native-app"
ANDROID_APP_MODULE_DIR = ANDROID_APP_DIR / "app"
ANDROID_GRADLE_FILE = ANDROID_APP_MODULE_DIR / "build.gradle.kts"
ANDROID_MANIFEST_FILE = ANDROID_APP_MODULE_DIR / "src" / "main" / "AndroidManifest.xml"

IOS_APP_DIR = ROOT / "mobile" / "ios" / "native-app"
IOS_PROJECT_FILE = IOS_APP_DIR / "project.yml"
IOS_XCODEPROJ = IOS_APP_DIR / "HocgNative.xcodeproj"


@dataclass
class CheckResult:
    status: str
    name: str
    detail: str
    blocker: bool


def run_command(command: list[str], cwd: Path, timeout: int = 600) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return False, f"command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"

    merged = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    if not merged:
        merged = f"exit={proc.returncode}"
    return proc.returncode == 0, merged


def first_lines(text: str, limit: int = 6) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return " | ".join(lines)
    return " | ".join(lines[:limit]) + " | ..."


class Gate:
    def __init__(self) -> None:
        self.results: list[CheckResult] = []

    def pass_(self, name: str, detail: str) -> None:
        self.results.append(CheckResult("PASS", name, detail, False))

    def fail(self, name: str, detail: str, *, blocker: bool = True) -> None:
        self.results.append(CheckResult("FAIL", name, detail, blocker))

    def skip(self, name: str, detail: str) -> None:
        self.results.append(CheckResult("SKIP", name, detail, False))

    @property
    def blocker_count(self) -> int:
        return sum(1 for result in self.results if result.status == "FAIL" and result.blocker)

    def print_report(self) -> None:
        for result in self.results:
            print(f"[{result.status}] {result.name}: {result.detail}")

        if self.blocker_count:
            print(f"\nGate result: NO-GO ({self.blocker_count} blocker(s))")
        else:
            print("\nGate result: GO")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_android_versions(gradle_text: str) -> tuple[str | None, str | None]:
    code_match = re.search(r"versionCode\s*=\s*(?:.*\?:\s*)?(\d+)", gradle_text)
    name_match = re.search(r'versionName\s*=\s*(?:.*\?:\s*)?"([^"]+)"', gradle_text)
    code = code_match.group(1) if code_match else None
    name = name_match.group(1) if name_match else None
    return code, name


def parse_ios_versions(project_text: str) -> tuple[str | None, str | None]:
    marketing_match = re.search(r"^\s*MARKETING_VERSION:\s*([^\s]+)", project_text, flags=re.MULTILINE)
    build_match = re.search(r"^\s*CURRENT_PROJECT_VERSION:\s*([^\s]+)", project_text, flags=re.MULTILINE)
    marketing = marketing_match.group(1) if marketing_match else None
    build = build_match.group(1) if build_match else None
    return marketing, build


def parse_android_source_dirs(gradle_text: str) -> list[str]:
    raw_entries = re.findall(r"java\.srcDirs\((.*?)\)", gradle_text)
    paths: list[str] = []
    for raw in raw_entries:
        for path in re.findall(r'"([^\"]+)"', raw):
            paths.append(path)
    return paths


def parse_android_namespace(gradle_text: str) -> str | None:
    match = re.search(r"namespace\s*=\s*\"([^\"]+)\"", gradle_text)
    return match.group(1) if match else None


def parse_manifest_activity(manifest_text: str) -> str | None:
    match = re.search(r"<activity[^>]*android:name=\"([^\"]+)\"", manifest_text)
    return match.group(1) if match else None


def parse_manifest_package(manifest_text: str) -> str | None:
    match = re.search(r"<manifest[^>]*package=\"([^\"]+)\"", manifest_text)
    return match.group(1) if match else None


def resolve_activity_name(activity_name: str, package_name: str | None, namespace: str | None) -> str:
    if activity_name.startswith("."):
        prefix = package_name or namespace or ""
        return f"{prefix}{activity_name}" if prefix else activity_name.lstrip(".")
    if "." not in activity_name and (package_name or namespace):
        prefix = package_name or namespace
        return f"{prefix}.{activity_name}"
    return activity_name


def has_android_sdk() -> tuple[bool, str]:
    for env_key in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.getenv(env_key, "").strip()
        if value and Path(value).exists():
            return True, f"{env_key}={value}"

    local_properties = ANDROID_APP_DIR / "local.properties"
    if local_properties.exists():
        for line in read_text(local_properties).splitlines():
            line = line.strip()
            if line.startswith("sdk.dir="):
                sdk_dir = line.split("=", 1)[1].strip().replace("\\\\", "\\")
                if Path(sdk_dir).exists():
                    return True, f"sdk.dir={sdk_dir}"
                return False, f"sdk.dir path missing: {sdk_dir}"

    return False, "set ANDROID_HOME/ANDROID_SDK_ROOT or mobile/android/native-app/local.properties"


def parse_ios_source_paths(project_text: str) -> list[str]:
    return re.findall(r"^\s*-\s*path:\s*([^\n#]+)", project_text, flags=re.MULTILINE)


def count_swift_sources(path: Path) -> int:
    return len(list(path.rglob("*.swift")))


def check_android(gate: Gate, run_commands: bool, run_builds: bool) -> tuple[str | None, str | None]:
    if not ANDROID_GRADLE_FILE.exists():
        gate.fail("Android Gradle config", f"missing {ANDROID_GRADLE_FILE}")
        return None, None
    gate.pass_("Android Gradle config", str(ANDROID_GRADLE_FILE.relative_to(ROOT)))

    if not ANDROID_MANIFEST_FILE.exists():
        gate.fail("Android manifest", f"missing {ANDROID_MANIFEST_FILE}")
        return None, None
    gate.pass_("Android manifest", str(ANDROID_MANIFEST_FILE.relative_to(ROOT)))

    gradle_text = read_text(ANDROID_GRADLE_FILE)
    manifest_text = read_text(ANDROID_MANIFEST_FILE)

    version_code, version_name = parse_android_versions(gradle_text)
    if version_code and version_name:
        gate.pass_("Android version fields", f"versionName={version_name}, versionCode={version_code}")
    else:
        gate.fail("Android version fields", "versionName/versionCode parse failed")

    source_dirs_ok = True
    source_dir_entries = parse_android_source_dirs(gradle_text)
    if not source_dir_entries:
        source_dirs_ok = False
        gate.fail("Android sourceSets", "java.srcDirs(...) entry not found")
    else:
        for raw_path in source_dir_entries:
            resolved = (ANDROID_APP_MODULE_DIR / raw_path).resolve()
            rel = resolved.relative_to(ROOT) if resolved.is_relative_to(ROOT) else resolved
            if not resolved.exists():
                source_dirs_ok = False
                gate.fail("Android source path", f"missing {rel} (from app/build.gradle.kts)")
            else:
                file_count = len(list(resolved.rglob("*.kt"))) + len(list(resolved.rglob("*.java")))
                if file_count == 0:
                    source_dirs_ok = False
                    gate.fail("Android source path", f"no .kt/.java files in {rel}")
                else:
                    gate.pass_("Android source path", f"{rel} ({file_count} source files)")

    activity_name = parse_manifest_activity(manifest_text)
    package_name = parse_manifest_package(manifest_text)
    namespace = parse_android_namespace(gradle_text)

    if not activity_name:
        gate.fail("Android launcher activity", "android:name not found in manifest activity")
    else:
        fqcn = resolve_activity_name(activity_name, package_name, namespace)
        rel = Path(*fqcn.split("."))
        roots = [ANDROID_APP_MODULE_DIR / "src" / "main" / "java", ANDROID_APP_MODULE_DIR / "src" / "main" / "kotlin"]
        roots.extend((ANDROID_APP_MODULE_DIR / raw).resolve() for raw in source_dir_entries)
        found_path = None
        for root in roots:
            for ext in (".kt", ".java"):
                candidate = root / f"{rel}{ext}"
                if candidate.exists():
                    found_path = candidate
                    break
            if found_path:
                break
        if found_path:
            gate.pass_("Android launcher activity", str(found_path.relative_to(ROOT)))
        else:
            gate.fail("Android launcher activity", f"class file not found for {fqcn}")

    if run_commands:
        ok, output = run_command(["./gradlew", "-q", "help"], cwd=ANDROID_APP_DIR, timeout=180)
        if ok:
            gate.pass_("Android Gradle health", "./gradlew -q help")
        else:
            gate.fail("Android Gradle health", first_lines(output))

        sdk_ok, sdk_detail = has_android_sdk()
        if sdk_ok:
            gate.pass_("Android SDK config", sdk_detail)
            if run_builds and source_dirs_ok:
                ok, output = run_command(["./gradlew", ":app:compileDebugKotlin"], cwd=ANDROID_APP_DIR, timeout=600)
                if ok:
                    gate.pass_("Android compile gate", ":app:compileDebugKotlin")
                else:
                    gate.fail("Android compile gate", first_lines(output))
            elif run_builds:
                gate.skip("Android compile gate", "skipped because source path checks already failed")
        else:
            gate.fail("Android SDK config", sdk_detail)
            if run_builds:
                gate.skip("Android compile gate", "skipped because Android SDK is not configured")

    return version_code, version_name


def check_ios(gate: Gate, run_commands: bool, run_builds: bool) -> tuple[str | None, str | None]:
    if not IOS_PROJECT_FILE.exists():
        gate.fail("iOS project config", f"missing {IOS_PROJECT_FILE}")
        return None, None
    gate.pass_("iOS project config", str(IOS_PROJECT_FILE.relative_to(ROOT)))

    if not IOS_XCODEPROJ.exists():
        gate.fail("iOS xcodeproj", f"missing {IOS_XCODEPROJ}")
        return None, None
    gate.pass_("iOS xcodeproj", str(IOS_XCODEPROJ.relative_to(ROOT)))

    project_text = read_text(IOS_PROJECT_FILE)
    marketing_version, build_number = parse_ios_versions(project_text)
    if marketing_version and build_number:
        gate.pass_("iOS version fields", f"MARKETING_VERSION={marketing_version}, CURRENT_PROJECT_VERSION={build_number}")
        if not build_number.isdigit():
            gate.fail("iOS build number format", "CURRENT_PROJECT_VERSION must be numeric")
    else:
        gate.fail("iOS version fields", "MARKETING_VERSION/CURRENT_PROJECT_VERSION parse failed")

    source_paths_ok = True
    source_paths = parse_ios_source_paths(project_text)
    if not source_paths:
        source_paths_ok = False
        gate.fail("iOS sources list", "no '- path:' entries found in project.yml")
    else:
        for raw_path in source_paths:
            clean_path = raw_path.strip().strip("\"'")
            resolved = (IOS_APP_DIR / clean_path).resolve()
            rel = resolved.relative_to(ROOT) if resolved.is_relative_to(ROOT) else resolved
            if not resolved.exists():
                source_paths_ok = False
                gate.fail("iOS source path", f"missing {rel} (from project.yml)")
                continue
            if "Sources" in clean_path and resolved.is_dir():
                swift_count = count_swift_sources(resolved)
                if swift_count == 0:
                    source_paths_ok = False
                    gate.fail("iOS source path", f"no .swift files in {rel}")
                else:
                    gate.pass_("iOS source path", f"{rel} ({swift_count} swift files)")
            else:
                gate.pass_("iOS source path", str(rel))

    if run_commands:
        ok, output = run_command(["xcodebuild", "-list", "-project", "HocgNative.xcodeproj"], cwd=IOS_APP_DIR, timeout=180)
        if ok:
            gate.pass_("iOS xcodebuild health", "xcodebuild -list")
        else:
            gate.fail("iOS xcodebuild health", first_lines(output))

        if run_builds:
            if sys.platform != "darwin":
                gate.skip("iOS compile gate", "skipped because host OS is not macOS")
            elif source_paths_ok:
                cmd = [
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
                ]
                ok, output = run_command(cmd, cwd=IOS_APP_DIR, timeout=900)
                if ok:
                    gate.pass_("iOS compile gate", "simulator debug build")
                else:
                    gate.fail("iOS compile gate", first_lines(output))
            else:
                gate.skip("iOS compile gate", "skipped because source path checks already failed")

    return build_number, marketing_version


def check_version_sync(gate: Gate, android_version_name: str | None, ios_marketing_version: str | None) -> None:
    if not android_version_name or not ios_marketing_version:
        gate.skip("Cross-platform version sync", "skipped because version fields were not fully parsed")
        return
    if android_version_name == ios_marketing_version:
        gate.pass_("Cross-platform version sync", f"Android/iOS version={android_version_name}")
    else:
        gate.fail(
            "Cross-platform version sync",
            f"Android versionName={android_version_name}, iOS MARKETING_VERSION={ios_marketing_version}",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Android/iOS mobile build gate with source-path and build health checks.",
    )
    parser.add_argument(
        "--target",
        choices=["all", "android", "ios"],
        default="all",
        help="Gate target platform",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run config/path checks only (skip command/build execution)",
    )
    parser.add_argument(
        "--skip-builds",
        action="store_true",
        help="Run health commands but skip compile/build commands",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = Gate()

    run_commands = not args.preflight_only
    run_builds = run_commands and not args.skip_builds

    android_version_name: str | None = None
    ios_marketing_version: str | None = None

    if args.target in ("all", "android"):
        _, android_version_name = check_android(gate, run_commands=run_commands, run_builds=run_builds)
    if args.target in ("all", "ios"):
        _, ios_marketing_version = check_ios(gate, run_commands=run_commands, run_builds=run_builds)
    if args.target == "all":
        check_version_sync(gate, android_version_name, ios_marketing_version)

    gate.print_report()
    return 1 if gate.blocker_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
