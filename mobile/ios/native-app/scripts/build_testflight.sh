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
AUTO_EXTERNAL="${AUTO_EXTERNAL:-0}"
EXTERNAL_GROUPS="${EXTERNAL_GROUPS:-}"
TESTFLIGHT_WHATS_NEW="${TESTFLIGHT_WHATS_NEW:-Automated upload}"

# Upload auth options (used only when UPLOAD=1)
ASC_API_KEY_ID="${ASC_API_KEY_ID:-}"
ASC_API_ISSUER_ID="${ASC_API_ISSUER_ID:-}"
ASC_API_KEY_FILE="${ASC_API_KEY_FILE:-}"
ASC_APPLE_ID="${ASC_APPLE_ID:-}"
ASC_APP_PASSWORD="${ASC_APP_PASSWORD:-}"
ASC_PROVIDER_PUBLIC_ID="${ASC_PROVIDER_PUBLIC_ID:-}"

if [[ "$AUTO_EXTERNAL" == "1" && "$UPLOAD" != "1" ]]; then
  echo "AUTO_EXTERNAL=1 requires UPLOAD=1"
  exit 1
fi

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
  if [[ "$AUTO_EXTERNAL" == "1" ]]; then
    if ! command -v fastlane >/dev/null 2>&1; then
      echo "AUTO_EXTERNAL=1 requires fastlane. Install it first:"
      echo "  gem install fastlane"
      exit 1
    fi
    if [[ -z "$EXTERNAL_GROUPS" ]]; then
      echo "AUTO_EXTERNAL=1 requires EXTERNAL_GROUPS (comma-separated)."
      echo "Example: EXTERNAL_GROUPS='Public Testers'"
      exit 1
    fi

    pilot_cmd=(
      fastlane
      pilot
      upload
      --ipa "$IPA_PATH"
      --app_identifier "$BUNDLE_ID"
      --skip_waiting_for_build_processing false
      --distribute_external true
      --groups "$EXTERNAL_GROUPS"
      --notify_external_testers true
      --submit_beta_review true
      --changelog "$TESTFLIGHT_WHATS_NEW"
    )

    temp_api_key_json=""
    cleanup() {
      if [[ -n "$temp_api_key_json" && -f "$temp_api_key_json" ]]; then
        rm -f "$temp_api_key_json"
      fi
    }
    trap cleanup EXIT

    if [[ -n "$ASC_API_KEY_ID" && -n "$ASC_API_ISSUER_ID" ]]; then
      if [[ -z "$ASC_API_KEY_FILE" ]]; then
        ASC_API_KEY_FILE="$HOME/Desktop/AuthKey_${ASC_API_KEY_ID}.p8"
      fi
      if [[ ! -f "$ASC_API_KEY_FILE" ]]; then
        echo "AUTO_EXTERNAL API key mode requires ASC_API_KEY_FILE (or Desktop/AuthKey_<KEY_ID>.p8)."
        echo "Missing file: $ASC_API_KEY_FILE"
        exit 1
      fi
      temp_api_key_json="$(mktemp)"
      python3 - <<PY > "$temp_api_key_json"
import json
from pathlib import Path
print(json.dumps({
    "key_id": "$ASC_API_KEY_ID",
    "issuer_id": "$ASC_API_ISSUER_ID",
    "key": Path(r"$ASC_API_KEY_FILE").read_text()
}))
PY
      pilot_cmd+=(--api_key_path "$temp_api_key_json")
    else
      if [[ -z "$ASC_APPLE_ID" || -z "$ASC_APP_PASSWORD" ]]; then
        echo "AUTO_EXTERNAL=1 requires auth settings."
        echo "Use API key auth:"
        echo "  ASC_API_KEY_ID=<KEY_ID> ASC_API_ISSUER_ID=<ISSUER_ID> [ASC_API_KEY_FILE=<.p8 path>]"
        echo "or Apple ID auth:"
        echo "  ASC_APPLE_ID=<APPLE_ID_EMAIL> ASC_APP_PASSWORD=<APP_SPECIFIC_PASSWORD>"
        exit 1
      fi
      export FASTLANE_APPLE_APPLICATION_SPECIFIC_PASSWORD="$ASC_APP_PASSWORD"
      pilot_cmd+=(--username "$ASC_APPLE_ID")
    fi

    if [[ -n "$ASC_PROVIDER_PUBLIC_ID" ]]; then
      pilot_cmd+=(--itc_provider "$ASC_PROVIDER_PUBLIC_ID")
    fi
    "${pilot_cmd[@]}"
  else
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
  fi
else
  echo "[3/3] Skip upload (set UPLOAD=1 to upload to TestFlight)"
fi
