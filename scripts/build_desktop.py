#!/usr/bin/env python3
"""Desktop build helper for Windows(.exe) and macOS(.app)."""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
APP_MAIN = ROOT / "app" / "main.py"
PNG_ICON = ROOT / "app" / "app_icon.png"
ICO_ICON = ROOT / "app" / "app_icon.ico"
ICNS_ICON = ROOT / "app" / "app_icon.icns"
ICONSET_DIR = ROOT / "app" / "icon.iconset"


def run_command(command: list[str]) -> None:
    print("+", " ".join(str(part) for part in command))
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_windows_icon() -> Path:
    if not PNG_ICON.exists():
        raise FileNotFoundError(f"PNG 아이콘 파일이 없습니다: {PNG_ICON}")

    ICO_ICON.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(PNG_ICON) as img:
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        img.save(
            ICO_ICON,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    return ICO_ICON


def ensure_macos_icon() -> Path:
    if not PNG_ICON.exists():
        raise FileNotFoundError(f"PNG 아이콘 파일이 없습니다: {PNG_ICON}")

    if ICONSET_DIR.exists():
        shutil.rmtree(ICONSET_DIR)
    ICONSET_DIR.mkdir(parents=True, exist_ok=True)

    icon_sizes = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    with Image.open(PNG_ICON) as img:
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        for size, name in icon_sizes:
            resized = img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(ICONSET_DIR / name, format="PNG")

    run_command(["iconutil", "-c", "icns", str(ICONSET_DIR), "-o", str(ICNS_ICON)])
    shutil.rmtree(ICONSET_DIR)
    return ICNS_ICON


def build_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Windows .exe 빌드는 Windows 환경에서만 가능합니다.")

    icon = ensure_windows_icon()
    run_command(["flet", "pack", str(APP_MAIN), "--icon", str(icon)])


def build_macos() -> None:
    if platform.system() != "Darwin":
        raise RuntimeError("macOS .app 빌드는 macOS 환경에서만 가능합니다.")

    icon = ensure_macos_icon()
    run_command(["flet", "pack", str(APP_MAIN), "--icon", str(icon)])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Windows(.exe) 또는 macOS(.app)용 Flet 앱 빌드를 실행합니다."
    )
    parser.add_argument(
        "target",
        choices=["windows", "macos"],
        help="빌드 대상 플랫폼",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.target == "windows":
        build_windows()
    else:
        build_macos()


if __name__ == "__main__":
    main()
