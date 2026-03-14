"""
엑스트라 무제한 문구(ko/ja) 누락 현황을 점검하는 읽기 전용 스크립트입니다.

기본 동작:
1) 한국어 본문에 "몇 장이라도 넣을 수 있다" 문구가 있는 카드 수 집계
2) 일본어 본문에는 무제한 문구가 있으나 한국어 본문에는 없는 카드 집계
3) 특정 카드(hBP04-020) 상태 확인
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


DEFAULT_DB = Path(__file__).resolve().parent.parent / "app" / "assets" / "hololive_ocg.sqlite"


def normalized_expr(column: str) -> str:
    # 공백/전각공백 제거 후 비교
    return f"REPLACE(REPLACE(COALESCE({column}, ''), ' ', ''), '　', '')"


def fetch_rows(connection: sqlite3.Connection) -> list[tuple[str, str, str, str]]:
    ko_norm = normalized_expr("ko.effect_text")
    ja_norm = normalized_expr("ja.effect_text")
    sql = f"""
        SELECT
            COALESCE(p.card_number, '') AS card_number,
            COALESCE(p.detail_url, '') AS detail_url,
            COALESCE(ko.effect_text, '') AS ko_text,
            COALESCE(ja.effect_text, '') AS ja_text
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
        WHERE
            {ja_norm} LIKE '%何枚でも%'
            AND {ja_norm} LIKE '%入れられる%'
            AND {ko_norm} NOT LIKE '%몇장이라도넣을수있다%'
        ORDER BY p.card_number
    """
    return connection.execute(sql).fetchall()


def fetch_counts(connection: sqlite3.Connection) -> tuple[int, int]:
    ko_norm = normalized_expr("ko.effect_text")
    ja_norm = normalized_expr("ja.effect_text")
    ko_count_sql = f"""
        SELECT COUNT(*)
        FROM card_texts_ko ko
        WHERE {ko_norm} LIKE '%몇장이라도넣을수있다%'
    """
    ja_only_count_sql = f"""
        SELECT COUNT(*)
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
        WHERE
            {ja_norm} LIKE '%何枚でも%'
            AND {ja_norm} LIKE '%入れられる%'
            AND {ko_norm} NOT LIKE '%몇장이라도넣을수있다%'
    """
    ko_count = int(connection.execute(ko_count_sql).fetchone()[0])
    ja_only_count = int(connection.execute(ja_only_count_sql).fetchone()[0])
    return ko_count, ja_only_count


def fetch_target_card_state(connection: sqlite3.Connection, card_number: str) -> tuple[str, str]:
    ko_norm = normalized_expr("ko.effect_text")
    ja_norm = normalized_expr("ja.effect_text")
    sql = f"""
        SELECT
            CASE
                WHEN {ko_norm} LIKE '%몇장이라도넣을수있다%' THEN 'ko_has_phrase'
                ELSE 'ko_no_phrase'
            END,
            CASE
                WHEN {ja_norm} LIKE '%何枚でも%' AND {ja_norm} LIKE '%入れられる%' THEN 'ja_has_phrase'
                ELSE 'ja_no_phrase'
            END
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
        WHERE UPPER(COALESCE(p.card_number, '')) = UPPER(?)
        LIMIT 1
    """
    row = connection.execute(sql, (card_number,)).fetchone()
    if row is None:
        return "card_not_found", "card_not_found"
    return str(row[0]), str(row[1])


def main() -> int:
    parser = argparse.ArgumentParser(description="엑스트라 무제한 문구 누락 점검")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite DB 경로")
    parser.add_argument("--list", action="store_true", help="카드 번호 목록만 출력")
    parser.add_argument("--limit", type=int, default=50, help="샘플 출력 최대 개수")
    parser.add_argument("--target-card", default="hBP04-020", help="상태 확인 카드 번호")
    args = parser.parse_args()

    db_path = args.db.resolve()
    if not db_path.exists():
        print(f"DB 파일이 없습니다: {db_path}")
        return 1

    with sqlite3.connect(db_path) as connection:
        ko_count, ja_only_count = fetch_counts(connection)
        target_ko, target_ja = fetch_target_card_state(connection, args.target_card)
        rows = fetch_rows(connection)

    if args.list:
        for card_number, _, _, _ in rows:
            print(card_number)
        return 0

    print(f"DB 경로: {db_path}")
    print(f"ko 무제한 문구 포함 카드 수: {ko_count}")
    print(f"ja 무제한 문구만 있고 ko 무제한 문구가 없는 카드 수: {ja_only_count}")
    print(f"대상 카드({args.target_card}) 상태: {target_ko}, {target_ja}")

    if not rows:
        print("\n누락 카드가 없습니다.")
        return 0

    print(f"\n누락 카드 샘플 (최대 {args.limit}개):")
    for card_number, detail_url, ko_text, ja_text in rows[: max(0, args.limit)]:
        ko_preview = ko_text.replace("\n", " ").strip()
        ja_preview = ja_text.replace("\n", " ").strip()
        if len(ko_preview) > 80:
            ko_preview = ko_preview[:80] + "..."
        if len(ja_preview) > 80:
            ja_preview = ja_preview[:80] + "..."
        print(f"- {card_number} | {detail_url}")
        print(f"  ko: {ko_preview or '(빈 값)'}")
        print(f"  ja: {ja_preview or '(빈 값)'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
