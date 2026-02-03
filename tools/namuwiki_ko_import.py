#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import Korean card texts from NamuWiki or Google Sheets into card_texts_ko.

Usage example:
  python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --page "hololive OCG/카드 목록"
  python tools/namuwiki_ko_import.py --db data/hololive_ocg.sqlite --sheet-url "https://docs.google.com/spreadsheets/d/<id>/edit#gid=0"
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import parse_qs, quote, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

NAMU_BASE = "https://namu.wiki"
CARDNO_RE = re.compile(r"\b[hH][A-Za-z]{1,5}\d{2}-\d{3}\b")

EFFECT_HEADER_KEYWORDS = ("효과", "텍스트", "능력", "카드 효과", "효과 텍스트")
NAME_HEADER_KEYWORDS = ("카드명", "카드 이름", "이름", "카드명(한)")
CARDNO_HEADER_KEYWORDS = ("카드번호", "카드 번호", "card number", "card no", "card_no", "print", "카드넘버")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_card_number(card_no: str) -> str:
    return card_no.strip().upper()


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_header(text: str) -> str:
    return normalize_ws(text).lower()


@dataclass
class KoRow:
    card_number: str
    name: str
    effect: str
    source_url: str


def build_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=0)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_html(session: requests.Session, page: str, *, timeout: float) -> str:
    if page.startswith("http://") or page.startswith("https://"):
        url = page
    else:
        url = f"{NAMU_BASE}/w/{quote(page)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = session.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def find_header_map(header_cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    normalized = [normalize_header(c) for c in header_cells]
    for idx, cell in enumerate(normalized):
        for key in CARDNO_HEADER_KEYWORDS:
            if key in cell:
                mapping["card_number"] = idx
                break
        for key in EFFECT_HEADER_KEYWORDS:
            if key in cell:
                mapping["effect"] = idx
                break
        for key in NAME_HEADER_KEYWORDS:
            if key in cell:
                mapping["name"] = idx
    return mapping


def pick_effect(cells: list[str], header_map: dict[str, int]) -> str:
    if "effect" in header_map:
        idx = header_map["effect"]
        if 0 <= idx < len(cells):
            return normalize_ws(cells[idx])
    # fallback: pick the longest non-empty cell
    candidates = [normalize_ws(c) for c in cells if normalize_ws(c)]
    if not candidates:
        return ""
    return max(candidates, key=len)


def pick_name(cells: list[str], header_map: dict[str, int]) -> str:
    if "name" in header_map:
        idx = header_map["name"]
        if 0 <= idx < len(cells):
            return normalize_ws(cells[idx])
    return ""


def pick_card_number(cells: list[str], header_map: dict[str, int]) -> str:
    if "card_number" in header_map:
        idx = header_map["card_number"]
        if 0 <= idx < len(cells):
            value = normalize_ws(cells[idx])
            if value:
                return value
    for cell in cells:
        match = CARDNO_RE.search(cell)
        if match:
            return normalize_card_number(match.group(0))
    return ""


def parse_tables(html: str, source_url: str) -> list[KoRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[KoRow] = []
    for table in soup.select("table"):
        header_map: dict[str, int] = {}
        header_cells: list[str] = []
        body_rows = []
        for tr in table.select("tr"):
            cells = tr.find_all(["th", "td"])
            if not cells:
                continue
            cell_texts = [c.get_text("\n", strip=True) for c in cells]
            if not header_cells and tr.find("th"):
                header_cells = cell_texts
                header_map = find_header_map(header_cells)
                continue
            body_rows.append(cell_texts)

        if not header_cells and body_rows:
            header_cells = body_rows[0]
            header_map = find_header_map(header_cells)
            body_rows = body_rows[1:]

        for cells in body_rows:
            card_no = pick_card_number(cells, header_map)
            if not card_no:
                continue
            effect = pick_effect(cells, header_map)
            name = pick_name(cells, header_map)
            if not effect:
                continue
            rows.append(KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url))
    return rows


def iter_pages(pages: list[str], page_file: str | None) -> Iterable[str]:
    for page in pages:
        if page:
            yield page.strip()
    if page_file:
        with open(page_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                yield line


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
    reader = csv.reader(csv_text.splitlines())
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


def upsert_ko_text(
    conn: sqlite3.Connection,
    print_id: int,
    name: str,
    effect: str,
    source_url: str,
    *,
    overwrite: bool,
) -> bool:
    row = conn.execute(
        "SELECT name, effect_text, version FROM card_texts_ko WHERE print_id=?",
        (print_id,),
    ).fetchone()
    if row and not overwrite:
        if row["effect_text"] and row["effect_text"].strip():
            return False
    version = 1
    if row:
        version = int(row["version"] or 1)
        if row["effect_text"] != effect or row["name"] != name:
            version += 1
    conn.execute(
        """
        INSERT INTO card_texts_ko(print_id,name,effect_text,memo,source,version,updated_at)
        VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(print_id) DO UPDATE SET
          name=excluded.name,
          effect_text=excluded.effect_text,
          memo=excluded.memo,
          source=excluded.source,
          version=excluded.version,
          updated_at=excluded.updated_at
        """,
        (print_id, name, effect, source_url, "namuwiki", version, now_iso()),
    )
    return True


def import_from_pages(db_path: str, pages: list[str], page_file: str | None, *, timeout: float, overwrite: bool) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    session = build_session()

    updated = 0
    for page in iter_pages(pages, page_file):
        html = fetch_html(session, page, timeout=timeout)
        source_url = page if page.startswith("http") else f"{NAMU_BASE}/w/{quote(page)}"
        for row in parse_tables(html, source_url):
            print_row = conn.execute(
                "SELECT print_id FROM prints WHERE upper(card_number)=upper(?)",
                (row.card_number,),
            ).fetchone()
            if not print_row:
                print(f"[SKIP] missing print for {row.card_number}")
                continue
            if upsert_ko_text(conn, int(print_row["print_id"]), row.name, row.effect, row.source_url, overwrite=overwrite):
                updated += 1
    conn.commit()
    conn.close()
    return updated


def import_from_sheet(db_path: str, sheet_url: str, *, timeout: float, overwrite: bool, gid: str | None) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    session = build_session()
    csv_url = build_sheet_csv_url(sheet_url, gid)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    resp = session.get(csv_url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    updated = 0
    for row in parse_sheet_csv(resp.text, csv_url):
        print_row = conn.execute(
            "SELECT print_id FROM prints WHERE upper(card_number)=upper(?)",
            (row.card_number,),
        ).fetchone()
        if not print_row:
            print(f"[SKIP] missing print for {row.card_number}")
            continue
        if upsert_ko_text(conn, int(print_row["print_id"]), row.name, row.effect, row.source_url, overwrite=overwrite):
            updated += 1
    conn.commit()
    conn.close()
    return updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--page", action="append", default=[], help="NamuWiki page title or full URL")
    ap.add_argument("--page-file", help="Text file containing page titles/URLs")
    ap.add_argument("--sheet-url", help="Google Sheets URL (share or export CSV)")
    ap.add_argument("--sheet-gid", help="Google Sheets gid (optional)")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing Korean texts")
    args = ap.parse_args()

    if not args.page and not args.page_file and not args.sheet_url:
        print("No sources provided. Use --page/--page-file or --sheet-url.")
        return 1

    updated = 0
    if args.page or args.page_file:
        updated += import_from_pages(args.db, args.page, args.page_file, timeout=args.timeout, overwrite=args.overwrite)
    if args.sheet_url:
        updated += import_from_sheet(
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
