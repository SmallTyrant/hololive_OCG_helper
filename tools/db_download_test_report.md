# DB 다운로드 기능 테스트 리포트

**테스트 일시**: 2026-03-11  
**테스트 대상**: iOS 및 Android UpdateRepository 로직

---

## 테스트 개요

iOS와 Android 앱의 DB 다운로드 기능이 올바르게 작동하는지 검증했습니다.

### 수정된 코드

#### iOS (`mobile/ios/native/Sources/HocgNative/UpdateRepository.swift`)

```swift
private let githubRepo = "SmallTyrant/hololive_OCG_helper"
private let dbReleaseTag = "DB"
private let dbReleaseAPI = URL(string: "https://api.github.com/repos/\(githubRepo)/releases/tags/\(dbReleaseTag)")!
private let dbDirectURL = URL(string: "https://github.com/\(githubRepo)/releases/download/\(dbReleaseTag)/hololive_ocg.sqlite")!
```

#### Android (`mobile/android/native/src/main/java/com/smalltyrant/hocgh/data/UpdateRepository.kt`)

```kotlin
private const val GITHUB_REPO = "SmallTyrant/hololive_OCG_helper"
private const val DB_RELEASE_TAG = "DB"
private const val DB_RELEASE_API = "https://api.github.com/repos/$GITHUB_REPO/releases/tags/$DB_RELEASE_TAG"
private const val DB_DIRECT_URL = "https://github.com/$GITHUB_REPO/releases/download/$DB_RELEASE_TAG/hololive_ocg.sqlite"
```

---

## 테스트 결과

### ✅ 테스트 1: GitHub API 호출

**목적**: DB 릴리스 정보를 GitHub API에서 가져올 수 있는지 확인

**결과**:
- HTTP 상태 코드: `200 OK`
- 태그: `DB`
- Assets 개수: `1`
- DB Asset 이름: `hololive_ocg.sqlite`
- 다운로드 URL: `https://github.com/SmallTyrant/hololive_OCG_helper/releases/download/DB/hololive_ocg.sqlite`

**검증 내용**:
```json
{
  "tag_name": "DB",
  "assets": [
    {
      "name": "hololive_ocg.sqlite",
      "browser_download_url": "https://github.com/SmallTyrant/hololive_OCG_helper/releases/download/DB/hololive_ocg.sqlite",
      "updated_at": "2026-03-11T11:53:42Z"
    }
  ]
}
```

### ✅ 테스트 2: DB 파일 다운로드

**목적**: DB 파일을 실제로 다운로드하고 유효성을 검증

**결과**:
- HTTP 상태 코드: `200 OK`
- 파일 크기: `2,433,024 bytes (2.32 MB)`
- SQLite 헤더: `SQLite format 3\0` (유효함)
- 카드 프린트 개수: `1,044개`

**샘플 데이터**:
```
print_id | card_number | name_ja
---------|-------------|------------------
1        | hBP06-087   | しめじダンス
2        | hBP06-088   | ドッキリうさぎ
3        | hBP06-085   | フェイバリットパソコン
4        | hBP06-086   | 愛情いっぱい召し上がれ♪
5        | hBP06-089   | ドローイングストリーム
```

**테이블 구조**:
- `prints`: 카드 프린트 정보 (1,044 rows)
- `card_texts_ja`: 일본어 카드 텍스트
- `card_texts_ko`: 한국어 카드 텍스트
- `tags`: 태그 정보
- `meta`: 메타데이터 (앱이 다운로드 후 작성)

### ✅ 테스트 3: Fallback URL 검증

**목적**: API 실패 시 사용하는 직접 다운로드 URL이 작동하는지 확인

**결과**:
- HTTP 상태 코드: `200 OK`
- Fallback URL 접근 가능

---

## 테스트 방법

### iOS 로직 테스트

Swift 스크립트를 사용하여 iOS UpdateRepository의 로직을 재현:

```bash
swift tools/test_db_download.swift
```

**테스트 항목**:
1. GitHub API `/releases/tags/DB` 호출
2. DB 파일 다운로드 및 SQLite 헤더 검증
3. Fallback URL 접근 확인

### Android 로직 테스트

Python 스크립트를 사용하여 Android UpdateRepository의 로직을 재현:

```bash
python3 tools/test_db_download.py
```

**테스트 항목**:
1. GitHub API `/releases/tags/DB` 호출
2. DB 파일 다운로드 및 SQLite 헤더 검증
3. Fallback URL 접근 확인

---

## 결론

### ✅ 모든 테스트 통과

1. **GitHub API 호출**: DB 태그를 명시적으로 지정하여 올바른 릴리스 정보를 가져옴
2. **DB 다운로드**: 2.32MB의 유효한 SQLite 파일을 성공적으로 다운로드
3. **Fallback URL**: API 실패 시에도 직접 다운로드 URL로 접근 가능
4. **데이터 무결성**: 1,044개의 카드 프린트 데이터가 올바르게 포함됨

### 수정 전 문제점

- `/releases/latest` API 사용 시 Android 릴리스(`android-v1.0.3`)가 반환됨
- Android 릴리스에는 `hololive_ocg.sqlite` 파일이 없어 404 오류 발생
- Fallback URL도 `/releases/latest/download/...`를 사용하여 동일한 문제 발생

### 수정 후 개선사항

- `/releases/tags/DB` API로 DB 전용 릴리스를 명시적으로 지정
- Fallback URL도 `/releases/download/DB/...`로 고정
- 다른 릴리스(Android, iOS)의 영향을 받지 않음

---

## 권장 사항

### 1. 실제 디바이스 테스트

시뮬레이터/에뮬레이터 또는 실제 디바이스에서 앱을 실행하여 다음을 확인:

**iOS**:
```bash
cd mobile/ios/native-app
xcodebuild -scheme HocgNative -destination 'platform=iOS Simulator,name=iPhone 15' build
```

**Android**:
```bash
cd mobile/android/native-app
./gradlew assembleDebug
```

### 2. 네트워크 오류 처리 개선

현재 코드는 기본적인 오류 처리를 포함하고 있지만, 다음 시나리오에 대한 추가 처리 고려:

- 네트워크 연결 없음
- GitHub API 속도 제한
- 불완전한 다운로드
- 디스크 공간 부족

### 3. 사용자 피드백 개선

DB 다운로드 중 진행 상황을 사용자에게 표시:
- 다운로드 진행률 (%)
- 예상 남은 시간
- 현재 단계 (API 호출 중, 다운로드 중, 검증 중)

---

## 테스트 파일

- `tools/test_db_download.swift`: iOS 로직 테스트 스크립트
- `tools/test_db_download.py`: Android 로직 테스트 스크립트
- `/tmp/test_db.sqlite`: 다운로드된 테스트 DB 파일

## 참고

- GitHub Release: https://github.com/SmallTyrant/hololive_OCG_helper/releases/tag/DB
- DB 파일 직접 다운로드: https://github.com/SmallTyrant/hololive_OCG_helper/releases/download/DB/hololive_ocg.sqlite
