#!/usr/bin/env python3
"""
DB 한국어 텍스트 커버리지 전수검사 스크립트.

크롤링 후 반드시 실행해서 누락·오염 카드를 확인한다.
사용법: .venv/bin/python3 tools/check_ko_coverage.py [--db PATH]
"""
import argparse
import sqlite3
import sys


def check(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    errors = 0

    # 1. ko 텍스트가 없거나 비어있는 카드
    cur.execute("""
        SELECT p.card_number, p.name_ja
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        WHERE ko.print_id IS NULL OR TRIM(COALESCE(ko.effect_text,'')) = ''
        ORDER BY p.card_number
    """)
    rows = cur.fetchall()
    if rows:
        print(f"[FAIL] ko 텍스트 누락: {len(rows)}건")
        for r in rows:
            print(f"       {r['card_number']} | {r['name_ja']}")
        errors += len(rows)
    else:
        print("[OK] ko 텍스트 누락: 0건")

    # 2. 일본어에 アーツ가 있는데 한국어에 아츠가 없는 카드 (홀로멤/툴/마스코트 등)
    cur.execute("""
        SELECT p.card_number, p.name_ja, ko.effect_text
        FROM prints p
        JOIN card_texts_ja ja ON ja.print_id = p.print_id
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        WHERE ja.effect_text LIKE '%アーツ%'
          AND (ko.effect_text IS NULL OR ko.effect_text NOT LIKE '%아츠%')
        ORDER BY p.card_number
    """)
    rows = cur.fetchall()
    if rows:
        print(f"[FAIL] 아츠 누락 카드: {len(rows)}건")
        for r in rows:
            ko = (r['effect_text'] or '')[:60]
            print(f"       {r['card_number']} | {r['name_ja']} | ko={repr(ko)}")
        errors += len(rows)
    else:
        print("[OK] 아츠 누락 카드: 0건")

    # 3. 메타데이터 뭉침 패턴 (레벨 속성 HP 배턴 터치)
    cur.execute("""
        SELECT COUNT(*) FROM card_texts_ko
        WHERE effect_text LIKE '%레벨 속성%' AND effect_text LIKE '%배턴 터치%'
    """)
    count = cur.fetchone()[0]
    if count:
        print(f"[FAIL] 메타 뭉침(레벨 속성 배턴 터치) 패턴: {count}건")
        cur.execute("""
            SELECT p.card_number, k.effect_text
            FROM card_texts_ko k
            JOIN prints p ON p.print_id = k.print_id
            WHERE k.effect_text LIKE '%레벨 속성%' AND k.effect_text LIKE '%배턴 터치%'
            ORDER BY p.card_number LIMIT 5
        """)
        for r in cur.fetchall():
            print(f"       {r['card_number']} | {repr(r['effect_text'][:80])}")
        errors += count
    else:
        print("[OK] 메타 뭉침 패턴: 0건")

    # 4. 홀로멤/서포트 등 카드 타입이 name으로 오염
    bad_names = ('홀로멤', '오시 홀로멤', '서포트', '이벤트', '마스코트', '팬', '툴')
    placeholders = ','.join('?' for _ in bad_names)
    cur.execute(f"""
        SELECT p.card_number, k.name
        FROM card_texts_ko k
        JOIN prints p ON p.print_id = k.print_id
        WHERE LOWER(TRIM(k.name)) IN ({placeholders})
        ORDER BY p.card_number
    """, [n.lower() for n in bad_names])
    rows = cur.fetchall()
    if rows:
        print(f"[FAIL] 카드 타입 name 오염: {len(rows)}건")
        for r in rows:
            print(f"       {r['card_number']} | name={repr(r['name'])}")
        errors += len(rows)
    else:
        print("[OK] 카드 타입 name 오염: 0건")

    # 5. 커버율 요약
    cur.execute("SELECT COUNT(*) FROM prints")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM card_texts_ko WHERE TRIM(COALESCE(effect_text,'')) != ''")
    filled = cur.fetchone()[0]
    pct = filled / total * 100 if total else 0
    print(f"\n총 prints: {total}건 | ko 있음: {filled}건 | 커버율: {pct:.1f}%")

    conn.close()

    if errors:
        print(f"\n[RESULT] FAIL - 오류 {errors}건")
        return 1
    print("\n[RESULT] ALL OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="DB 한국어 텍스트 커버리지 전수검사")
    ap.add_argument("--db", default="app/assets/hololive_ocg.sqlite", help="SQLite DB 경로")
    args = ap.parse_args()
    return check(args.db)


if __name__ == "__main__":
    sys.exit(main())
