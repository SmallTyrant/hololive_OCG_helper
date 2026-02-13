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
