#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def has_source_column(conn: sqlite3.Connection) -> bool:
    rows = conn.execute("PRAGMA table_info(card_texts_ko)").fetchall()
    return any((row[1] or "") == "source" for row in rows)


def resolve_print_id(conn: sqlite3.Connection, row: dict[str, str]) -> int | None:
    card_number = (row.get("card_number") or "").strip()
    if card_number:
        mapped = conn.execute(
            "SELECT print_id FROM prints WHERE UPPER(card_number)=UPPER(?)",
            (card_number,),
        ).fetchone()
        if mapped:
            return int(mapped[0])

    pid_raw = (row.get("print_id") or "").strip()
    if not pid_raw:
        return None
    try:
        return int(pid_raw)
    except ValueError:
        return None


def import_csv(db_path: str, csv_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    include_source = has_source_column(conn)

    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(csv_path)

    updated = 0
    with p.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            pid = resolve_print_id(conn, row)
            if pid is None:
                continue

            ko_name = (row.get("ko_name") or "").strip()
            ko_text = (row.get("ko_text") or "").strip()
            ko_memo = (row.get("ko_memo") or "").strip()

            if not (ko_name or ko_text or ko_memo):
                continue

            ts = now_iso()
            if include_source:
                conn.execute(
                    """
                    INSERT INTO card_texts_ko(print_id, name, effect_text, memo, source, updated_at)
                    VALUES(?, ?, ?, ?, 'manual', ?)
                    ON CONFLICT(print_id) DO UPDATE SET
                      name=excluded.name,
                      effect_text=excluded.effect_text,
                      memo=excluded.memo,
                      source='manual',
                      updated_at=excluded.updated_at
                    """,
                    (pid, ko_name, ko_text, ko_memo, ts),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO card_texts_ko(print_id, name, effect_text, memo, updated_at)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(print_id) DO UPDATE SET
                      name=excluded.name,
                      effect_text=excluded.effect_text,
                      memo=excluded.memo,
                      updated_at=excluded.updated_at
                    """,
                    (pid, ko_name, ko_text, ko_memo, ts),
                )
            updated += 1

    conn.commit()
    conn.close()
    print(f"[DONE] import updated={updated}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--csv", required=True, help="CSV path")
    args = ap.parse_args()

    import_csv(args.db, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
