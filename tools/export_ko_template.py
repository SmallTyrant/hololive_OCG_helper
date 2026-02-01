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

    rows = conn.execute(
        """
        SELECT p.print_id, p.card_number, COALESCE(p.name_ja,'') AS name_ja
        FROM prints p
        ORDER BY p.card_number
        """
    ).fetchall()

    # prefetch tags
    # Prefer tags_ja if present, fallback to legacy tags
    has_tags_ja = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='tags_ja'"
    ).fetchone() is not None
    tag_table = "tags_ja" if has_tags_ja else "tags"

    tag_rows = conn.execute(
        f"""
        SELECT pt.print_id, t.tag
        FROM print_tags pt
        JOIN {tag_table} t ON t.tag_id = pt.tag_id
        ORDER BY pt.print_id, t.tag
        """
    ).fetchall()

    tags_by_print: dict[int, list[str]] = {}
    for r in tag_rows:
        tags_by_print.setdefault(int(r["print_id"]), []).append(r["tag"])

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["print_id", "card_number", "name_ja", "tags", "ko_name", "ko_text", "ko_memo"])
        for r in rows:
            pid = int(r["print_id"])
            tags = ", ".join(tags_by_print.get(pid, []))
            w.writerow([
                pid,
                r["card_number"],
                r["name_ja"],
                tags,
                "",  # ko_name
                "",  # ko_text
                "",  # ko_memo
            ])

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
