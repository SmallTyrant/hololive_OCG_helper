# hololive OCG Helper

홀로라이브 OCG 카드 정보를 빠르게 검색하고 카드 효과를 확인할 수 있는 멀티 플랫폼 앱입니다.

---

## 📌 Overview
- Android / iOS / Windows / macOS 지원
- 카드 번호 기반 검색
- 카드 이미지 및 효과 텍스트 제공
- 로컬 DB 기반 빠른 조회
- JSON / 이미지 형태 덱 공유 지원

---

## 🎯 Problem
- 카드 효과가 텍스트 형태로 제공되어 검색이 어려움
- 공식 데이터 접근이 제한적
- 반복적인 카드 확인 과정이 비효율적

---

## 💡 Solution
- 크롤링을 통해 카드 데이터를 수집
- 불규칙한 텍스트 데이터를 정제하여 DB 저장
- 네이티브 앱으로 구현하여 사용자 경험 개선
- GitHub 기반 DB 업데이트 방식으로 서버 없이 운영

---

## 🛠 Tech Stack
- Python (크롤링 / 데이터 처리)
- Playwright (크롤링 안정성 확보)
- SQLite (로컬 DB)
- Kotlin (Android)
- Swift (iOS)

---

## ⚙️ Architecture
크롤링 → 데이터 정제 → SQLite 저장 → 앱에서 조회

---

## 🔄 Data Pipeline
1. 크롤링 데이터 수집
2. 카드 효과 텍스트 정제
3. DB 저장
4. 앱에서 조회 및 표시
5. DB 변경 시 GitHub 통해 업데이트

---

## 📱 Features
- 카드 번호 검색
- 카드 이미지 및 효과 확인
- 덱 저장 (앱 내부)
- JSON 기반 덱 공유
- 이미지 형태 내보내기

---

## 🚀 Installation

### Android
- APK 설치

### iOS
- TestFlight 참여
https://testflight.apple.com/join/xfQ2hPbT

---

## 📊 DB / CSV 변환

### DB → CSV
python3 tools/export_db_to_csv.py --db data/hololive_ocg.sqlite --out-dir data/csv_dump

### CSV → DB
python3 tools/import_db_from_csv.py --csv-dir data/csv_dump --db data/hololive_from_csv.sqlite --overwrite-db

---

## 🤔 Why No Server?
- 정적인 카드 데이터 특성상 서버 필요성 낮음
- GitHub 기반 DB 배포로 유지 비용 최소화
- 앱에서 직접 DB 업데이트 가능

---

## 📌 Challenges
- 카드 효과 텍스트 구조가 일정하지 않아 정제 작업이 어려움
- 크롤링 대상 사이트의 DOM 변경 대응 필요

---

## 🔧 Future Work
- 카드 이미지 선택 기능 추가
- 자동 DB 업데이트 개선
- 테스트 자동화 강화

---

## ✅ Repeatable Dev Loop
- 로컬 반복 루프: `python3 scripts/run_quality_loop.py --max-attempts 3`
- CI 병렬 검증: `.github/workflows/quality-loop.yml`
- 실패 로그 분석: `python3 scripts/analyze_ci_failures.py --log-dir <dir>`
- 운영 가이드: `docs/parallel_agent_loop.md`
- OpenCode 병렬 작업 가이드: `docs/opencode_parallel.md`
