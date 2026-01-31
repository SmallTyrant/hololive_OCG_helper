#!/usr/bin/env bash
set -euo pipefail

PNG="app/app_icon.png"
ICONSET_DIR="app/icon.iconset"
ICNS="app/app_icon.icns"

rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"

# Generate standard macOS iconset sizes
sips -z 16 16     "$PNG" --out "$ICONSET_DIR/icon_16x16.png"
sips -z 32 32     "$PNG" --out "$ICONSET_DIR/icon_16x16@2x.png"
sips -z 32 32     "$PNG" --out "$ICONSET_DIR/icon_32x32.png"
sips -z 64 64     "$PNG" --out "$ICONSET_DIR/icon_32x32@2x.png"
sips -z 128 128   "$PNG" --out "$ICONSET_DIR/icon_128x128.png"
sips -z 256 256   "$PNG" --out "$ICONSET_DIR/icon_128x128@2x.png"
sips -z 256 256   "$PNG" --out "$ICONSET_DIR/icon_256x256.png"
sips -z 512 512   "$PNG" --out "$ICONSET_DIR/icon_256x256@2x.png"
sips -z 512 512   "$PNG" --out "$ICONSET_DIR/icon_512x512.png"
sips -z 1024 1024 "$PNG" --out "$ICONSET_DIR/icon_512x512@2x.png"

iconutil -c icns "$ICONSET_DIR" -o "$ICNS"
rm -rf "$ICONSET_DIR"

flet pack app/main.py --icon "$ICNS"
