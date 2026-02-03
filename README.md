# hololive_OCG_helper
PC-only Flet helper app.


아직은 일본어만 지원합니다.

## 한국어 효과 텍스트 적재 (NamuWiki/Google Sheets)
`tools/namuwiki_ko_import.py`로 NamuWiki 카드 목록 테이블(세로 표 포함) 또는 Google Sheets CSV에서 카드 번호/효과를 추출해
`card_texts_ko`에 적재할 수 있습니다. DB 스키마 변경 없이 기존 `prints`와 카드 번호로 매칭됩니다.

예시(단일 페이지):
```
python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --page "홀로라이브 오피셜 카드 게임/옐"
```

예시(여러 페이지):
```
python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --page "홀로라이브 오피셜 카드 게임/제한 카드" --page "홀로라이브 오피셜 카드 게임/프로모션 카드" --page "홀로라이브 오피셜 카드 게임/옐"
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
