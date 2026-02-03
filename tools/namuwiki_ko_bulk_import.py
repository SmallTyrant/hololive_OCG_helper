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
import html as html_lib
import re
import sqlite3
import time
from typing import Iterable
from urllib.parse import parse_qs, quote, unquote, urlparse

import requests
from bs4 import BeautifulSoup, FeatureNotFound

from tools.namuwiki_ko_common import (
    build_session,
    import_rows,
    load_existing_ko,
    load_print_map,
)
from tools.namuwiki_ko_scrape import NAMU_BASE, parse_tables

DEFAULT_EXTRA_PAGES = [
    "블루밍 레디언스",
    "퀀텟 스펙트럼",
    "엘리트 스파크",
    "큐리어스 유니버스",
    "인챈트 레갈리아",
    "아야카시 버밀리온",
]


def _is_relevant_title(title: str, base_title: str, *, match_substring: bool) -> bool:
    if title == base_title:
        return True
    if title.startswith(base_title + "/"):
        return True
    if title.endswith("/" + base_title):
        return True
    if match_substring and base_title in title:
        return True
    return False


def extract_titles(html: str, base_title: str, *, match_substring: bool) -> list[str]:
    links = re.findall(r'href=\"(/w/[^\"]+)\"', html)
    titles: list[str] = []
    for link in links:
        if not link.startswith("/w/"):
            continue
        title = unquote(link[3:])
        if _is_relevant_title(title, base_title, match_substring=match_substring):
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


def normalize_title(page: str) -> str | None:
    if not page:
        return None
    if page.startswith("http://") or page.startswith("https://"):
        parsed = urlparse(page)
        if parsed.path.startswith("/w/"):
            return unquote(parsed.path[3:])
        return None
    return page


def expand_card_subpages(pages: Iterable[str], *, include_card_subpages: bool) -> list[str]:
    out: list[str] = []
    seen = set()
    for page in pages:
        if page in seen:
            continue
        seen.add(page)
        out.append(page)
    if not include_card_subpages:
        return out
    for page in list(out):
        title = normalize_title(page)
        if not title:
            continue
        if title.endswith("/카드"):
            continue
        card_title = f"{title}/카드"
        if card_title not in seen:
            seen.add(card_title)
            out.append(card_title)
    return out


def fetch_html(session: requests.Session, url: str, timeout: float) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _extract_search_pages(html: str, query: str) -> list[str]:
    links = re.findall(r'href=\"(/Search\\?[^\"]+)\"', html)
    pages: list[str] = []
    for link in links:
        parsed = urlparse(link)
        qs = parse_qs(parsed.query)
        if qs.get("q", [None])[0] != query:
            continue
        pages.append(link)
    return pages


def _search_for_query(
    session: requests.Session,
    *,
    query: str,
    timeout: float,
    base_title: str,
    match_substring: bool,
    max_search_pages: int | None,
    parent_title: str | None = None,
) -> list[str]:
    candidates: list[str] = []
    if max_search_pages is None:
        max_pages = 200
        stop_on_empty = True
    else:
        max_pages = max_search_pages
        stop_on_empty = False
    empty_streak = 0
    seen_titles = set()
    for page in range(1, max_pages + 1):
        url = f"{NAMU_BASE}/Search?q={quote(query)}&page={page}"
        try:
            html = fetch_html(session, url, timeout)
        except Exception:
            continue
        if parent_title:
            found = _extract_descendants(html, parent_title)
        else:
            found = extract_titles(html, base_title, match_substring=match_substring)
        new = [t for t in found if t not in seen_titles]
        if new:
            candidates.extend(new)
            seen_titles.update(new)
            empty_streak = 0
        else:
            empty_streak += 1
        if stop_on_empty and empty_streak >= 2:
            break
    return candidates


def _extract_descendants(html: str, parent_title: str) -> list[str]:
    links = re.findall(r'href=\"(/w/[^\"]+)\"', html)
    titles: list[str] = []
    prefix = parent_title + "/"
    for link in links:
        if not link.startswith("/w/"):
            continue
        title = unquote(link[3:])
        if title.startswith(prefix):
            titles.append(title)
    return titles


