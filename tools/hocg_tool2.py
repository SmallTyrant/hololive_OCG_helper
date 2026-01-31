#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hocg_tool.py (fixed parser + safer upsert)
- Prevents "CARDLIST ーカードリストー" name pollution
- Skips non-detail pages (must contain カードナンバー with valid card_no)
- Prevents silent overwrites when card_number duplicates happen
- Keeps progress logs for Android/Pydroid

Requirements:
  pip install requests beautifulsoup4
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup


BASE = "https://hololive-official-cardgame.com"
CARDSEARCH_BASE = f"{BASE}/cardlist/cardsearch/"

# card number examples: hBP04-002, hSD05-009, etc.
CARDNO_RE = re.compile(r"\b[hH][A-Za-z]{1,5}\d{2}-\d{3}\b")

# list page links: /cardlist/?id=123&view=text
DETAIL_ID_RE = re.compile(r"/cardlist/\?id=(\d+)")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def log(msg: str, verbose: bool) -> None:
    if verbose:
        print(msg, flush=True)


_thread_local = threading.local()


def _get_thread_session() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        _thread_local.session = sess
    return sess


def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta(
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prints(
          print_id INTEGER PRIMARY KEY AUTOINCREMENT,
          card_number TEXT NOT NULL UNIQUE,
          set_code TEXT,
          rarity TEXT,
          color TEXT,
          card_type TEXT,
          product TEXT,
          name_ja TEXT,
          image_url TEXT,
          image_sha256 TEXT,
          detail_id INTEGER,
          detail_url TEXT,
          updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_texts_ja(
          print_id INTEGER PRIMARY KEY,
          name TEXT,
          effect_text TEXT,
          raw_text TEXT,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(print_id) REFERENCES prints(print_id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS card_texts_ko(
          print_id INTEGER PRIMARY KEY,
          name TEXT,
          effect_text TEXT,
          memo TEXT,
          source TEXT DEFAULT 'manual',
          version INTEGER DEFAULT 1,
          updated_at TEXT NOT NULL,
          FOREIGN KEY(print_id) REFERENCES prints(print_id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tags(
          tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
          tag TEXT NOT NULL UNIQUE,
          normalized TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS print_tags(
          print_id INTEGER NOT NULL,
          tag_id INTEGER NOT NULL,
          PRIMARY KEY(print_id, tag_id),
          FOREIGN KEY(print_id) REFERENCES prints(print_id) ON DELETE CASCADE,
          FOREIGN KEY(tag_id) REFERENCES tags(tag_id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS raw_snapshots(
          snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
          print_id INTEGER NOT NULL,
          fetched_at TEXT NOT NULL,
          url TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          raw_html BLOB NOT NULL,
          FOREIGN KEY(print_id) REFERENCES prints(print_id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def normalize_tag(tag: str) -> str:
    t = (tag or "").strip()
    if t.startswith("#"):
        t = t[1:]
    t = re.sub(r"\s+", "", t).lower()
    return t


def upsert_tag(conn: sqlite3.Connection, tag: str) -> int:
    norm = normalize_tag(tag)
    conn.execute(
        """
        INSERT INTO tags(tag, normalized)
        VALUES(?, ?)
        ON CONFLICT(tag) DO UPDATE SET normalized=excluded.normalized
        """,
        (tag, norm),
    )
    row = conn.execute("SELECT tag_id FROM tags WHERE tag=?", (tag,)).fetchone()
    return int(row[0])


def replace_print_tags(conn: sqlite3.Connection, print_id: int, tags: List[str]) -> None:
    conn.execute("DELETE FROM print_tags WHERE print_id=?", (print_id,))
    for t in tags:
        tid = upsert_tag(conn, t)
        conn.execute(
            "INSERT OR IGNORE INTO print_tags(print_id, tag_id) VALUES(?, ?)",
            (print_id, tid),
        )


def upsert_print(conn: sqlite3.Connection, card_number: str, detail: dict) -> int:
    card_number = card_number.strip()
    set_code = detail.get("set_code") or ""
    rarity = detail.get("rarity") or ""
    color = detail.get("color") or ""
    card_type = detail.get("card_type") or ""
    product = detail.get("product") or ""
    name_ja = detail.get("name") or ""
    img_url = detail.get("image_url") or ""
    detail_id = detail.get("detail_id")
    detail_url = detail.get("detail_url") or ""

    img_sha = sha256_text(img_url) if img_url else ""

    conn.execute(
        """
        INSERT INTO prints(card_number,set_code,rarity,color,card_type,product,name_ja,image_url,image_sha256,detail_id,detail_url,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(card_number) DO UPDATE SET
          set_code=excluded.set_code,
          rarity=excluded.rarity,
          color=excluded.color,
          card_type=excluded.card_type,
          product=excluded.product,
          name_ja=excluded.name_ja,
          image_url=excluded.image_url,
          image_sha256=excluded.image_sha256,
          detail_id=excluded.detail_id,
          detail_url=excluded.detail_url,
          updated_at=excluded.updated_at
        """,
        (
            card_number,
            set_code,
            rarity,
            color,
            card_type,
            product,
            name_ja,
            img_url,
            img_sha,
            detail_id,
            detail_url,
            now_iso(),
        ),
    )
    row = conn.execute("SELECT print_id FROM prints WHERE card_number=?", (card_number,)).fetchone()
    return int(row[0])


def upsert_text_ja(conn: sqlite3.Connection, print_id: int, name: str, raw_text: str) -> None:
    # effect_text는 raw_text 기반으로 일단 동일값(뷰어에서 사용)
    conn.execute(
        """
        INSERT INTO card_texts_ja(print_id,name,effect_text,raw_text,updated_at)
        VALUES(?,?,?,?,?)
        ON CONFLICT(print_id) DO UPDATE SET
          name=excluded.name,
          effect_text=excluded.effect_text,
          raw_text=excluded.raw_text,
          updated_at=excluded.updated_at
        """,
        (print_id, name, raw_text, raw_text, now_iso()),
    )


EXP_RE = re.compile(r"expansion=([A-Za-z0-9]+)")


def parse_expansion_codes(html: bytes) -> Set[str]:
    text = html.decode("utf-8", errors="ignore")
    exps: Set[str] = set()
    for m in EXP_RE.finditer(text):
        exps.add(m.group(1))
    return exps


@dataclass
class ListItem:
    card_id: str
    card_number: str


def parse_list_page(html: bytes) -> List[ListItem]:
    """
    From cardsearch/?...&view=text pages:
    - Find anchors to detail pages: a[href*='cardlist/?id=']
    - Pull the card number from the anchor's visible text (view=text makes it reliable)
    """
    soup = BeautifulSoup(html, "html.parser")
    items: List[ListItem] = []
    for a in soup.select("a[href*='cardlist/?id=']"):
        href = a.get("href") or ""
        m = DETAIL_ID_RE.search(href)
        if not m:
            continue
        card_id = m.group(1)

        text = " ".join(a.get_text(" ", strip=True).split())
        m_no = CARDNO_RE.search(text)
        if not m_no:
            continue
        card_no = m_no.group(0)

        items.append(ListItem(card_id=card_id, card_number=card_no))
    return items


def _extract_field_by_label(text: str, label: str) -> str:
    pat = re.compile(rf"{re.escape(label)}\s*[：:]\s*(.+)")
    for line in text.splitlines():
        line = line.strip()
        m = pat.search(line)
        if m:
            return m.group(1).strip()
    return ""


def normalize_raw_text(text: str, *, remove_private: bool = False) -> str:
    """Normalize raw page text for stable downstream parsing/UI.

    - Merge label/value pairs onto one line for: カードタイプ, レアリティ, 色, LIFE, HP
      (단, 다음 줄이 또 다른 라벨이면 값이 아니므로 병합하지 않음)
    - Remove the 収録商品 section block (it is noisy for offline viewer)
      (단, 페이지 네비/푸터에 등장하는 収録商品은 제거하지 않음)
    """
    import re as _re

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out: list[str] = []
    i = 0

    MERGE_LABELS = {"カードタイプ", "レアリティ", "色", "LIFE", "HP", "カードナンバー"}
    REMOVE_LABELS = {"イラストレーター名", "カードナンバー", "収録商品"} if remove_private else set()

    # "다음 줄이 라벨이면 병합 금지"용 라벨 집합
    ALL_LABELS = set(MERGE_LABELS) | {
        "タグ", "推しスキル", "SP推しスキル", "Bloomレベル",
        "アーツ", "バトンタッチ", "エクストラ", "イラストレーター名",
        "カードナンバー", "キーワード", "収録商品",
    }

    SECTION_START_RE = _re.compile(
        r"^(カードタイプ|レアリティ|色|LIFE|HP|推しスキル|SP推しスキル|アーツ|バトンタッチ|エクストラ|イラストレーター名|カードナンバー|キーワード)"
    )

    def _normalize_label(line: str) -> str:
        return line.replace("：", "").replace(":", "").strip()

    while i < len(lines):
        line = lines[i]
        label = _normalize_label(line)

        if label in REMOVE_LABELS:
            i += 1
            if i < len(lines) and _normalize_label(lines[i]) not in ALL_LABELS:
                i += 1
            continue

        if label == "タグ":
            tags = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("#"):
                tags.append(lines[j].strip())
                j += 1
            if tags:
                out.append("タグ")
                out.append(" ".join(tags))
                i = j
                continue

        def _is_label_line(s: str) -> bool:
            s = _normalize_label(s)
            if s in ALL_LABELS:
                return True
            for lbl in ALL_LABELS:
                if s.startswith(lbl + " "):
                    return True
            return False

        # merge label + next line value (next가 라벨이면 병합하지 않음)
        if label in MERGE_LABELS and i + 1 < len(lines):
            nxt = lines[i + 1]
            if _is_label_line(nxt):
                out.append(label)
                i += 1
                continue
            out.append(f"{label} {nxt}")
            i += 2
            continue

        # remove 収録商品 section (only if it looks like real "product" section)
        if label == "収録商品":
            look = " ".join(lines[i + 1:i + 7])
            is_real_section = any(k in look for k in [
                "Accessories", "Boosters", "発売日", "【使用可能カード】",
                "スタートデッキ", "ブースターパック", "エントリーカップ",
            ])

            if not is_real_section:
                # nav/footer "収録商品" -> keep it
                out.append(label)
                i += 1
                continue

            # real product section -> skip until next section header
            i += 1
            while i < len(lines) and not SECTION_START_RE.match(lines[i]):
                i += 1
            continue

        out.append(label if label != line and label in ALL_LABELS else line)
        i += 1

    return "\n".join(out)


def extract_detail_text(soup: BeautifulSoup) -> str:
    """
    Prefer the card detail container to avoid navigation/menu noise.
    """
    detail_root = soup.select_one(".cardlist-Detail")
    if detail_root is None:
        return soup.get_text("\n", strip=True)
    return detail_root.get_text("\n", strip=True)


def parse_detail(detail_html: bytes, fallback_card_no: str, verbose: bool) -> Optional[dict]:
    soup = BeautifulSoup(detail_html, "html.parser")

    raw_full = extract_detail_text(soup)
    raw = normalize_raw_text(raw_full)

    # 카드 번호
    card_no = ""
    cn = _extract_field_by_label(raw_full, "カードナンバー")
    m = CARDNO_RE.search(cn) if cn else None
    if m:
        card_no = m.group(0)
    else:
        m2 = CARDNO_RE.search(raw_full)
        if m2:
            card_no = m2.group(0)

    if not card_no:
        if verbose:
            print("[WARN] detail page missing card number -> SKIP", flush=True)
        return None

    # 카드명(ja)
    name = _extract_field_by_label(raw_full, "カード名")
    if not name:
        title = (soup.title.get_text(" ", strip=True) if soup.title else "").strip()
        if title:
            name = title.split("|", 1)[0].strip()

    if name and "CARDLIST" in name.upper():
        name = ""

    rarity = _extract_field_by_label(raw_full, "レアリティ")
    color = _extract_field_by_label(raw_full, "色")
    card_type = _extract_field_by_label(raw_full, "カードタイプ")
    product = _extract_field_by_label(raw_full, "収録商品")

    tags: List[str] = []
    for a in soup.select("a"):
        t = a.get_text(" ", strip=True)
        if t.startswith("#") and len(t) >= 2:
            tags.append(t)

    image_url = ""
    for img in soup.select("img"):
        src = img.get("src") or ""
        if "/wp-content/images/cardlist/" in src:
            image_url = src
            break

    return {
        "name": name,
        "card_number": card_no or fallback_card_no,
        "card_type": card_type,
        "rarity": rarity,
        "product": product,
        "color": color,
        "tags": tags,
        "image_url": image_url,
        "raw_text": normalize_raw_text(raw_full, remove_private=True),
    }


def detect_pagination_param(html: bytes) -> str:
    # Try to detect 'page' param from links, fallback to 'page'
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href*='page=']"):
        href = a.get("href") or ""
        if "page=" in href:
            return "page"
    return "page"

def detect_total_count(html: bytes) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    num_el = soup.select_one(".cardlist-Result_Target_Num .num")
    if num_el:
        try:
            return int(num_el.get_text(strip=True))
        except ValueError:
            pass

    text = soup.get_text("\n", strip=True)
    m = re.search(r"検索結果\s*(\d+)\s*件", text)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def detect_max_page(html: bytes, page_param: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    max_page = 0
    for a in soup.select(f"a[href*='{page_param}=']"):
        href = a.get("href") or ""
        m = re.search(rf"[?&]{re.escape(page_param)}=(\d+)", href)
        if not m:
            continue
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if n > max_page:
            max_page = n
    return max_page or None


def build_list_url(expansion: str | None, page: int, page_param: str) -> str:
    # always use view=text so card numbers appear in anchor text reliably
    if expansion:
        base = f"{CARDSEARCH_BASE}?expansion={expansion}&view=text"
    else:
        base = f"{CARDSEARCH_BASE}?view=text"
    if page <= 1:
        return base
    return f"{base}&{page_param}={page}"


def fetch(session: requests.Session, url: str, verbose: bool) -> bytes:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    r = session.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.content


def _fetch_detail_worker(detail_url: str, card_number: str, card_id: str, delay: float, verbose: bool):
    if delay:
        time.sleep(delay)
    sess = _get_thread_session()
    detail_html = fetch(sess, detail_url, verbose)
    detail = parse_detail(detail_html, fallback_card_no=card_number, verbose=verbose)
    return {
        "detail": detail,
        "detail_url": detail_url,
        "card_number": card_number,
        "card_id": card_id,
    }


def process_list_page(expansion: str | None, page: int, html: bytes, args, session: requests.Session, conn: sqlite3.Connection) -> Tuple[int, int]:
    items = parse_list_page(html)
    exp_label = expansion if expansion else "ALL"
    log(f"[PAGE] exp={exp_label} page={page} items={len(items)} seen_total={args._seen_total}", True)

    new_items = 0
    def _log_progress(idx: int, total_in_page: int):
        elapsed = max(1e-6, time.time() - args._t0)
        rate = args._seen_total / elapsed
        log(
            f"[PROGRESS] exp={exp_label} page={page} ({idx}/{total_in_page}) total={args._seen_total} rate={rate:.2f}/s",
            True,
        )
        if args._total_items:
            total_seen = max(1, args._seen_total)
            progress = min(1.0, max(0.0, total_seen / args._total_items))
            eta = int((args._total_items - total_seen) / rate) if rate > 0 else 0
            log(
                f"[PROGRESS_PCT] stage=scrape exp={exp_label} pct={progress*100:.2f} eta={eta}",
                True,
            )

    def _handle_detail(detail, it_card_number: str, it_card_id: str, detail_url: str):
        nonlocal new_items
        if not detail:
            log(f"[SKIP] exp={exp_label} id={it_card_id} (no valid card detail)", True)
            return 0

        detail["detail_id"] = int(it_card_id)
        detail["detail_url"] = detail_url
        if expansion:
            detail["set_code"] = expansion
        else:
            card_no = (detail.get("card_number") or it_card_number or "").strip()
            detail["set_code"] = card_no.split("-", 1)[0] if "-" in card_no else ""

        print_id = upsert_print(conn, detail.get("card_number") or it_card_number, detail)
        upsert_text_ja(conn, print_id, detail.get("name") or "", detail.get("raw_text") or "")
        replace_print_tags(conn, print_id, detail.get("tags") or [])

        return 1

    if args.workers > 1:
        futures = []
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for idx, it in enumerate(items, 1):
                if it.card_id in args._seen_ids:
                    continue
                args._seen_ids.add(it.card_id)
                new_items += 1

                if idx == 1 or idx % 20 == 0 or idx == len(items):
                    _log_progress(idx, len(items))

                detail_url = f"{BASE}/cardlist/?id={it.card_id}&view=text"
                futures.append(
                    ex.submit(
                        _fetch_detail_worker,
                        detail_url,
                        it.card_number,
                        it.card_id,
                        args.delay,
                        args.verbose,
                    )
                )

            for f in as_completed(futures):
                try:
                    result = f.result()
                except Exception as e:
                    log(f"[ERROR] fetch detail failed: exp={exp_label} err={e}", True)
                    continue

                detail = result["detail"]
                detail_url = result["detail_url"]
                card_number = result["card_number"]
                card_id = result["card_id"]
                added = _handle_detail(detail, card_number, card_id, detail_url)
                if added:
                    args._seen_total += 1
                    if args.max_cards and args._seen_total >= args.max_cards:
                        return new_items, 1
                    if args._seen_total % 50 == 0:
                        elapsed = max(1e-6, time.time() - args._t0)
                        rate = args._seen_total / elapsed
                        log(f"[PROGRESS] total={args._seen_total} rate={rate:.2f}/s", True)
                        conn.commit()
    else:
        for idx, it in enumerate(items, 1):
            if it.card_id in args._seen_ids:
                continue
            args._seen_ids.add(it.card_id)
            new_items += 1

            if idx == 1 or idx % 20 == 0 or idx == len(items):
                _log_progress(idx, len(items))

            detail_url = f"{BASE}/cardlist/?id={it.card_id}&view=text"
            time.sleep(args.delay)

            try:
                detail_html = fetch(session, detail_url, args.verbose)
            except Exception as e:
                log(f"[ERROR] fetch detail failed: exp={exp_label} {it.card_number} id={it.card_id} err={e}", True)
                continue

            detail = parse_detail(detail_html, fallback_card_no=it.card_number, verbose=args.verbose)
            added = _handle_detail(detail, it.card_number, it.card_id, detail_url)
            if added:
                args._seen_total += 1
                if args.max_cards and args._seen_total >= args.max_cards:
                    return new_items, 1

                if args._seen_total % 50 == 0:
                    elapsed = max(1e-6, time.time() - args._t0)
                    rate = args._seen_total / elapsed
                    log(f"[PROGRESS] total={args._seen_total} rate={rate:.2f}/s", True)
                    conn.commit()

    conn.commit()
    return new_items, 0


def scrape_expansion(conn: sqlite3.Connection, session: requests.Session, expansion: str | None, args) -> int:
    first_url = build_list_url(expansion, 1, "page")
    first_html = fetch(session, first_url, args.verbose)

    page_param = detect_pagination_param(first_html)
    exp_label = expansion if expansion else "ALL"
    log(f"[PAGINATION] exp={exp_label} param='{page_param}'", True)
    total_pages = detect_max_page(first_html, page_param)
    args._total_pages = total_pages
    if total_pages:
        log(f"[PAGES] exp={exp_label} total_pages={total_pages}", True)
    total_items = detect_total_count(first_html)
    args._total_items = total_items
    if total_items:
        log(f"[TOTAL] exp={exp_label} items={total_items}", True)

    for page in range(1, args.max_pages + 1):
        url = build_list_url(expansion, page, page_param)
        html = first_html if page == 1 else fetch(session, url, args.verbose)
        new_items, stop = process_list_page(expansion, page, html, args, session, conn)
        if stop:
            return 1
        if new_items == 0:
            log(f"[DONE] exp={expansion} no new items on page {page}", args.verbose)
            break
    return 0


def cmd_scrape(args) -> int:
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    init_db(conn)

    args._seen_ids = set()
    args._seen_total = 0
    args._t0 = time.time()

    session = requests.Session()

    if args.expansion == "all":
        exps = sorted(parse_expansion_codes(fetch(session, f"{CARDSEARCH_BASE}?view=text", args.verbose)))
        if exps:
            log(f"[INFO] expansions={len(exps)}", True)
            for exp in exps:
                if args.max_cards and args._seen_total >= args.max_cards:
                    break
                log(f"[EXP] {exp}", True)
                stop = scrape_expansion(conn, session, exp, args)
                if stop:
                    break
        else:
            # Fallback: crawl all cards without expansion filter
            log("[WARN] expansions not found; fallback to ALL cards", True)
            scrape_expansion(conn, session, None, args)
    else:
        scrape_expansion(conn, session, args.expansion, args)

    conn.commit()
    conn.close()
    return 0


def cmd_list_exps(args) -> int:
    session = requests.Session()
    html = fetch(session, f"{CARDSEARCH_BASE}?view=text", args.verbose)
    exps = sorted(parse_expansion_codes(html))
    for e in exps:
        print(e)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list-exps", help="List expansion codes")
    p.set_defaults(func=cmd_list_exps)
    p.add_argument("--verbose", action="store_true")

    s = sub.add_parser("scrape", help="Scrape one expansion")
    s.set_defaults(func=cmd_scrape)
    s.add_argument("--expansion", default="all", help="Expansion code (or 'all' if your build supports it)")
    s.add_argument("--delay", type=float, default=0.6, help="Delay seconds between detail fetches")
    s.add_argument("--workers", type=int, default=1, help="Parallel fetch workers (default: 1)")
    s.add_argument("--max-pages", type=int, default=999)
    s.add_argument("--max-cards", type=int, default=0)
    s.add_argument("--verbose", action="store_true")

    args = ap.parse_args()

    if args.cmd == "scrape":
        print(f"[START] db={args.db} delay={args.delay}s max_pages={args.max_pages} max_cards={args.max_cards}", flush=True)

    if args.cmd == "scrape" and args.expansion == "all":
        # If you want: iterate over expansions. Keeping simple here.
        # Users can run list-exps then scrape each exp.
        pass

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
