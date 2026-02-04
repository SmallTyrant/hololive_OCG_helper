# hololive_OCG_helper
PC-only Flet helper app.


아직은 일본어만 지원합니다.

## 모바일 앱 제작 안내
Android(Kotlin) / iOS(Swift) 앱 제작을 위한 가이드는 `mobile/` 폴더를 참고하세요.

## 한국어 효과 텍스트 적재 (NamuWiki/Google Sheets)
`tools/namuwiki_ko_import.py`로 NamuWiki 카드 목록 테이블 또는 Google Sheets CSV에서 카드 번호/효과를 추출해
`card_texts_ko`에 적재할 수 있습니다. DB 스키마 변경 없이 기존 `prints`와 카드 번호로 매칭됩니다.

예시:
```
python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --page "hololive OCG/카드 목록"
```

카드 번호로 NamuWiki 검색까지 포함하려면 `--search-card-numbers`를 추가하세요:
```
python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --page "hololive OCG/카드 목록" --search-card-numbers
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