def _extract_category_items(html: str) -> list[str]:
    links = re.findall(r'href=\"(/w/[^\"]+)\"', html)
    items: list[str] = []
    for link in links:
        if not link.startswith("/w/"):
            continue
        title = unquote(link[3:])
        if title.startswith("분류:"):
            continue
        if title.startswith("틀:"):
            continue
        if title.startswith("파일:"):
            continue
        if title.startswith("나무위키:"):
            continue
        items.append(title)
    # de-dupe preserve order
    seen = set()
    out: list[str] = []
    for t in items:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _extract_category_next_urls(html: str) -> list[str]:
    html = html_lib.unescape(html)
    links = re.findall(r'href=\"(/w/분류:[^\"]+?[&?]cfrom=[^\"]+)\"', html)
    if not links:
        links = re.findall(r'href=\"(/w/분류:[^\"]+?[&?]from=[^\"]+)\"', html)
    out: list[str] = []
    seen = set()
    for link in links:
        full = link if link.startswith("http") else f"{NAMU_BASE}{link}"
        if full in seen:
            continue
        seen.add(full)
        out.append(full)
    return out


def _extract_member_links(html: str, tags: Iterable[str]) -> list[str]:
    if "등장 홀로멤" not in html:
        return []
    try:
        soup = BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(html, "html.parser")
    tag_set = {t.strip() for t in tags if t and t.strip()}
    if not tag_set:
        return []
    links: list[str] = []
    for folding in soup.select("dl.wiki-folding"):
        dt = folding.find("dt")
        dd = folding.find("dd")
        if not dt or not dd:
            continue
        label = dt.get_text(" ", strip=True)
        if not any(tag in label for tag in tag_set):
            continue
        for a in dd.select("a[href^='/w/']"):
            href = a.get("href")
            if not href:
                continue
            title = unquote(href[3:])
            if title.startswith("분류:") or title.startswith("틀:") or title.startswith("파일:"):
                continue
            links.append(title)
    # de-dupe preserve order
    seen = set()
    out: list[str] = []
    for t in links:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _crawl_category(
    session: requests.Session,
    *,
    category: str,
    timeout: float,
    max_pages: int | None,
) -> list[str]:
    items: list[str] = []
    if category.startswith("http"):
        start_url = category
    else:
        start_url = f"{NAMU_BASE}/w/{quote(category)}"
    queue = [start_url]
    seen_urls = set()
    pages = 0
    while queue:
        url = queue.pop(0)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            html = fetch_html(session, url, timeout)
        except Exception:
            continue
        items.extend(_extract_category_items(html))
        for next_url in _extract_category_next_urls(html):
            if next_url not in seen_urls:
                queue.append(next_url)
        pages += 1
        if max_pages and pages >= max_pages:
            break
    # de-dupe preserve order
    seen = set()
    out: list[str] = []
    for t in items:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def discover_pages(
    session: requests.Session,
    *,
    base_title: str,
    timeout: float,
    include_base: bool,
    extra_pages: Iterable[str],
    max_pages: int | None,
    match_substring: bool,
    max_search_pages: int | None,
    include_descendants: bool,
    max_depth: int | None,
    category_pages: Iterable[str],
    max_category_pages: int | None,
) -> list[str]:
    candidates: list[str] = []
    if include_base:
        candidates.append(base_title)

    for category in category_pages:
        if not category:
            continue
        candidates.extend(
            _crawl_category(
                session,
                category=category,
                timeout=timeout,
                max_pages=max_category_pages,
            )
        )

    base_url = f"{NAMU_BASE}/w/{quote(base_title)}"
    try:
        html = fetch_html(session, base_url, timeout)
        candidates.extend(extract_titles(html, base_title, match_substring=match_substring))
    except Exception:
        pass

    for query in [base_title, base_title + "/"]:
        candidates.extend(
            _search_for_query(
                session,
                query=query,
                timeout=timeout,
                base_title=base_title,
                match_substring=match_substring,
                max_search_pages=max_search_pages,
            )
        )

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

    if not include_descendants:
        return out

    queue: list[tuple[str, int]] = [(t, 0) for t in out]
    while queue:
        title, depth = queue.pop(0)
        if max_depth is not None and depth >= max_depth:
            continue
        if not (title.startswith(base_title + "/") or title.endswith("/" + base_title)):
            continue
        url = title if title.startswith("http") else f"{NAMU_BASE}/w/{quote(title)}"
        try:
            html = fetch_html(session, url, timeout)
        except Exception:
            continue
        for child in _extract_descendants(html, title):
            if child in seen:
                continue
            seen.add(child)
            out.append(child)
            queue.append((child, depth + 1))
            if max_pages and len(out) >= max_pages:
                return out
        # Also search for deeper descendants via search results
        for child in _search_for_query(
            session,
            query=title + "/",
            timeout=timeout,
            base_title=base_title,
            match_substring=True,
            max_search_pages=max_search_pages,
            parent_title=title,
        ):
            if child in seen:
                continue
            seen.add(child)
            out.append(child)
            queue.append((child, depth + 1))
            if max_pages and len(out) >= max_pages:
                return out
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--base", default="홀로라이브 오피셜 카드 게임", help="Base NamuWiki page title")
    ap.add_argument("--include-base", action="store_true", help="Include the base page itself")
    ap.add_argument("--no-match-substring", action="store_true", help="Only include titles starting/ending with base title")
    ap.add_argument("--no-descendants", action="store_true", help="Do not scan subpages of matched pages")
    ap.add_argument("--max-depth", type=int, default=None, help="Max descendant depth (default: unlimited)")
    ap.add_argument("--max-search-pages", type=int, default=None, help="Max search result pages to scan (default: auto-until-empty)")
    ap.add_argument("--no-category", action="store_true", help="Do not scan category pages")
    ap.add_argument("--no-card-subpages", action="store_true", help="Do not add '/카드' subpages")
    ap.add_argument("--no-expand-members", action="store_true", help="Do not expand 등장 홀로멤 member lists")
    ap.add_argument("--member-tag", action="append", default=["#JP"], help="Tag label to expand (e.g. #JP)")
    ap.add_argument("--category", action="append", default=[], help="Extra category page title or URL")
    ap.add_argument("--max-category-pages", type=int, default=30, help="Max category pages to scan")
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
    for title in DEFAULT_EXTRA_PAGES:
        if title not in extra:
            extra.append(title)
    extra = expand_card_subpages(extra, include_card_subpages=not args.no_card_subpages)
    categories = list(args.category)
    if not args.no_category:
        categories.append(f"분류:{args.base}")
    titles = discover_pages(
        session,
        base_title=args.base,
        timeout=args.timeout,
        include_base=args.include_base,
        extra_pages=extra,
        max_pages=args.max_pages,
        match_substring=not args.no_match_substring,
        max_search_pages=args.max_search_pages,
        include_descendants=not args.no_descendants,
        max_depth=args.max_depth,
        category_pages=categories,
        max_category_pages=args.max_category_pages,
    )

    if not titles:
        print("[ERROR] no candidate pages found")
        return 1

    member_tags = [t for t in args.member_tag if t]

    selected: list[tuple[str, str]] = []
    pending = list(titles)
    seen_titles = set(titles)
    while pending:
        title = pending.pop(0)
        url = title if title.startswith("http") else f"{NAMU_BASE}/w/{quote(title)}"
        try:
            html = fetch_html(session, url, args.timeout)
        except Exception as exc:
            if args.verbose:
                print(f"[SKIP] {title} fetch failed: {exc}")
            continue
        if not args.no_expand_members:
            for member in _extract_member_links(html, member_tags):
                if member in seen_titles:
                    continue
                seen_titles.add(member)
                pending.append(member)
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
