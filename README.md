# hololive OCG Helper

홀로라이브 OCG 카드 정보를 빠르게 검색하고 카드 효과를 확인할 수 있는 멀티 플랫폼 앱입니다.

## 현재 상태

- 지원 플랫폼: **Android / iOS / Windows / macOS**
- 데이터 소스: **SQLite (`app/assets/hololive_ocg.sqlite`)**
- 로컬 반복 검증 기준선: `python3 scripts/run_quality_loop.py --max-attempts 1` **PASS** 기준으로 작업
- 배포/업데이트:
  - DB 릴리즈: `.github/workflows/publish-db.yml`
  - Android 빌드: `.github/workflows/build-android.yml`
  - iOS 빌드: `.github/workflows/build-ios.yml`

## 개요

- 카드 번호 기반 검색
- 카드 이미지 및 효과 텍스트 제공
- 로컬 DB 기반 빠른 조회
- JSON / 이미지 형태 덱 공유 지원

## 문제와 해결

### Problem
- 카드 효과가 텍스트 형태로 제공되어 검색이 어려움
- 공식 데이터 접근이 제한적
- 반복적인 카드 확인 과정이 비효율적

### Solution
- 크롤링을 통해 카드 데이터를 수집
- 불규칙한 텍스트 데이터를 정제하여 DB 저장
- 네이티브 앱으로 구현하여 사용자 경험 개선
- GitHub 기반 DB 업데이트 방식으로 서버 없이 운영

## 기술 스택

- Python (크롤링 / 데이터 처리 / 데스크톱/Flet UI)
- Playwright (크롤링 안정성 확보)
- SQLite (로컬 DB)
- Kotlin + Jetpack Compose (Android)
- Swift + SwiftUI (iOS)

## 아키텍처

크롤링 → 데이터 정제 → SQLite 저장 → 앱 조회 → GitHub 릴리즈로 DB/빌드 배포

## 레포 맵

| 경로 | 역할 |
|---|---|
| `app/` | Python/Flet 앱, 공용 자산, bundled DB |
| `app/assets/hololive_ocg.sqlite` | 앱에 포함되는 기준 DB |
| `mobile/android/native/` | Android 런타임 로직 |
| `mobile/android/native-app/` | Android 빌드/Gradle/Manifest |
| `mobile/ios/native/` | iOS 런타임 로직 |
| `mobile/ios/native-app/` | iOS Xcodegen/project 설정 |
| `tools/` | 데이터 정제/가져오기/검증 스크립트 |
| `scripts/` | 반복 검증, 빌드 게이트, 품질 루프 |
| `.github/workflows/` | CI/CD 및 릴리즈 자동화 |
| `docs/` | 운영/배포/보조 문서 |

## 기능

- 카드 번호 검색
- 카드 이미지 및 효과 확인
- 덱 저장 (앱 내부)
- JSON 기반 덱 공유
- 이미지 형태 내보내기

## 설치

### Android
- GitHub Releases의 APK 설치

### iOS
- TestFlight 참여
- https://testflight.apple.com/join/xfQ2hPbT

## 데이터 작업

### DB → CSV
```bash
python3 tools/export_db_to_csv.py --db app/assets/hololive_ocg.sqlite --out-dir data/csv_dump
```

### CSV → DB
```bash
python3 tools/import_db_from_csv.py --csv-dir data/csv_dump --db data/hololive_from_csv.sqlite --overwrite-db
```

## 반복 검증 명령

### 가장 먼저 돌릴 것
```bash
python3 scripts/run_quality_loop.py --max-attempts 1
```

### 개별 검증
```bash
python3 scripts/python_syntax_check.py
python3 tools/test_db_download.py
python3 tools/test_db_download_integration.py
python3 scripts/mobile_build_gate.py --target ios
```

### 실패 분석
```bash
python3 scripts/analyze_ci_failures.py --log-dir <dir>
```

## 운영 문서

- OpenCode 운영 규칙: `CLAUDE.md`
- 일반 에이전트용 fallback 가이드: `AGENTS.md`
- 병렬 작업 운영 가이드: `docs/opencode_parallel.md`
- Discord / cmux 브리지: `docs/discord_cmux_bot.md`
- Discord / cmux 서버 배포: `deploy/README.md`
- 품질 루프 문서: `docs/parallel_agent_loop.md`
- GitHub Secrets 설정: `.github/SECRETS_SETUP.md`

## 환경 변수 / 시크릿

- 이 저장소는 기본 로컬 실행에 `.env`를 전제하지 않습니다.
- Discord 브리지를 쓰려면 `DISCORD_BOT_TOKEN`, `OPENAI_API_KEY`, `DISCORD_ALLOWED_USER_IDS` 등을 추가로 설정하세요.
- 특정 채널로만 제한하려면 `DISCORD_ALLOWED_CHANNEL_IDS`를 함께 설정하세요.
- CI/CD와 스토어 배포용 시크릿은 `.github/SECRETS_SETUP.md`를 기준 문서로 사용합니다.
- `.p8`, `.jks`, `.keystore`, `keystore.properties`, `.env*` 같은 파일은 커밋하면 안 됩니다.

## 중요한 작업 규칙

- `app/build/**` 같은 generated output은 **git에 다시 추가하지 않습니다**
- iOS 빌드 설정의 기준은 `mobile/ios/native-app/project.yml` 이며, Xcode 프로젝트는 필요 시 **xcodegen으로 재생성**합니다
- DB 업데이트 로직은 GitHub release asset의 **SHA-256 digest 검증**을 통과해야 합니다
- 최소 변경(diff) 원칙을 유지합니다

## Why No Server?

- 정적인 카드 데이터 특성상 서버 필요성 낮음
- GitHub 기반 DB 배포로 유지 비용 최소화
- 앱에서 직접 DB 업데이트 가능

## Challenges

- 카드 효과 텍스트 구조가 일정하지 않아 정제 작업이 어려움
- 크롤링 대상 사이트의 DOM 변경 대응 필요

## Future Work

- 카드 이미지 선택 기능 추가
- 자동 DB 업데이트 개선
- 테스트 자동화 강화
