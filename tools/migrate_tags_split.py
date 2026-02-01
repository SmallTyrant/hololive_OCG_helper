#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sqlite3


def has_table(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # create tags_ja/ko if missing
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags_ja(
          tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
          tag TEXT NOT NULL UNIQUE,
          normalized TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags_ko(
          tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
          tag TEXT NOT NULL UNIQUE,
          normalized TEXT NOT NULL
        );
        """
    )

    # copy legacy tags -> tags_ja if tags exists and tags_ja empty
    tags_ja_count = conn.execute("SELECT COUNT(*) FROM tags_ja").fetchone()[0]
    if has_table(conn, "tags") and tags_ja_count == 0:
        rows = conn.execute("SELECT tag_id, tag, normalized FROM tags").fetchall()
        for r in rows:
            conn.execute(
                """
                INSERT OR IGNORE INTO tags_ja(tag_id, tag, normalized)
                VALUES(?, ?, ?)
                """,
                (r["tag_id"], r["tag"], r["normalized"]),
            )

    conn.commit()
    conn.close()
    print("[DONE] migrate tags -> tags_ja/tags_ko")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    args = ap.parse_args()
    migrate(args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
