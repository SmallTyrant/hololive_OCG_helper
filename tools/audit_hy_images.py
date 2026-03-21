#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "app" / "assets" / "hololive_ocg.sqlite"


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    hy_cards = conn.execute(
        """
        SELECT DISTINCT card_number
        FROM card_illustrations
        WHERE UPPER(card_number) LIKE 'HY%'
        ORDER BY card_number
        """
    ).fetchall()

    missing_rows = conn.execute(
        """
        SELECT card_number, rarity, COALESCE(image_url, '') AS image_url
        FROM card_illustrations
        WHERE UPPER(card_number) LIKE 'HY%'
          AND (image_url IS NULL OR TRIM(image_url) = '')
        ORDER BY card_number, rarity
        """
    ).fetchall()

    unresolved_cards = conn.execute(
        """
        WITH hy AS (
            SELECT DISTINCT card_number FROM card_illustrations WHERE UPPER(card_number) LIKE 'HY%'
        )
        SELECT h.card_number,
               COALESCE(MAX(CASE WHEN ci.image_url IS NOT NULL AND TRIM(ci.image_url) <> '' THEN 1 ELSE 0 END), 0) AS has_illustration_url,
               COALESCE(MAX(CASE WHEN p.image_url IS NOT NULL AND TRIM(p.image_url) <> '' THEN 1 ELSE 0 END), 0) AS has_print_url
        FROM hy h
        LEFT JOIN card_illustrations ci ON UPPER(ci.card_number) = UPPER(h.card_number)
        LEFT JOIN prints p ON UPPER(p.card_number) = UPPER(h.card_number)
        GROUP BY h.card_number
        HAVING has_illustration_url = 0 AND has_print_url = 0
        ORDER BY h.card_number
        """
    ).fetchall()

    print(f"DB: {DB_PATH}")
    print(f"HY card count: {len(hy_cards)}")
    print(f"HY illustration rows with empty image_url: {len(missing_rows)}")
    for row in missing_rows:
        print(f"  - {row['card_number']} ({row['rarity']})")

    print(f"HY cards without any usable image URL: {len(unresolved_cards)}")
    for row in unresolved_cards:
        print(f"  - {row['card_number']}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
