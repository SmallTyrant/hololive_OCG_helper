# iOS Native App Project

실행 가능한 Xcode 프로젝트입니다.
실제 앱 로직은 `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative`를 직접 참조합니다.

## 프로젝트 재생성
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native-app
xcodegen generate
```

## 빌드
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native-app
xcodebuild -project HocgNative.xcodeproj -scheme HocgNative -destination 'generic/platform=iOS Simulator' build
```

## 사이드로드(서명 + IPA 생성)
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native-app
TEAM_ID=<YOUR_TEAM_ID> BUNDLE_ID=com.smalltyrant.hocg.native ./scripts/build_sideload.sh
```

- IPA 출력 위치: `build/ipa_sideload/HocgNative-signed.ipa`
- 실기기 자동 설치까지 하려면 `DEVICE_ID`를 같이 지정:
```bash
TEAM_ID=<YOUR_TEAM_ID> BUNDLE_ID=com.smalltyrant.hocg.native DEVICE_ID=<UDID> ./scripts/build_sideload.sh
```

## TestFlight(App Store Connect)용 IPA 생성
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native-app
TEAM_ID=<YOUR_TEAM_ID> \
BUNDLE_ID=com.smalltyrant.hocg.native \
BUILD_NUMBER=<NEW_BUILD_NUMBER> \
./scripts/build_testflight.sh
```

- IPA 출력 위치: `build/ipa_testflight/HocgNative.ipa`
- 위 IPA는 App Store Connect 업로드 가능한 서명(`get-task-allow=false`)으로 export됩니다.
- 같은 버전 업로드 시 빌드 번호가 중복되면 거절되므로 `BUILD_NUMBER`를 증가시키세요.

### TestFlight 자동 업로드(선택)
```bash
TEAM_ID=<YOUR_TEAM_ID> \
BUNDLE_ID=com.smalltyrant.hocg.native \
BUILD_NUMBER=<NEW_BUILD_NUMBER> \
UPLOAD=1 \
ASC_API_KEY_ID=<KEY_ID> \
ASC_API_ISSUER_ID=<ISSUER_ID> \
./scripts/build_testflight.sh
```

또는 Apple ID 인증:
```bash
TEAM_ID=<YOUR_TEAM_ID> \
BUNDLE_ID=com.smalltyrant.hocg.native \
BUILD_NUMBER=<NEW_BUILD_NUMBER> \
UPLOAD=1 \
ASC_APPLE_ID=<APPLE_ID_EMAIL> \
ASC_APP_PASSWORD=<APP_SPECIFIC_PASSWORD> \
./scripts/build_testflight.sh
```

### 외부 테스터 승인 후 자동 배포
`fastlane`이 설치되어 있으면 업로드 후 외부 그룹 배정 + Beta Review 제출까지 자동으로 처리할 수 있습니다.

```bash
TEAM_ID=<YOUR_TEAM_ID> \
BUNDLE_ID=com.smalltyrant.hocg.native \
BUILD_NUMBER=<NEW_BUILD_NUMBER> \
UPLOAD=1 \
AUTO_EXTERNAL=1 \
EXTERNAL_GROUPS="Public Testers" \
ASC_APPLE_ID=<APPLE_ID_EMAIL> \
ASC_APP_PASSWORD=<APP_SPECIFIC_PASSWORD> \
TESTFLIGHT_WHATS_NEW="버그 수정 및 검색 개선" \
./scripts/build_testflight.sh
```

- `EXTERNAL_GROUPS`는 App Store Connect의 외부 테스터 그룹 이름(여러 개면 콤마 구분).
- 이 모드는 `fastlane pilot`을 사용하므로 `gem install fastlane`이 필요합니다.

API Key 인증으로도 실행 가능:

```bash
TEAM_ID=<YOUR_TEAM_ID> \
BUNDLE_ID=com.smalltyrant.hocg.native \
BUILD_NUMBER=<NEW_BUILD_NUMBER> \
UPLOAD=1 \
AUTO_EXTERNAL=1 \
EXTERNAL_GROUPS="Public Testers" \
ASC_API_KEY_ID=<KEY_ID> \
ASC_API_ISSUER_ID=<ISSUER_ID> \
ASC_API_KEY_FILE=/Users/<YOU>/Desktop/AuthKey_<KEY_ID>.p8 \
TESTFLIGHT_WHATS_NEW="버그 수정" \
./scripts/build_testflight.sh
```

## DB 번들 처리
- 빌드 단계에서 `data/hololive_ocg.sqlite`를 앱 번들 `Data/hololive_ocg.sqlite`로 복사합니다.
- 저장소 정책상 DB 파일은 커밋하지 않습니다.
