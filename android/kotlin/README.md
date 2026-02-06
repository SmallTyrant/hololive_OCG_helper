# Android Kotlin Native 프로젝트

`android/kotlin` 폴더에서 바로 빌드 가능한 Android 네이티브(Kotlin + Compose) 프로젝트입니다.

## 핵심 사항
- Python/Flet 코드와 분리된 **순수 Kotlin 네이티브 앱**
- 빌드 시 루트의 `data/hololive_ocg.sqlite`를 자동으로 `assets/hololive_ocg.sqlite`로 복사 시도
- DB 파일이 없어도 빌드는 가능하며, 앱에서 안내 문구를 표시
- 저장소 정책에 따라 DB 파일은 커밋하지 않음

## 빌드
```bash
cd android/kotlin
./gradlew assembleDebug
```

## DB 포함 방식
1. 루트 경로에 DB 파일 준비
   - `data/hololive_ocg.sqlite`
2. 아래 빌드 명령 실행
   - `./gradlew assembleDebug`
3. `preBuild`에서 DB를 `app/src/main/assets/hololive_ocg.sqlite`로 동기화

> DB/이미지는 저장소에 커밋하지 않도록 `.gitignore`에 제외 처리되어 있습니다.
