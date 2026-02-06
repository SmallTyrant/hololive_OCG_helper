#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import time
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


BASE = "https://namu.wiki"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _headers() -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }


def _session() -> requests.Session:
    s = requests.Session()
    cookie = os.getenv("NAMU_COOKIE", "").strip()
    if cookie:
        s.headers.update({"Cookie": cookie})
    return s


def fetch(session: requests.Session, url: str, timeout: float) -> str:
    r = session.get(url, headers=_headers(), timeout=timeout)
    r.raise_for_status()
    return r.text


def search_page_url(query: str, template: str) -> str:
    return template.format(query=requests.utils.quote(query, safe=""))


def resolve_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return f"{BASE}{href}"


def extract_first_match(html: str, query: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    # Find first /w/ link; prefer exact title match if possible
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        if "/w/" not in href:
            continue
        title = a.get_text(" ", strip=True)
        links.append((title, href))

    if not links:
        return None

    # exact or contains query
    for title, href in links:
        if title == query:
            return resolve_url(href)
    for title, href in links:
        if query in title:
            return resolve_url(href)

    return resolve_url(links[0][1])


def extract_content(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
        title = title.replace(" - 나무위키", "").strip()

    # Try common content containers, fallback to full text
    content = None
    for sel in ["article", "#content", ".wiki-content", ".wiki-article"]:
        el = soup.select_one(sel)
        if el:
            content = el.get_text("\n", strip=True)
            break
    if not content:
        content = soup.get_text("\n", strip=True)

    # Reduce excessive blank lines
    content = "\n".join([ln.strip() for ln in content.splitlines() if ln.strip()])
    return title, content


def ensure_table(conn: sqlite3.Connection) -> None:
    # no schema change; table already exists in current DBs
    pass


def upsert_ko(conn: sqlite3.Connection, print_id: int, title: str, content: str) -> None:
    ts = now_iso()
    # keep memo as full content; effect_text as short summary
    summary = content[:1000]
    conn.execute(
        """
        INSERT INTO card_texts_ko(print_id, name, effect_text, memo, source, updated_at)
        VALUES(?, ?, ?, ?, 'namuwiki', ?)
        ON CONFLICT(print_id) DO UPDATE SET
          name=excluded.name,
          effect_text=excluded.effect_text,
          memo=excluded.memo,
          source=excluded.source,
          updated_at=excluded.updated_at
        """,
        (print_id, title, summary, content, ts),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--delay", type=float, default=0.8, help="Delay between requests (seconds)")
    ap.add_argument("--max-cards", type=int, default=0, help="Max cards to process (0 = all)")
    ap.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout seconds")
    ap.add_argument("--search-url", default=f"{BASE}/Search?q={{query}}", help="Search URL template")
    ap.add_argument("--force", action="store_true", help="Overwrite existing namu entries")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    ensure_table(conn)

    rows = conn.execute(
        "SELECT print_id, card_number FROM prints ORDER BY print_id"
    ).fetchall()

    processed = 0
    session = _session()
    for r in rows:
        if args.max_cards and processed >= args.max_cards:
            break
        print_id = r["print_id"]
        card_no = (r["card_number"] or "").strip()
        if not card_no:
            continue

        if not args.force:
            existing = conn.execute(
                "SELECT source FROM card_texts_ko WHERE print_id=?",
                (print_id,),
            ).fetchone()
            if existing and (existing["source"] or "") == "namuwiki":
                continue

        search_url = search_page_url(card_no, args.search_url)
        try:
            html = fetch(session, search_url, args.timeout)
            page_url = extract_first_match(html, card_no)
            if not page_url:
                print(f"[SKIP] {card_no} no search result")
                continue

            time.sleep(args.delay)
            page_html = fetch(session, page_url, args.timeout)
            title, content = extract_content(page_html)
            if not content:
                print(f"[SKIP] {card_no} empty content")
                continue

            upsert_ko(conn, print_id, title or card_no, content)
            conn.commit()
            processed += 1
            print(f"[OK] {card_no} -> {title}")
        except Exception as ex:
            print(f"[ERROR] {card_no} {ex}")
        finally:
            time.sleep(args.delay)

    conn.close()
    print(f"[DONE] namu sync processed={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
