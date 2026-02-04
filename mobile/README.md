# Mobile app 방향성

이 폴더는 **Android(Kotlin)** 및 **iOS(Swift)** 네이티브 앱을 제작하기 위한
공통 가이드와 플랫폼별 준비 사항을 정리합니다.

## 목표
- Android는 Kotlin + Jetpack Compose로 구현
- iOS는 Swift + SwiftUI로 구현
- 데이터는 현재 `data/hololive_ocg.sqlite`를 **read-only**로 내장하고,
  앱 업데이트 시 교체하는 방식을 기본으로 합니다.
- 기존 DB 스키마는 변경하지 않습니다.

## 공통 데이터 계약 (요약)
- DB 파일: `data/hololive_ocg.sqlite`
- 주요 테이블: `cards`, `prints`, `card_texts_ko` 등 (스키마 변경 금지)
- 앱에서는 읽기 전용으로 접근하며, 앱 번들 내 DB를 복사해 사용합니다.

## 다음 단계
1. Android/iOS 프로젝트 생성 후, 앱 번들에 DB 포함
2. 각 플랫폼에 맞는 데이터 접근 계층 구현
3. 기존 PC 앱과 UI/UX 통일성 확보

플랫폼별 상세 안내는 아래 문서를 참고하세요.
- [Android 안내](./android/README.md)
- [iOS 안내](./ios/README.md)
