# Android Native (Kotlin) Implementation

`app/ui.py` Flet 동작을 Android 네이티브로 1:1에 가깝게 옮긴 레퍼런스 코드입니다.
Python 런타임/모듈 의존 없이 Kotlin 코드만으로 동작하도록 구성했습니다.

## 포함 기능
- 실시간 검색 (`partial` / `exact` 모드)
- 결과 리스트 + 선택 상세
- 모바일/와이드 반응형 레이아웃 (와이드에서 3패널: 목록/이미지/효과)
- 카드 이미지 캐시(`filesDir/hOCG_H/images/*.png`) 및 다운로드
- DB 무결성 체크(prints 테이블/행 수)
- 메뉴에서 `DB 수동갱신` (GitHub Releases 최신 DB 다운로드)
- 로컬 DB 날짜 vs GitHub DB 날짜 비교 후 업데이트 다이얼로그
- 상세 텍스트 섹션 칩 렌더링

## 코드 위치
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native/src/main/java/com/smalltyrant/hocgh/MainActivity.kt`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native/src/main/java/com/smalltyrant/hocgh/ui/HocgScreen.kt`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native/src/main/java/com/smalltyrant/hocgh/ui/HocgViewModel.kt`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native/src/main/java/com/smalltyrant/hocgh/data/*`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/android/native/src/main/java/com/smalltyrant/hocgh/model/Models.kt`

## Gradle 의존성
```kotlin
implementation("androidx.activity:activity-compose:1.9.3")
implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
implementation("androidx.compose.material3:material3")
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
implementation("com.squareup.okhttp3:okhttp:4.12.0")
implementation("io.coil-kt:coil-compose:2.7.0")
```

## 에셋 준비
- 앱 `assets/hololive_ocg.sqlite` 포함
- 첫 실행 시 `filesDir/hOCG_H/hololive_ocg.sqlite`로 자동 복사

## 참고
- DB/이미지 파일은 저장소 정책상 커밋하지 않습니다.
- 현재 디렉토리는 "복사해서 프로젝트에 붙이는" 소스 템플릿입니다.
