#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path


def export_csv(db_path: str, out_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Ensure tags_ja exists, fallback to legacy tags
    has_tags_ja = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tags_ja'"
    ).fetchone() is not None
    table = "tags_ja" if has_tags_ja else "tags"

    rows = conn.execute(
        f"SELECT tag_id, tag FROM {table} ORDER BY tag"
    ).fetchall()

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["tag_id", "ja_tag", "ko_tag"])
        for r in rows:
            w.writerow([r["tag_id"], r["tag"], ""])

    conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--out", required=True, help="Output CSV path")
    args = ap.parse_args()
    export_csv(args.db, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
