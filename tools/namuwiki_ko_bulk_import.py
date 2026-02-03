#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulk import Korean texts from NamuWiki by discovering subpages.

Example:
  python tools/namuwiki_ko_bulk_import.py --db data/hololive_ocg.sqlite
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import re
import sqlite3
import time
from typing import Iterable
from urllib.parse import quote, unquote

import requests

from tools.namuwiki_ko_common import (
    build_session,
    import_rows,
    load_existing_ko,
    load_print_map,
)
from tools.namuwiki_ko_scrape import NAMU_BASE, parse_tables


def extract_titles(html: str, base_title: str) -> list[str]:
    links = re.findall(r'href=\"(/w/[^\"]+)\"', html)
    titles: list[str] = []
    prefix = base_title + "/"
    for link in links:
        if not link.startswith("/w/"):
            continue
        title = unquote(link[3:])
        if title.startswith(prefix):
            titles.append(title)
    return titles


def iter_pages(pages: Iterable[str], page_file: str | None) -> Iterable[str]:
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


def fetch_html(session: requests.Session, url: str, timeout: float) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def discover_pages(
    session: requests.Session,
    *,
    base_title: str,
    timeout: float,
    include_base: bool,
    extra_pages: Iterable[str],
    max_pages: int | None,
) -> list[str]:
    candidates: list[str] = []
    if include_base:
        candidates.append(base_title)

    urls = [
        f"{NAMU_BASE}/w/{quote(base_title)}",
        f"{NAMU_BASE}/Search?q={quote(base_title + '/')}",
    ]
    for url in urls:
        try:
            html = fetch_html(session, url, timeout)
        except Exception:
            continue
        candidates.extend(extract_titles(html, base_title))

    for page in extra_pages:
        if page:
            candidates.append(page)

    # de-dupe preserving order
    seen = set()
    out: list[str] = []
    for title in candidates:
        if title in seen:
            continue
        seen.add(title)
        out.append(title)
        if max_pages and len(out) >= max_pages:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--base", default="홀로라이브 오피셜 카드 게임", help="Base NamuWiki page title")
    ap.add_argument("--include-base", action="store_true", help="Include the base page itself")
    ap.add_argument("--page", action="append", default=[], help="Extra page title or URL to include")
    ap.add_argument("--page-file", help="Text file containing page titles/URLs")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    ap.add_argument("--delay", type=float, default=0.3, help="Delay between page fetches (seconds)")
    ap.add_argument("--max-pages", type=int, default=None, help="Max pages to consider")
    ap.add_argument("--dry-run", action="store_true", help="List pages and exit without DB writes")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing Korean texts")
    ap.add_argument("--verbose", action="store_true", help="Log skipped pages")
    args = ap.parse_args()

    session = build_session()
    extra = list(iter_pages(args.page, args.page_file))
    titles = discover_pages(
        session,
        base_title=args.base,
        timeout=args.timeout,
        include_base=args.include_base,
        extra_pages=extra,
        max_pages=args.max_pages,
    )

    if not titles:
        print("[ERROR] no candidate pages found")
        return 1

    selected: list[tuple[str, str]] = []
    for title in titles:
        url = title if title.startswith("http") else f"{NAMU_BASE}/w/{quote(title)}"
        try:
            html = fetch_html(session, url, args.timeout)
        except Exception as exc:
            if args.verbose:
                print(f"[SKIP] {title} fetch failed: {exc}")
            continue
        rows = parse_tables(html, url)
        if rows:
            selected.append((title, html))
            print(f"[USE] {title} rows={len(rows)}")
        elif args.verbose:
            print(f"[SKIP] {title} no effect rows")
        time.sleep(max(args.delay, 0.0))

    if not selected:
        print("[ERROR] no pages with effect rows found")
        return 1

    if args.dry_run:
        print(f"[DONE] pages={len(selected)} (dry-run)")
        return 0

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    print_map = load_print_map(conn)
    existing_ko = load_existing_ko(conn)

    updated = 0
    for title, html in selected:
        url = title if title.startswith("http") else f"{NAMU_BASE}/w/{quote(title)}"
        rows = parse_tables(html, url)
        updated += import_rows(
            conn,
            rows,
            overwrite=args.overwrite,
            print_map=print_map,
            existing_ko=existing_ko,
        )
    conn.commit()
    conn.close()

    print(f"[DONE] pages={len(selected)} updated={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
