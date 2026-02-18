# Android Native App Project

실행 가능한 Android Studio/Gradle 프로젝트입니다.
실제 앱 로직은 `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native/src/main/java`를 소스셋으로 직접 참조합니다.

## 빌드
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native-app
cat > local.properties <<'EOP'
sdk.dir=/Users/perlihite/Library/Android/sdk
EOP
JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew assembleDebug
```

## DB 에셋 처리
- 빌드 시 `data/hololive_ocg.sqlite`가 있으면 `app/src/main/assets/hololive_ocg.sqlite`로 자동 복사됩니다.
- 저장소 정책상 DB 파일은 커밋하지 않습니다.

## APK 산출물
- `app/build/outputs/apk/debug/app-debug.apk`

## Release APK 서명
1. 키스토어 생성 (최초 1회):
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native-app
keytool -genkeypair -v \
  -keystore hocg-release.jks \
  -alias hocg \
  -keyalg RSA -keysize 2048 -validity 10000
```

2. `keystore.properties` 생성:
```properties
storeFile=hocg-release.jks
storePassword=YOUR_STORE_PASSWORD
keyAlias=hocg
keyPassword=YOUR_KEY_PASSWORD
```

3. 서명된 release APK 빌드:
```bash
cd /Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native-app
JAVA_HOME=$(/usr/libexec/java_home -v 17) ./gradlew clean assembleRelease
```

4. 산출물:
- `app/build/outputs/apk/release/app-release.apk`

참고:
- `keystore.properties` 또는 `ANDROID_KEYSTORE_PATH/ANDROID_KEYSTORE_PASSWORD/ANDROID_KEY_ALIAS/ANDROID_KEY_PASSWORD` 환경변수가 있으면 release 서명이 적용됩니다.
