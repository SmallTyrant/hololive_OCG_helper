# hololive_OCG_helper

안드로이드, iOS, Window, MAC OS 지원하는 홀로라이브 OCG 카드효과 찾는 도우미입니다.
현재 한국어만 지원합니다.

# 사용방법
1. 각 OS에서 설치를 진행합니다. (iOS는 알트스토어나 사이드로딩을 하셔야합니다)
2. 실행 후 원하는 카드 번호를 검색하면 이미지와 카드 본문 번역된것이 보입니다.

# DB/CSV 변환
- DB -> CSV 내보내기
  - `python3 tools/export_db_to_csv.py --db data/hololive_ocg.sqlite --out-dir data/csv_dump`
- CSV -> DB 가져오기
  - `python3 tools/import_db_from_csv.py --csv-dir data/csv_dump --db data/hololive_from_csv.sqlite --overwrite-db`

`export_db_to_csv.py`는 테이블별 CSV와 `schema.sql`을 같이 생성하며,
`import_db_from_csv.py`는 `schema.sql`이 있으면 자동으로 스키마를 복원한 뒤 CSV 데이터를 넣습니다.

# TO DO
- 덱 제작 및 공유
- 카드 신규 추가시 DB업데이트
