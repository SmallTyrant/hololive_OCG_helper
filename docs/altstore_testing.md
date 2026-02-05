# AltStore 테스트 배포 가이드

이 문서는 iOS 테스트용 IPA를 AltStore로 사이드로딩하는 방법을 정리합니다.

## 개발자(빌드 담당)

1) iOS IPA 빌드 준비
   - DB 파일을 `data/hololive_ocg.sqlite` 경로에 둡니다.
   - iOS 앱 아이콘으로 사용할 이미지를 `assets/icon_ios.png` (또는 공통 아이콘은 `assets/icon.png`)로 둡니다.

2) iOS IPA 빌드
```bash
flet build ipa
```

3) 생성된 `.ipa` 파일을 테스터에게 전달

## 테스터

1) AltServer 설치 (macOS 또는 Windows)
2) iPhone을 PC/Mac에 연결한 뒤 AltStore 설치
3) AltStore에서 `.ipa` 파일 선택 후 설치
4) 무료 Apple ID 사용 시 7일마다 재서명 필요

## 주의사항

- AltStore는 테스터의 Apple ID로 재서명합니다.
- 재서명하려면 AltServer가 설치된 PC/Mac에 주기적으로 연결해야 합니다.
- 설치 후 iOS에서 개발자 앱 신뢰가 필요할 수 있습니다.
