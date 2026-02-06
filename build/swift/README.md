# iOS Swift Native 리팩토링 베이스

요청하신 대로 iOS 코드를 Swift/SwiftUI 네이티브 구조로 새로 작성해 `build/swift`에 배치했습니다.

## 포함 내용
- SwiftUI 앱 엔트리/화면 구조
- SQLite 읽기 전용 데이터 접근 계층 (`SQLite3` 직접 사용)
- 카드 검색/상세 조회 MVVM
- XcodeGen용 `project.yml`

## 직접 넣어야 하는 리소스
- DB 파일: `HololiveOCGHelper/Resources/hololive_ocg.sqlite`
- 앱 아이콘: `HololiveOCGHelper/Resources/Assets.xcassets/AppIcon.appiconset`

> 저장소 정책상 DB/이미지는 커밋하지 않았습니다.

## 빌드 방법 (macOS)
1. XcodeGen 설치
   ```bash
   brew install xcodegen
   ```
2. 프로젝트 생성
   ```bash
   cd build/swift
   xcodegen generate
   ```
3. Xcode에서 `HololiveOCGHelper.xcodeproj` 열기 후 빌드

또는 CLI:
```bash
xcodebuild -project HololiveOCGHelper.xcodeproj -scheme HololiveOCGHelper -destination 'platform=iOS Simulator,name=iPhone 15' build
```
