# 변경 사항 요약 (KR)

## 변경된 파일
- AGENTS.md
- app/ui.py
- app/services/db.py
- app/services/pipeline.py
- tools/hocg_refine_update.py
- tools/hocg_tool2.py
- tools/namu_sync.py
- tools/export_ko_template.py
- tools/import_ko_from_csv.py
- tools/export_ko_tags_template.py
- tools/import_ko_tags.py
- tools/migrate_tags_split.py
- tools/export_ko_all_template.py
- tools/import_ko_all_from_csv.py
- data/ko_input.csv
- docs/changes_kr.md

## 추가된 기능
- 카드 상세 화면에서 일본어/한국어 본문을 함께 표시
- 나무위키 검색/수집을 통해 한국어 내용 DB 적재 스크립트 추가
- 카드 번호 기반 CSV 템플릿 export 및 CSV 기반 한국어 입력 반영 스크립트 추가
- 태그 한/일 분리를 위한 마이그레이션 및 ko 태그 CSV export/import 스크립트 추가
- 카드 번역 + 태그 번역을 하나의 CSV로 통합 export/import 지원
- 정제(refine) 병렬 처리 옵션(--jobs) 추가 및 배치 업데이트로 성능 개선

## 변경된 기능
- 크롤링/정제 파이프라인 호출 방식 단순화 (기본값 사용)
- 상세 화면에서 색(色) 섹션 및 バトンタッチ 섹션 표시 제거
- 상세 본문 표시 개선 (カードタイプ의 홀로멤 제거, Bloomレベル 한 줄 표시, HP 200 강조)
- Bloomレベル/HP를 태그(칩) 스타일로 강조 표시
- 태그 검색이 ja/ko 태그 모두를 대상으로 동작하도록 개선
- 모바일(앱) 레이아웃 재배치: 검색 아래 목록 → 이미지 → 본문 순서

## 제거된 기능
- UI 로딩바/ETA 표시 제거

## 비고
- data/ko_input.csv는 수동 입력용 템플릿 파일입니다.
