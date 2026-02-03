#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import Korean card texts from Google Sheets into card_texts_ko.

Usage example:
  python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --sheet-url "https://docs.google.com/spreadsheets/d/<id>/edit#gid=0"
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import csv
import io
import sqlite3
import sys
from urllib.parse import parse_qs, urlparse

from tools.namuwiki_ko_common import (
    KoRow,
    build_session,
    find_header_map,
    import_rows,
    load_existing_ko,
    load_print_map,
    pick_card_number,
    pick_effect,
    pick_name,
)


def build_sheet_csv_url(sheet_url: str, gid: str | None) -> str:
    if "export?format=csv" in sheet_url:
        return sheet_url
    parsed = urlparse(sheet_url)
    if "docs.google.com" not in parsed.netloc:
        return sheet_url
    path_parts = parsed.path.strip("/").split("/")
    if "d" in path_parts:
        idx = path_parts.index("d")
        if idx + 1 < len(path_parts):
            sheet_id = path_parts[idx + 1]
            query_gid = gid
            if not query_gid:
                query = parse_qs(parsed.query)
                query_gid = query.get("gid", [None])[0]
            if not query_gid and parsed.fragment.startswith("gid="):
                query_gid = parsed.fragment.split("gid=", 1)[-1] or None
            if not query_gid:
                query_gid = "0"
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={query_gid}"
    return sheet_url


def parse_sheet_csv(csv_text: str, source_url: str) -> list[KoRow]:
    rows: list[KoRow] = []
    csv_text = csv_text.lstrip("\ufeff")
    reader = csv.reader(io.StringIO(csv_text))
    all_rows = [row for row in reader if row]
    if not all_rows:
        return rows
    header_cells = all_rows[0]
    header_map = find_header_map(header_cells)
    data_rows = all_rows[1:] if header_map else all_rows
    for cells in data_rows:
        card_no = pick_card_number(cells, header_map)
        if not card_no:
            continue
        effect = pick_effect(cells, header_map)
        name = pick_name(cells, header_map)
        if not effect:
            continue
        rows.append(KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url))
    return rows


def import_from_sheet(db_path: str, sheet_url: str, *, timeout: float, overwrite: bool, gid: str | None) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    session = build_session()
    csv_url = build_sheet_csv_url(sheet_url, gid)
    print_map = load_print_map(conn)
    existing_ko = load_existing_ko(conn)
    resp = session.get(csv_url, timeout=timeout)
    resp.raise_for_status()
    updated = import_rows(
        conn,
        parse_sheet_csv(resp.text, csv_url),
        overwrite=overwrite,
        print_map=print_map,
        existing_ko=existing_ko,
    )
    conn.commit()
    conn.close()
    return updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--sheet-url", required=True, help="Google Sheets URL (share or export CSV)")
    ap.add_argument("--sheet-gid", help="Google Sheets gid (optional)")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing Korean texts")
    args = ap.parse_args()

    updated = import_from_sheet(
        args.db,
        args.sheet_url,
        timeout=args.timeout,
        overwrite=args.overwrite,
        gid=args.sheet_gid,
    )
    print(f"[DONE] updated={updated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
