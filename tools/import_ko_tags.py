#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


def ensure_tags_ko(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags_ko(
          tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
          tag TEXT NOT NULL UNIQUE,
          normalized TEXT NOT NULL
        );
        """
    )


def normalize(tag: str) -> str:
    t = (tag or "").strip()
    if t.startswith("#"):
        t = t[1:]
    return "".join(t.split()).lower()


def import_csv(db_path: str, csv_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ensure_tags_ko(conn)

    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(csv_path)

    updated = 0
    with p.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            tag_id_raw = (row.get("tag_id") or "").strip()
            ko_tag = (row.get("ko_tag") or "").strip()
            if not tag_id_raw or not ko_tag:
                continue
            try:
                tag_id = int(tag_id_raw)
            except ValueError:
                continue

            norm = normalize(ko_tag)
            conn.execute(
                """
                INSERT INTO tags_ko(tag_id, tag, normalized)
                VALUES(?, ?, ?)
                ON CONFLICT(tag_id) DO UPDATE SET
                  tag=excluded.tag,
                  normalized=excluded.normalized
                """,
                (tag_id, ko_tag, norm),
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"[DONE] import tags_ko updated={updated}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--csv", required=True, help="CSV path")
    args = ap.parse_args()

    import_csv(args.db, args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
