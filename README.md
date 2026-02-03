# hololive_OCG_helper
PC-only Flet helper app.


아직은 일본어만 지원합니다.

## 한국어 효과 텍스트 적재 (NamuWiki/Google Sheets)
NamuWiki는 전용 벌크 스크립트로 자동 탐색해 효과 텍스트가 있는 페이지만 적재합니다.
Google Sheets는 별도 스크립트로 CSV를 가져옵니다. DB 스키마 변경 없이 기존 `prints`와 카드 번호로 매칭됩니다.

NamuWiki 벌크 예시:
```
python tools/namuwiki_ko_bulk_import.py --db data/hololive_ocg.sqlite
```

NamuWiki 벌크 (옵션 예시):
```
python tools/namuwiki_ko_bulk_import.py --db data/hololive_ocg.sqlite --dry-run
python tools/namuwiki_ko_bulk_import.py --db data/hololive_ocg.sqlite --overwrite
```

Google Sheets 예시(공개 시트):
```
python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --sheet-url "https://docs.google.com/spreadsheets/d/<id>/edit#gid=0"
```

앱의 DB 갱신 시 자동으로 불러오려면 환경변수를 설정하세요:
```
HOCG_KO_SHEET_URL="https://docs.google.com/spreadsheets/d/<id>/edit#gid=0"
HOCG_KO_SHEET_GID="0"
```
