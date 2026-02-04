# iOS (Swift) 앱 제작 가이드

## 권장 스택
- Swift
- SwiftUI
- SQLite (SQLite3 또는 GRDB)
- Combine / async-await

## 프로젝트 생성
1. Xcode에서 **App (SwiftUI)** 템플릿 생성
2. 최소 iOS 16 권장

## 빌드 방법
### Xcode
1. `ios/` 프로젝트 열기
2. 타깃 디바이스 선택 후 **Run** 실행

### CLI (xcodebuild)
```bash
xcodebuild -scheme "HololiveOCG" -destination "platform=iOS Simulator,name=iPhone 15" build
```

## DB 포함
1. 현재 저장소의 `data/hololive_ocg.sqlite`를 앱 번들에 추가
2. 앱 최초 실행 시 Documents 디렉터리로 복사 후 읽기 전용으로 사용

### 예시 (SQLite3 로드)
```swift
import SQLite3

final class DatabaseProvider {
    private var db: OpaquePointer?

    func openDatabase() throws {
        let fileManager = FileManager.default
        let documentsURL = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first!
        let dbURL = documentsURL.appendingPathComponent("hololive_ocg.sqlite")

        if !fileManager.fileExists(atPath: dbURL.path) {
            if let bundledURL = Bundle.main.url(forResource: "hololive_ocg", withExtension: "sqlite") {
                try fileManager.copyItem(at: bundledURL, to: dbURL)
            }
        }

        if sqlite3_open(dbURL.path, &db) != SQLITE_OK {
            throw NSError(domain: "Database", code: 1)
        }
    }
}
```

## 기본 화면 흐름 (예시)
1. 카드 리스트 화면 (필터/검색)
2. 카드 상세 화면 (이미지/텍스트)
3. 덱 빌더 화면

## 할 일 체크리스트
- [ ] DB 접근 레이어 구성 (SQLite3/GRDB)
- [ ] 모델/쿼리 정의
- [ ] 리스트/상세 UI 구현
- [ ] 상태 관리 구조 결정 (예: ObservableObject)

## 데이터 접근 팁
- 스키마 변경 금지
- 읽기 전용 접근
- 검색/필터는 SQL에서 처리하는 것을 우선
