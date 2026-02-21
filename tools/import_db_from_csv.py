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


def decode_cell(raw: str | None) -> object:
    if raw is None:
        return None
    if raw == NULL_TOKEN:
        return None
    if raw.startswith(ESCAPE_PREFIX):
        return raw[len(ESCAPE_PREFIX):]
    if raw.startswith(BLOB_PREFIX):
        encoded = raw[len(BLOB_PREFIX):]
        return base64.b64decode(encoded.encode("ascii"))
    return raw


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


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({quote_ident(table_name)})").fetchall()
    return [str(row["name"]) for row in rows]


def ensure_table(conn: sqlite3.Connection, table_name: str, columns: list[str]) -> None:
    if table_exists(conn, table_name):
        existing = set(table_columns(conn, table_name))
        missing = [col for col in columns if col not in existing]
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Table '{table_name}' is missing CSV columns: {joined}")
        return

    cols_sql = ", ".join(f"{quote_ident(col)} TEXT" for col in columns)
    conn.execute(f"CREATE TABLE {quote_ident(table_name)} ({cols_sql})")


def load_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    script = schema_path.read_text(encoding="utf-8")
    conn.executescript(script)


def normalize_headers(fieldnames: list[str | None]) -> list[str]:
    headers: list[str] = []
    seen: set[str] = set()
    for field in fieldnames:
        name = (field or "").strip()
        if not name:
            raise RuntimeError("CSV has an empty column name.")
        if name in seen:
            raise RuntimeError(f"CSV has duplicate column name: {name}")
        seen.add(name)
        headers.append(name)
    return headers


def import_table(conn: sqlite3.Connection, csv_path: Path, table_name: str, replace_table: bool) -> int:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError(f"CSV has no header: {csv_path}")

        headers = normalize_headers(reader.fieldnames)
        ensure_table(conn, table_name, headers)

        if replace_table:
            conn.execute(f"DELETE FROM {quote_ident(table_name)}")

        cols_sql = ", ".join(quote_ident(col) for col in headers)
        placeholders = ", ".join("?" for _ in headers)
        insert_sql = f"INSERT INTO {quote_ident(table_name)} ({cols_sql}) VALUES ({placeholders})"

        inserted = 0
        for row in reader:
            values = [decode_cell(row.get(col)) for col in headers]
            if all(v in (None, "") for v in values):
                continue
            conn.execute(insert_sql, values)
            inserted += 1

    return inserted


def import_db(csv_dir: str, db_path: str, schema_path: str | None, overwrite_db: bool, replace_table: bool) -> None:
    source_dir = Path(csv_dir)
    if not source_dir.exists() or not source_dir.is_dir():
        raise NotADirectoryError(csv_dir)

    db_file = Path(db_path)
    if overwrite_db and db_file.exists():
        db_file.unlink()

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    existing_tables = list_tables(conn)
    candidate_schema = Path(schema_path) if schema_path else source_dir / "schema.sql"
    if schema_path and not candidate_schema.exists():
        conn.close()
        raise FileNotFoundError(candidate_schema)

    if candidate_schema.exists() and not existing_tables:
        load_schema(conn, candidate_schema)
        print(f"[SCHEMA] loaded -> {candidate_schema}")
    elif candidate_schema.exists():
        print(f"[SCHEMA] skipped (tables already exist) -> {candidate_schema}")

    csv_files = sorted(p for p in source_dir.glob("*.csv") if p.is_file())
    if not csv_files:
        conn.close()
        raise RuntimeError(f"No CSV files found in {source_dir}")

    for csv_path in csv_files:
        table_name = csv_path.stem
        inserted = import_table(conn, csv_path, table_name, replace_table=replace_table)
        print(f"[TABLE] {table_name}: rows={inserted} <- {csv_path}")

    conn.commit()
    conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Import CSV files into a SQLite DB.")
    ap.add_argument("--csv-dir", required=True, help="Directory containing table CSV files")
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--schema", help="Optional schema.sql path (default: <csv-dir>/schema.sql)")
    ap.add_argument("--overwrite-db", action="store_true", help="Delete DB file before import")
    ap.add_argument("--replace-table", action="store_true", help="Delete table rows before importing CSV")
    args = ap.parse_args()

    import_db(
        csv_dir=args.csv_dir,
        db_path=args.db,
        schema_path=args.schema,
        overwrite_db=args.overwrite_db,
        replace_table=args.replace_table,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
