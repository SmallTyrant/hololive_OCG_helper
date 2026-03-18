#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

BASE_URL = "https://hololive-official-cardgame.com"
RARITY_FROM_FILE_RE = re.compile(r"_([A-Za-z0-9]+)(?:_\d+)?\.[A-Za-z0-9]+$")
CARD_SET_RE = re.compile(r"^([A-Za-z0-9]+)-\d+$")


@dataclass(frozen=True)
class MissingIllustration:
    illustration_id: int
    card_number: str
    rarity: str


def to_absolute_url(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        return f"{BASE_URL}{value}"
    return f"{BASE_URL}/{value}"


def parse_rarity_from_url(url: str) -> str | None:
    token = url.rsplit("/", 1)[-1]
    m = RARITY_FROM_FILE_RE.search(token)
    if not m:
        return None
    return m.group(1).upper()


def collect_missing_illustrations(conn: sqlite3.Connection) -> list[MissingIllustration]:
    rows = conn.execute(
        """
        SELECT illustration_id, card_number, rarity
        FROM card_illustrations
        WHERE image_url IS NULL OR TRIM(image_url) = ''
        ORDER BY card_number, rarity, illustration_id
        """
    ).fetchall()
    return [MissingIllustration(int(r[0]), r[1], (r[2] or "").strip().upper()) for r in rows]


def collect_print_urls_by_card(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
    rows = conn.execute(
        """
        SELECT card_number, image_url
        FROM prints
        WHERE image_url IS NOT NULL AND TRIM(image_url) != ''
        """
    ).fetchall()
    by_card: dict[str, dict[str, str]] = {}
    for card_number, raw_url in rows:
        absolute = to_absolute_url(raw_url)
        rarity = parse_rarity_from_url(absolute)
        if not rarity:
            continue
        by_card.setdefault(card_number, {})[rarity] = absolute
    return by_card


def apply_inferred_urls(conn: sqlite3.Connection, missing: Iterable[MissingIllustration]) -> tuple[int, list[tuple[MissingIllustration, str]]]:
    by_card = collect_print_urls_by_card(conn)
    updates: list[tuple[MissingIllustration, str]] = []
    for row in missing:
        candidate = by_card.get(row.card_number, {}).get(row.rarity)
        if not candidate:
            continue
        updates.append((row, candidate))

    if updates:
        conn.executemany(
            "UPDATE card_illustrations SET image_url=? WHERE illustration_id=?",
            [(url, row.illustration_id) for row, url in updates],
        )
        conn.commit()
    return len(updates), updates


def build_probe_candidates(card_number: str, rarity: str) -> list[str]:
    m = CARD_SET_RE.match(card_number)
    set_code = m.group(1) if m else ""
    folders: list[str] = []
    if set_code:
        folders.append(set_code)
    if rarity == "P" and "hPR" not in folders:
        folders.append("hPR")

    candidates: list[str] = []
    for folder in folders:
        candidates.append(f"{BASE_URL}/wp-content/images/cardlist/{folder}/{card_number}_{rarity}.png")
        if rarity == "P":
            for idx in range(2, 31):
                candidates.append(f"{BASE_URL}/wp-content/images/cardlist/{folder}/{card_number}_{rarity}_{idx:02d}.png")
    return candidates


def probe_one_missing(row: MissingIllustration, timeout: float) -> tuple[MissingIllustration, str] | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    for url in build_probe_candidates(row.card_number, row.rarity):
        try:
            resp = requests.get(url, headers=headers, allow_redirects=True, timeout=timeout, stream=True)
        except Exception:  # noqa: BLE001
            continue
        if resp.status_code == 200:
            return (row, url)
    return None


def discover_missing_urls(missing: Iterable[MissingIllustration], timeout: float, workers: int) -> list[tuple[MissingIllustration, str]]:
    rows = list(missing)
    if not rows:
        return []
    found: list[tuple[MissingIllustration, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        futures = [executor.submit(probe_one_missing, row, timeout) for row in rows]
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                found.append(result)
    return found


def apply_discovered_urls(conn: sqlite3.Connection, updates: list[tuple[MissingIllustration, str]]) -> int:
    if not updates:
        return 0
    conn.executemany(
        "UPDATE card_illustrations SET image_url=? WHERE illustration_id=?",
        [(url, row.illustration_id) for row, url in updates],
    )
    conn.commit()
    return len(updates)


def collect_all_image_urls(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT image_url FROM prints WHERE image_url IS NOT NULL AND TRIM(image_url) != ''
        UNION
        SELECT image_url FROM card_illustrations WHERE image_url IS NOT NULL AND TRIM(image_url) != ''
        """
    ).fetchall()
    return sorted({to_absolute_url(r[0]) for r in rows if (r[0] or "").strip()})


def check_url(session: requests.Session, url: str, timeout: float) -> tuple[str, int, str]:
    try:
        resp = session.head(url, allow_redirects=True, timeout=timeout)
        status = resp.status_code
        if status in (403, 405) or status >= 500:
            resp = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
            status = resp.status_code
        return (url, status, "")
    except Exception as exc:  # noqa: BLE001
        return (url, 0, str(exc))


def verify_urls(
    urls: list[str], workers: int, timeout: float
) -> tuple[list[tuple[str, int, str]], list[tuple[str, int, str]], list[tuple[str, int, str]]]:
    session = requests.Session()
    session.headers["User-Agent"] = "hocg-image-audit/1.0"

    ok: list[tuple[str, int, str]] = []
    blocked: list[tuple[str, int, str]] = []
    bad: list[tuple[str, int, str]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_url, session, url, timeout): url for url in urls}
        for fut in as_completed(futures):
            url, status, err = fut.result()
            if status >= 200 and status < 400:
                ok.append((url, status, err))
            elif status == 403:
                blocked.append((url, status, err))
            else:
                bad.append((url, status, err))

    return ok, blocked, bad


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit and patch card image URLs")
    parser.add_argument("--db", default="app/assets/hololive_ocg.sqlite", help="Path to SQLite DB")
    parser.add_argument("--apply", action="store_true", help="Apply inferred image_url updates")
    parser.add_argument("--verify", action="store_true", help="Run HTTP verification for all image URLs")
    parser.add_argument("--probe-missing", action="store_true", help="Probe official cardlist URLs for remaining missing rows")
    parser.add_argument("--workers", type=int, default=20, help="Concurrent workers for URL verification")
    parser.add_argument("--timeout", type=float, default=12.0, help="HTTP timeout (seconds)")
    parser.add_argument("--missing-report", default="", help="Write remaining missing rows to CSV file")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        missing_before = collect_missing_illustrations(conn)
        print(f"[INFO] Missing illustration image_url: {len(missing_before)}")

        if args.apply:
            updated_count, updates = apply_inferred_urls(conn, missing_before)
            print(f"[INFO] Inferred updates applied: {updated_count}")
            if updates:
                print("[INFO] Sample updates:")
                for row, url in updates[:20]:
                    print(f"  - {row.card_number} {row.rarity} -> {url}")

        if args.probe_missing:
            current_missing = collect_missing_illustrations(conn)
            discovered = discover_missing_urls(current_missing, timeout=args.timeout, workers=max(1, args.workers))
            discovered_count = apply_discovered_urls(conn, discovered)
            print(f"[INFO] Probed updates applied: {discovered_count}")
            if discovered:
                print("[INFO] Sample probed updates:")
                for row, url in discovered[:20]:
                    print(f"  - {row.card_number} {row.rarity} -> {url}")

        missing_after = collect_missing_illustrations(conn)
        print(f"[INFO] Missing illustration image_url after patch: {len(missing_after)}")

        if missing_after:
            by_rarity: dict[str, int] = {}
            for row in missing_after:
                by_rarity[row.rarity] = by_rarity.get(row.rarity, 0) + 1
            print("[INFO] Remaining missing by rarity:")
            for rarity, count in sorted(by_rarity.items(), key=lambda x: (-x[1], x[0])):
                print(f"  - {rarity}: {count}")

            if args.missing_report:
                report_path = Path(args.missing_report)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                with report_path.open("w", newline="", encoding="utf-8") as fp:
                    writer = csv.writer(fp)
                    writer.writerow(["illustration_id", "card_number", "rarity"])
                    for row in missing_after:
                        writer.writerow([row.illustration_id, row.card_number, row.rarity])
                print(f"[INFO] Missing report written: {report_path}")

        if args.verify:
            urls = collect_all_image_urls(conn)
            print(f"[INFO] Verifying URLs: {len(urls)}")
            ok, blocked, bad = verify_urls(urls, workers=max(1, args.workers), timeout=args.timeout)
            print(f"[INFO] URL check complete: ok={len(ok)} blocked={len(blocked)} bad={len(bad)}")
            if blocked:
                print("[INFO] 403-blocked URL samples:")
                for url, status, _ in blocked[:30]:
                    print(f"  - HTTP {status} :: {url}")
            if bad:
                print("[WARN] Broken URL samples:")
                for url, status, err in bad[:50]:
                    reason = err if err else f"HTTP {status}"
                    print(f"  - {reason} :: {url}")
                return 1

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
