# iOS Native (Swift) Implementation

`app/ui.py` Flet 동작을 iOS 네이티브로 1:1에 가깝게 옮긴 SwiftUI 레퍼런스 코드입니다.
Python 런타임/모듈 의존 없이 Swift 코드만으로 동작하도록 구성했습니다.

## 포함 기능
- 실시간 검색 (`partial` / `exact` 모드)
- 결과 리스트 + 선택 상세
- 모바일/와이드 반응형 레이아웃 (와이드에서 3패널: 목록/이미지/효과)
- 카드 이미지 캐시(`Documents/hOCG_H/images/*.png`) 및 다운로드
- DB 무결성 체크(prints 테이블/행 수)
- 메뉴에서 `DB 수동갱신` (GitHub Releases 최신 DB 다운로드)
- 로컬 DB 날짜 vs GitHub DB 날짜 비교 후 업데이트 다이얼로그
- 상세 텍스트 섹션 칩 렌더링

## 코드 위치
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/HocgNativeApp.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/ContentView.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/HocgViewModel.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/DatabaseRepository.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/ImageRepository.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/UpdateRepository.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/SQLiteHelpers.swift`
- `/Users/perlihite/Desktop/hololive_OCG_helper/mobile/ios/native/Sources/HocgNative/AppPaths.swift`

## Xcode 설정
1. iOS App(SwiftUI) 프로젝트 생성
2. 위 파일들을 타깃에 추가
3. `Build Settings > Other Linker Flags`에 `-lsqlite3` 추가
4. 앱 번들에 `hololive_ocg.sqlite` 파일 포함

## 참고
- 첫 실행 시 번들 DB를 `Documents/hOCG_H/hololive_ocg.sqlite`로 복사합니다.
- DB/이미지 파일은 저장소 정책상 커밋하지 않습니다.
