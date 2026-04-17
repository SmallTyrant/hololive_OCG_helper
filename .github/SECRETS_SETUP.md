# GitHub Secrets 설정 가이드

이 문서는 iOS 및 Android 자동 빌드를 위해 필요한 GitHub Secrets를 설정하는 방법을 안내합니다.

## 필수 Secrets

### iOS (TestFlight 업로드)

#### 1. `IOS_TEAM_ID`
- **설명**: Apple Developer Team ID
- **획득 방법**:
  1. [Apple Developer](https://developer.apple.com/account) 로그인
  2. Membership 페이지에서 Team ID 확인 (10자리 영숫자)
- **예시**: `ABCD123456`

#### 2. `APP_STORE_CONNECT_KEY_ID`
- **설명**: App Store Connect API Key ID
- **획득 방법**:
  1. [App Store Connect](https://appstoreconnect.apple.com) 로그인
  2. Users and Access → Keys → App Store Connect API
  3. "+" 버튼으로 새 키 생성 (Admin 또는 App Manager 권한)
  4. Key ID 복사 (예: `ABC123XYZ`)

#### 3. `APP_STORE_CONNECT_ISSUER_ID`
- **설명**: App Store Connect Issuer ID
- **획득 방법**:
  1. App Store Connect API Keys 페이지에서 확인
  2. Issuer ID는 UUID 형식 (예: `12345678-1234-1234-1234-123456789012`)

#### 4. `APP_STORE_CONNECT_API_KEY`
- **설명**: App Store Connect API Private Key (.p8 파일 내용)
- **획득 방법**:
  1. API Key 생성 시 다운로드한 `.p8` 파일 열기
  2. 전체 내용을 하나의 repository secret 값으로 복사
- **예시 값 형식**: `App Store Connect에서 다운로드한 .p8 파일의 전체 내용을 그대로 붙여넣기`

### Android (GitHub Release)

#### 5. `ANDROID_KEYSTORE_BASE64`
- **설명**: Android 키스토어 파일을 Base64로 인코딩한 문자열
- **생성 방법**:
  1. 키스토어가 없다면 생성:
     ```bash
     keytool -genkeypair -v \
       -keystore hocg-release.jks \
       -alias hocg \
       -keyalg RSA -keysize 2048 -validity 10000 \
       -storepass YOUR_STORE_PASSWORD \
       -keypass YOUR_KEY_PASSWORD \
       -dname "CN=Hololive OCG Helper, OU=Dev, O=Your Org, L=City, ST=State, C=KR"
     ```
  2. Base64 인코딩:
     ```bash
     base64 -i hocg-release.jks | pbcopy  # macOS
     # 또는
     base64 hocg-release.jks > keystore.b64  # Linux
     ```
  3. 출력된 Base64 문자열을 Secret에 저장

#### 6. `ANDROID_KEYSTORE_PASSWORD`
- **설명**: 키스토어 비밀번호
- **예시**: 키스토어 생성 시 설정한 storePassword

#### 7. `ANDROID_KEY_ALIAS`
- **설명**: 키 별칭
- **예시**: `hocg` (키스토어 생성 시 -alias 옵션 값)

#### 8. `ANDROID_KEY_PASSWORD`
- **설명**: 키 비밀번호
- **예시**: 키스토어 생성 시 설정한 keyPassword

## Secrets 설정 방법

1. GitHub 저장소 페이지로 이동
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** 클릭
4. Name과 Value 입력 후 **Add secret** 클릭
5. 위의 모든 Secrets 반복 설정

## 선택 사항

### Android Debug 빌드만 사용하는 경우
Android Secrets (5-8번)을 설정하지 않으면 자동으로 Debug APK가 빌드됩니다.
Debug APK는 서명이 필요 없지만, Google Play Store에 업로드할 수 없습니다.

### iOS 로컬 빌드만 사용하는 경우
iOS Secrets를 설정하지 않고 로컬에서만 빌드하려면:
```bash
cd mobile/ios/native-app
DEVELOPMENT_TEAM=YOUR_TEAM_ID ./ship.sh
```

## SDK 버전 요구사항

### iOS/iPadOS 앱

Apple은 **2026년 4월 28일**부터 다음을 요구합니다:
- **필수 SDK**: iOS 26 SDK 이상 (Xcode 26+)
- **현재 설정**: 워크플로우는 자동으로 Xcode 26.3을 선택하도록 설정됨

#### SDK vs Deployment Target

- **SDK 버전**: 앱을 빌드하는 데 사용되는 도구 버전 (Xcode에 포함)
- **Deployment Target**: 앱이 지원하는 최소 iOS 버전 (현재 16.0)

⚠️ **중요**: iOS 26 SDK로 빌드해도 deployment target은 iOS 16.0으로 유지되므로, 기존 사용자에게 영향을 주지 않습니다.

#### 워크플로우 검증

GitHub Actions 워크플로우는 자동으로 다음을 확인합니다:
1. Xcode 26.3 선택
2. iOS 26 SDK 존재 여부 확인
3. SDK 버전이 요구사항을 충족하지 않으면 빌드 실패

## 워크플로우 트리거

### 자동 트리거
다음 경로의 파일이 변경되면 자동으로 빌드가 실행됩니다:
- iOS: `mobile/ios/native-app/**`, `mobile/ios/native/**`, `app/assets/hololive_ocg.sqlite`
- Android: `mobile/android/native-app/**`, `mobile/android/native/**`, `app/assets/hololive_ocg.sqlite`

### 수동 트리거
GitHub Actions 페이지에서 "Run workflow" 버튼으로 수동 실행 가능합니다.

## 빌드 결과 확인

### iOS
- **TestFlight**: App Store Connect → TestFlight 탭에서 확인 (처리에 5-10분 소요)
- **아티팩트**: GitHub Actions 페이지에서 `ios-ipa-{빌드번호}` 다운로드 가능

### Android
- **GitHub Release**: 저장소의 Releases 페이지에서 `android-v1.0.{빌드번호}` 태그 확인
- **아티팩트**: GitHub Actions 페이지에서 `android-apk-{빌드번호}` 다운로드 가능

## 문제 해결

### iOS 빌드 실패
- Team ID가 올바른지 확인
- App Store Connect API Key가 유효한지 확인 (만료되지 않았는지)
- Xcode 프로젝트의 Bundle Identifier가 App Store Connect에 등록되어 있는지 확인

### Android 빌드 실패
- 키스토어 Base64 인코딩이 올바른지 확인
- 비밀번호와 별칭이 일치하는지 확인
- JDK 버전이 17인지 확인

## 보안 주의사항

⚠️ **절대 커밋하지 말 것**:
- `.p8` 파일 (iOS API Key)
- `.jks` 파일 (Android 키스토어)
- `keystore.properties` 파일
- 비밀번호나 API 키가 포함된 파일

이러한 파일들은 `.gitignore`에 추가되어 있어야 합니다.
