#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "app" / "assets" / "hololive_ocg.sqlite"


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def parse_card_type(row: sqlite3.Row) -> str:
    card_type = (row["card_type"] or "").strip()
    if card_type:
        return card_type
    ja_text = row["ja_text"] or ""
    m = re.search(r"カードタイプ\s*([^\n]+)", ja_text)
    return m.group(1).strip() if m else ""


def is_oshi(row: sqlite3.Row) -> bool:
    card_type = parse_card_type(row)
    return "오시" in card_type or "推し" in card_type


def is_yell(row: sqlite3.Row) -> bool:
    card_number = (row["card_number"] or "").upper()
    if card_number.startswith("HY"):
        return True
    color = (row["color"] or "").lower()
    card_type = parse_card_type(row).lower()
    return any(x in color for x in ("옐", "yell", "エール")) or any(x in card_type for x in ("yell", "エール"))


def has_unlimited_rule(row: sqlite3.Row) -> bool:
    ko_norm = normalize(row["ko_text"] or "")
    ja_norm = normalize(row["ja_text"] or "")
    return "덱에몇장이라도넣을수있" in ko_norm or "デッキに何枚でも入れられる" in ja_norm


def rarity_set(row: sqlite3.Row) -> set[str]:
    raw = (row["illustration_rarities"] or "").strip()
    if not raw:
        return set()
    return {part.strip().upper() for part in raw.split(",") if part.strip()}


def max_per_card_policy(row: sqlite3.Row) -> int:
    rarities = rarity_set(row)
    if is_oshi(row):
        return 1
    if "OUR" in rarities or "OSR" in rarities:
        return 1
    if is_yell(row):
        return 50
    if has_unlimited_rule(row):
        return 50
    return 4


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT
            p.print_id,
            p.card_number,
            COALESCE(p.card_type, '') AS card_type,
            COALESCE(p.color, '') AS color,
            COALESCE(ko.effect_text, '') AS ko_text,
            COALESCE(ja.effect_text, '') AS ja_text,
            COALESCE((
                SELECT GROUP_CONCAT(DISTINCT UPPER(COALESCE(ci.rarity, '')))
                FROM card_illustrations ci
                WHERE UPPER(ci.card_number) = UPPER(p.card_number)
            ), '') AS illustration_rarities
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
        ORDER BY p.card_number, p.print_id
        """
    ).fetchall()

    counts = Counter()
    sec_non_oshi: list[tuple[str, str]] = []
    unlimited_cards: list[str] = []

    for row in rows:
        limit = max_per_card_policy(row)
        counts[limit] += 1
        rset = rarity_set(row)
        if "SEC" in rset and not is_oshi(row):
            sec_non_oshi.append((row["card_number"], parse_card_type(row)))
        if has_unlimited_rule(row):
            unlimited_cards.append(row["card_number"])

    print(f"DB: {DB_PATH}")
    print(f"Total prints: {len(rows)}")
    print("Limit distribution:")
    for key in sorted(counts.keys()):
        print(f"  {key}: {counts[key]}")

    print(f"SEC non-oshi card count: {len(sec_non_oshi)}")
    for card_number, card_type in sec_non_oshi[:20]:
        print(f"  - {card_number} ({card_type})")

    unique_unlimited = sorted(set(unlimited_cards))
    print(f"Unlimited-rule card count: {len(unique_unlimited)}")
    for card_number in unique_unlimited[:20]:
        print(f"  - {card_number}")

    # Spot checks requested in thread.
    print("Spot check:")
    targets = ["hBP07-102", "hBP04-104", "hBP04-072", "hBP02-084", "hBP05-016", "hBP05-080"]
    by_upper = {str(r["card_number"]).upper(): r for r in rows}
    for cn in targets:
        row = by_upper.get(cn.upper())
        if not row:
            print(f"  - {cn}: not found")
            continue
        print(f"  - {cn}: {max_per_card_policy(row)}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
