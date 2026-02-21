#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import base64
import csv
import sqlite3
from pathlib import Path

NULL_TOKEN = "__SQLITE_NULL__"
BLOB_PREFIX = "__SQLITE_BLOB_BASE64__:"
ESCAPE_PREFIX = "__SQLITE_ESC__:"


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def encode_cell(value: object) -> object:
    if value is None:
        return NULL_TOKEN
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        return BLOB_PREFIX + base64.b64encode(raw).decode("ascii")
    if isinstance(value, str):
        if value == NULL_TOKEN or value.startswith(BLOB_PREFIX) or value.startswith(ESCAPE_PREFIX):
            return ESCAPE_PREFIX + value
    return value


def list_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall()
    return [str(row["name"]) for row in rows]


def export_table(conn: sqlite3.Connection, table_name: str, out_path: Path) -> int:
    columns = table_columns(conn, table_name)
    cursor = conn.execute(f"SELECT * FROM {quote_ident(table_name)}")
    row_count = 0

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        for row in cursor:
            writer.writerow([encode_cell(row[col]) for col in columns])
            row_count += 1

    return row_count


def export_schema(conn: sqlite3.Connection, out_path: Path) -> int:
    rows = conn.execute(
        """
        SELECT type, name, sql
        FROM sqlite_master
        WHERE sql IS NOT NULL
          AND type IN ('table', 'index', 'trigger', 'view')
          AND name NOT LIKE 'sqlite_%'
        ORDER BY
          CASE type
            WHEN 'table' THEN 0
            WHEN 'index' THEN 1
            WHEN 'trigger' THEN 2
            WHEN 'view' THEN 3
            ELSE 9
          END,
          name
        """
    ).fetchall()

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            sql = str(row["sql"]).strip()
            if not sql.endswith(";"):
                sql += ";"
            f.write(sql)
            f.write("\n\n")

    return len(rows)


def export_db(db_path: str, out_dir: str, include_schema: bool) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tables = list_tables(conn)
    if not tables:
        conn.close()
        raise RuntimeError("No user tables found in DB.")

    for table_name in tables:
        csv_path = out / f"{table_name}.csv"
        row_count = export_table(conn, table_name, csv_path)
        print(f"[TABLE] {table_name}: rows={row_count} -> {csv_path}")

    if include_schema:
        schema_path = out / "schema.sql"
        statement_count = export_schema(conn, schema_path)
        print(f"[SCHEMA] statements={statement_count} -> {schema_path}")

    conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Export SQLite DB tables to CSV files.")
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--out-dir", required=True, help="Output directory for CSV files")
    ap.add_argument("--no-schema", action="store_true", help="Do not export schema.sql")
    args = ap.parse_args()

    export_db(args.db, args.out_dir, include_schema=not args.no_schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
