# hololive_OCG_helper
PC-only Flet helper app.
아직은 일본어만 지원합니다.

## 한국어 효과 텍스트 적재 (NamuWiki)
`tools/namuwiki_ko_import.py`로 NamuWiki 카드 목록 테이블에서 카드 번호/효과를 추출해
`card_texts_ko`에 적재할 수 있습니다. DB 스키마 변경 없이 기존 `prints`와 카드 번호로 매칭됩니다.

예시:
```
python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --page "hololive OCG/카드 목록"
```
