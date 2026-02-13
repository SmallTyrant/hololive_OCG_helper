#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEME="HocgNative"

TEAM_ID="${TEAM_ID:-}"
BUNDLE_ID="${BUNDLE_ID:-com.smalltyrant.hocg.native}"
MARKETING_VERSION="${MARKETING_VERSION:-}"
BUILD_NUMBER="${BUILD_NUMBER:-}"
ARCHIVE_PATH="${ARCHIVE_PATH:-$PROJECT_DIR/build/HocgNative-TestFlight.xcarchive}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_DIR/build/ipa_testflight}"
UPLOAD="${UPLOAD:-0}"

# Upload auth options (used only when UPLOAD=1)
ASC_API_KEY_ID="${ASC_API_KEY_ID:-}"
ASC_API_ISSUER_ID="${ASC_API_ISSUER_ID:-}"
ASC_APPLE_ID="${ASC_APPLE_ID:-}"
ASC_APP_PASSWORD="${ASC_APP_PASSWORD:-}"
ASC_PROVIDER_PUBLIC_ID="${ASC_PROVIDER_PUBLIC_ID:-}"

if [[ -z "$TEAM_ID" ]]; then
  echo "TEAM_ID is required. Example:"
  echo "  TEAM_ID=R777443GCA BUNDLE_ID=com.smalltyrant.hocg.native BUILD_NUMBER=2 ./scripts/build_testflight.sh"
  exit 1
fi

cd "$PROJECT_DIR"

echo "[1/3] Archive for App Store Connect (Release)"
archive_cmd=(
  xcodebuild
  -project "$SCHEME.xcodeproj"
  -scheme "$SCHEME"
  -configuration Release
  -destination "generic/platform=iOS"
  -archivePath "$ARCHIVE_PATH"
  DEVELOPMENT_TEAM="$TEAM_ID"
  CODE_SIGN_STYLE=Automatic
  PRODUCT_BUNDLE_IDENTIFIER="$BUNDLE_ID"
  -allowProvisioningUpdates
)
if [[ -n "$MARKETING_VERSION" ]]; then
  archive_cmd+=("MARKETING_VERSION=$MARKETING_VERSION")
fi
if [[ -n "$BUILD_NUMBER" ]]; then
  archive_cmd+=("CURRENT_PROJECT_VERSION=$BUILD_NUMBER")
fi
archive_cmd+=(archive)
"${archive_cmd[@]}"

echo "[2/3] Export IPA (app-store-connect)"
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

EXPORT_OPTIONS="$OUTPUT_DIR/ExportOptions.plist"
cat > "$EXPORT_OPTIONS" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>destination</key>
  <string>export</string>
  <key>method</key>
  <string>app-store-connect</string>
  <key>signingStyle</key>
  <string>automatic</string>
  <key>teamID</key>
  <string>$TEAM_ID</string>
  <key>manageAppVersionAndBuildNumber</key>
  <false/>
  <key>stripSwiftSymbols</key>
  <true/>
  <key>testFlightInternalTestingOnly</key>
  <false/>
  <key>uploadSymbols</key>
  <true/>
</dict>
</plist>
PLIST

xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$OUTPUT_DIR" \
  -exportOptionsPlist "$EXPORT_OPTIONS" \
  -allowProvisioningUpdates

IPA_PATH="$OUTPUT_DIR/$SCHEME.ipa"
if [[ ! -f "$IPA_PATH" ]]; then
  IPA_PATH="$(find "$OUTPUT_DIR" -maxdepth 1 -name '*.ipa' -print -quit || true)"
fi
if [[ -z "$IPA_PATH" || ! -f "$IPA_PATH" ]]; then
  echo "Export failed: IPA file not found under $OUTPUT_DIR"
  exit 1
fi
echo "IPA: $IPA_PATH"

if [[ "$UPLOAD" == "1" ]]; then
  echo "[3/3] Upload to App Store Connect"
  upload_cmd=(
    xcrun altool
    --upload-app
    -f "$IPA_PATH"
    --type ios
    --show-progress
  )

  if [[ -n "$ASC_API_KEY_ID" && -n "$ASC_API_ISSUER_ID" ]]; then
    upload_cmd+=(--apiKey "$ASC_API_KEY_ID" --apiIssuer "$ASC_API_ISSUER_ID")
  else
    if [[ -z "$ASC_APPLE_ID" || -z "$ASC_APP_PASSWORD" ]]; then
      echo "UPLOAD=1 requires auth settings."
      echo "Use API key auth:"
      echo "  ASC_API_KEY_ID=<KEY_ID> ASC_API_ISSUER_ID=<ISSUER_ID>"
      echo "or Apple ID auth:"
      echo "  ASC_APPLE_ID=<APPLE_ID_EMAIL> ASC_APP_PASSWORD=<APP_SPECIFIC_PASSWORD>"
      exit 1
    fi
    upload_cmd+=(-u "$ASC_APPLE_ID" -p "$ASC_APP_PASSWORD")
    if [[ -n "$ASC_PROVIDER_PUBLIC_ID" ]]; then
      upload_cmd+=(--provider-public-id "$ASC_PROVIDER_PUBLIC_ID")
    fi
  fi

  "${upload_cmd[@]}"
else
  echo "[3/3] Skip upload (set UPLOAD=1 to upload to TestFlight)"
fi
