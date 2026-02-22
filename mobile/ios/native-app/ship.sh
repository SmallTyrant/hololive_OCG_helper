#!/usr/bin/env bash
set -e

# Required env vars:
#   DEVELOPMENT_TEAM  – Apple Developer Team ID
: "${DEVELOPMENT_TEAM:?Set DEVELOPMENT_TEAM env var}"

SCHEME="HocgNative"
PROJECT="HocgNative.xcodeproj"
CONFIG="Release"

mkdir -p build

echo "Archive..."
xcodebuild \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration "$CONFIG" \
  -archivePath build/$SCHEME.xcarchive \
  -destination "generic/platform=iOS" \
  DEVELOPMENT_TEAM="$DEVELOPMENT_TEAM" \
  CODE_SIGN_STYLE=Automatic \
  -allowProvisioningUpdates \
  archive

echo "Export + Upload to TestFlight..."

cat > build/ExportOptions.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store-connect</string>
    <key>teamID</key>
    <string>${DEVELOPMENT_TEAM}</string>
    <key>destination</key>
    <string>upload</string>
    <key>signingStyle</key>
    <string>automatic</string>
    <key>uploadSymbols</key>
    <true/>
</dict>
</plist>
EOF

xcodebuild -exportArchive \
  -archivePath build/$SCHEME.xcarchive \
  -exportOptionsPlist build/ExportOptions.plist \
  -exportPath build/ipa_testflight \
  -allowProvisioningUpdates

echo "Done. Check App Store Connect for processing status."
