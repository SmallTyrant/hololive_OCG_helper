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
import io
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable
from urllib.parse import parse_qs, quote, urlparse

import requests
from bs4 import BeautifulSoup, FeatureNotFound
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NAMU_BASE = "https://namu.wiki"
CARDNO_RE = re.compile(r"\b[hH][A-Za-z]{1,5}\d{2}-\d{3}\b")

EFFECT_HEADER_KEYWORDS = ("효과", "텍스트", "능력", "카드 효과", "효과 텍스트")
NAME_HEADER_KEYWORDS = ("카드명", "카드 이름", "이름", "카드명(한)")
CARDNO_HEADER_KEYWORDS = ("카드번호", "카드 번호", "카드 넘버", "card number", "card no", "card_no", "print", "카드넘버")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_card_number(card_no: str) -> str:
    return card_no.strip().upper()


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_header(text: str) -> str:
    return normalize_ws(text).lower()


LABEL_CELL_KEYWORDS = tuple(
    sorted(
        {
            normalize_header(k)
            for k in (
                *CARDNO_HEADER_KEYWORDS,
                *NAME_HEADER_KEYWORDS,
                *EFFECT_HEADER_KEYWORDS,
                "레벨",
                "속성",
                "종류",
                "타입",
                "색",
                "색상",
                "컬러",
                "레어도",
                "코스트",
                "에너지",
                "소속",
                "기수",
                "유닛",
                "카드종류",
                "카드 종류",
                "카드 타입",
            )
        }
    )
)

BULLET_MARKERS = ("■", "●", "◆", "◇", "•", "·")


def cell_has_keyword(cell: str, keywords: Iterable[str]) -> bool:
    normalized = normalize_header(cell)
    for key in keywords:
        if normalize_header(key) in normalized:
            return True
    return False


def is_label_cell(cell: str) -> bool:
    normalized = normalize_header(cell)
    if not normalized:
        return False
    return any(key in normalized for key in LABEL_CELL_KEYWORDS)


@dataclass
class KoRow:
    card_number: str
    name: str
    effect: str
    source_url: str


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        }
    )
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_html(session: requests.Session, page: str, *, timeout: float) -> str:
    if page.startswith("http://") or page.startswith("https://"):
        url = page
    else:
        url = f"{NAMU_BASE}/w/{quote(page)}"
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def find_header_map(header_cells: list[str], *, min_matches: int = 2) -> dict[str, int]:
    mapping: dict[str, int] = {}
    normalized = [normalize_header(c) for c in header_cells]
    for idx, cell in enumerate(normalized):
        if "card_number" not in mapping:
            for key in CARDNO_HEADER_KEYWORDS:
                if key in cell:
                    mapping["card_number"] = idx
                    break
        if "effect" not in mapping:
            for key in EFFECT_HEADER_KEYWORDS:
                if key in cell:
                    mapping["effect"] = idx
                    break
        if "name" not in mapping:
            for key in NAME_HEADER_KEYWORDS:
                if key in cell:
                    mapping["name"] = idx
                    break
    if len(mapping) < min_matches:
        return {}
    return mapping


def pick_effect(cells: list[str], header_map: dict[str, int]) -> str:
    if "effect" in header_map:
        idx = header_map["effect"]
        if 0 <= idx < len(cells):
            return normalize_ws(cells[idx])
    # fallback: pick the longest non-empty cell
    candidates = []
    for cell in cells:
        normalized = normalize_ws(cell)
        if not normalized:
            continue
        if CARDNO_RE.search(normalized):
            continue
        if is_label_cell(normalized):
            continue
        candidates.append(normalized)
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
                return normalize_card_number(value)
    for cell in cells:
        match = CARDNO_RE.search(cell)
        if match:
            return normalize_card_number(match.group(0))
    return ""


