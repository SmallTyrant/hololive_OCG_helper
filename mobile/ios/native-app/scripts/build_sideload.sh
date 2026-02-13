#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEME="HocgNative"
TEAM_ID="${TEAM_ID:-}"
BUNDLE_ID="${BUNDLE_ID:-com.smalltyrant.hocg.native}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/build/ipa_sideload}"
DEVICE_ID="${DEVICE_ID:-}"

if [[ -z "$TEAM_ID" ]]; then
  echo "TEAM_ID is required. Example:"
  echo "  TEAM_ID=R777443GCA BUNDLE_ID=com.smalltyrant.hocg.native ./scripts/build_sideload.sh"
  exit 1
fi

cd "$PROJECT_DIR"

echo "[1/3] Build signed iOS app (Release, iphoneos)"
xcodebuild \
  -project "$SCHEME.xcodeproj" \
  -scheme "$SCHEME" \
  -configuration Release \
  -sdk iphoneos \
  -destination "generic/platform=iOS" \
  DEVELOPMENT_TEAM="$TEAM_ID" \
  CODE_SIGN_STYLE=Automatic \
  PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID" \
  OTHER_CODE_SIGN_FLAGS="--deep" \
  -allowProvisioningUpdates \
  build

APP_PATH="$(ls -td "$HOME"/Library/Developer/Xcode/DerivedData/"$SCHEME"-*/Build/Products/Release-iphoneos/"$SCHEME".app 2>/dev/null | head -n 1 || true)"
if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
  echo "Could not find built app bundle in DerivedData."
  exit 1
fi

echo "[2/3] Package IPA"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR/Payload"
cp -R "$APP_PATH" "$OUTPUT_DIR/Payload/"
(
  cd "$OUTPUT_DIR"
  zip -qry "${SCHEME}-signed.ipa" Payload
)

IPA_PATH="$OUTPUT_DIR/${SCHEME}-signed.ipa"
echo "IPA: $IPA_PATH"

if [[ -n "$DEVICE_ID" ]]; then
  echo "[3/3] Install to device ($DEVICE_ID)"
  xcrun devicectl device install app --device "$DEVICE_ID" "$APP_PATH" --verbose
else
  echo "[3/3] Skip device install (set DEVICE_ID to install automatically)"
fi
