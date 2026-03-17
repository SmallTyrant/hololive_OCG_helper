#!/usr/bin/env python3
"""
import_manage_id.py
hocg-fan-sim-assets의 hocg_cards.json 에서 manage_id_jp 를
app/assets/hololive_ocg.sqlite 의 prints 테이블에 추가합니다.

Usage:
    .venv/bin/python3 tools/import_manage_id.py
"""
from __future__ import annotations
import json, sqlite3, urllib.request, sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "app" / "assets" / "hololive_ocg.sqlite"
CARDS_JSON_URL = "https://qrimpuff.github.io/hocg-fan-sim-assets/hocg_cards.json"


def fetch_cards() -> dict:
    print(f"[INFO] fetching {CARDS_JSON_URL} ...", flush=True)
    with urllib.request.urlopen(CARDS_JSON_URL, timeout=60) as resp:
        return json.loads(resp.read())


def add_column_if_missing(conn: sqlite3.Connection) -> None:
    cols = [row[1] for row in conn.execute("PRAGMA table_info(prints)")]
    if "manage_id_jp" not in cols:
        conn.execute("ALTER TABLE prints ADD COLUMN manage_id_jp INTEGER")
        conn.commit()
        print("[INFO] added column manage_id_jp to prints", flush=True)
    else:
        print("[INFO] column manage_id_jp already exists", flush=True)


def build_mapping(cards: dict) -> dict[str, int]:
    """card_number -> first JP manage_id"""
    mapping: dict[str, int] = {}
    for card_number, card in cards.items():
        for illus in card.get("illustrations", []):
            jp_ids = illus.get("manage_id", {}).get("jp", [])
            if jp_ids:
                mapping[card_number] = int(jp_ids[0])
                break
    return mapping


def update_db(conn: sqlite3.Connection, mapping: dict[str, int]) -> int:
    cur = conn.cursor()
    updated = 0
    for card_number, manage_id in mapping.items():
        cur.execute(
            "UPDATE prints SET manage_id_jp=? WHERE card_number=?",
            (manage_id, card_number),
        )
        if cur.rowcount > 0:
            updated += 1
    conn.commit()
    return updated


def main() -> None:
    cards = fetch_cards()
    print(f"[INFO] fetched {len(cards)} cards", flush=True)

    mapping = build_mapping(cards)
    print(f"[INFO] built mapping for {len(mapping)} card_numbers", flush=True)

    conn = sqlite3.connect(DB_PATH)
    try:
        add_column_if_missing(conn)
        updated = update_db(conn, mapping)
        print(f"[INFO] updated {updated} rows in prints", flush=True)

        # 커버리지 확인
        total = conn.execute("SELECT COUNT(*) FROM prints").fetchone()[0]
        covered = conn.execute(
            "SELECT COUNT(*) FROM prints WHERE manage_id_jp IS NOT NULL"
        ).fetchone()[0]
        print(
            f"[INFO] coverage: {covered}/{total} ({covered/total*100:.1f}%)",
            flush=True,
        )

        # 샘플 출력
        print("\n[SAMPLE]", flush=True)
        for row in conn.execute(
            "SELECT card_number, manage_id_jp FROM prints WHERE manage_id_jp IS NOT NULL LIMIT 5"
        ):
            print(f"  {row[0]} -> {row[1]}", flush=True)

        # 미매핑 카드
        no_id = conn.execute(
            "SELECT card_number FROM prints WHERE manage_id_jp IS NULL ORDER BY card_number"
        ).fetchall()
        if no_id:
            print(f"\n[WARN] {len(no_id)} cards without manage_id_jp:", flush=True)
            for row in no_id[:20]:
                print(f"  {row[0]}", flush=True)
            if len(no_id) > 20:
                print(f"  ...and {len(no_id)-20} more", flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