def parse_vertical_table(table, source_url: str) -> KoRow | None:
    rows: list[list[str]] = []
    for tr in table.select("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        rows.append([c.get_text("\n", strip=True) for c in cells])

    if not rows:
        return None

    header_map: dict[str, int] = {}
    for tr in table.select("tr"):
        if tr.find("th"):
            header_cells = [c.get_text("\n", strip=True) for c in tr.find_all(["th", "td"])]
            header_map = find_header_map(header_cells)
            break
    if len(header_map) >= 2:
        return None

    card_numbers: list[str] = []
    for cells in rows:
        for cell in cells:
            for match in CARDNO_RE.finditer(cell):
                card_numbers.append(normalize_card_number(match.group(0)))
    unique_card_numbers = sorted(set(card_numbers))
    if len(unique_card_numbers) != 1:
        return None
    if len(rows) > 20 or sum(len(r) for r in rows) > 60:
        return None

    card_no = unique_card_numbers[0]

    name = ""
    for cells in rows:
        if len(cells) >= 2 and cell_has_keyword(cells[0], NAME_HEADER_KEYWORDS):
            name = normalize_ws(cells[1])
            break

    effect = ""
    for cells in rows:
        if len(cells) >= 2 and cell_has_keyword(cells[0], EFFECT_HEADER_KEYWORDS):
            effect = normalize_ws(cells[1])
            break

    if not effect:
        candidates: list[tuple[int, str]] = []
        for cells in rows:
            for cell in cells:
                raw = cell
                text = normalize_ws(cell)
                if not text:
                    continue
                if CARDNO_RE.search(text):
                    continue
                if is_label_cell(text):
                    continue
                if name and normalize_ws(text) == name:
                    continue
                score = len(text)
                if "\n" in raw:
                    score += 20
                if any(marker in raw for marker in BULLET_MARKERS):
                    score += 30
                candidates.append((score, text))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            effect = candidates[0][1]

    if not effect:
        return None

    return KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url)


def parse_tables(html: str, source_url: str) -> list[KoRow]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(html, "html.parser")
    rows: list[KoRow] = []
    for table in soup.select("table"):
        vertical = parse_vertical_table(table, source_url)
        if vertical:
            rows.append(vertical)
            continue
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


def upsert_ko_text(
    conn: sqlite3.Connection,
    print_id: int,
    name: str,
    effect: str,
    source_url: str,
    *,
    overwrite: bool,
    existing: dict[int, tuple[str, str, int]] | None = None,
) -> bool:
    cached = existing.get(print_id) if existing is not None else None
    if cached and not overwrite:
        if cached[1].strip():
            return False
    version = 1
    if cached:
        version = int(cached[2] or 1)
        if cached[1] != effect or cached[0] != name:
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
    if existing is not None:
        existing[print_id] = (name, effect, version)
    return True


def load_print_map(conn: sqlite3.Connection) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for row in conn.execute("SELECT print_id, card_number FROM prints"):
        mapping[normalize_card_number(row["card_number"] or "")] = int(row["print_id"])
    return mapping


def load_existing_ko(conn: sqlite3.Connection) -> dict[int, tuple[str, str, int]]:
    mapping: dict[int, tuple[str, str, int]] = {}
    for row in conn.execute("SELECT print_id, name, effect_text, version FROM card_texts_ko"):
        mapping[int(row["print_id"])] = (
            row["name"] or "",
            row["effect_text"] or "",
            int(row["version"] or 1),
        )
    return mapping


def import_rows(
    conn: sqlite3.Connection,
    rows: Iterable[KoRow],
    *,
    overwrite: bool,
    print_map: dict[str, int],
    existing_ko: dict[int, tuple[str, str, int]],
) -> int:
    updated = 0
    for row in rows:
        print_id = print_map.get(normalize_card_number(row.card_number))
        if not print_id:
            print(f"[SKIP] missing print for {row.card_number}")
            continue
        if upsert_ko_text(
            conn,
            print_id,
            row.name,
            row.effect,
            row.source_url,
            overwrite=overwrite,
            existing=existing_ko,
        ):
            updated += 1
    return updated


def import_from_pages(db_path: str, pages: list[str], page_file: str | None, *, timeout: float, overwrite: bool) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    session = build_session()
    print_map = load_print_map(conn)
    existing_ko = load_existing_ko(conn)

    updated = 0
    for page in iter_pages(pages, page_file):
        html = fetch_html(session, page, timeout=timeout)
        source_url = page if page.startswith("http") else f"{NAMU_BASE}/w/{quote(page)}"
        updated += import_rows(
            conn,
            parse_tables(html, source_url),
            overwrite=overwrite,
            print_map=print_map,
            existing_ko=existing_ko,
        )
    conn.commit()
    conn.close()
    return updated


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
