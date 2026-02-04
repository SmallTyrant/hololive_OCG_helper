#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import re
import sqlite3
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_raw_text(text: str) -> str:
    if not text:
        return text

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    NOISE_EXACT = {
        "MENU",
        "CLOSE",
        "FOR BEGINNERS",
        "RULE/Q&A",
        "NEWS",
        "PRODUCT",
        "EVENT",
        "SHOP",
        "CARD LIST",
        "DECK RECIPE",
        "TOP",
        "CARDLIST",
        "カードリスト",
        "ーカードリストー",
    }

    def _normalize_label(line: str) -> str:
        return line.replace("：", "").replace(":", "").strip()

    MERGE_LABELS = {"カードタイプ", "レアリティ", "色", "LIFE", "HP", "カードナンバー"}
    REMOVE_LABELS = {"イラストレーター名", "カードナンバー", "収録商品"}
    ALL_LABELS = set(MERGE_LABELS) | {
        "タグ", "推しスキル", "SP推しスキル", "Bloomレベル",
        "アーツ", "バトンタッチ", "エクストラ",
        "イラストレーター名", "カードナンバー", "収録商品",
        "キーワード",
    }

    SECTION_START_RE = re.compile(
        r"^(カードタイプ|レアリティ|色|LIFE|HP|推しスキル|SP推しスキル|"
        r"Bloomレベル|アーツ|バトンタッチ|エクストラ|"
        r"イラストレーター名|カードナンバー|キーワード)"
    )

    cleaned: list[str] = []
    for line in lines:
        label = _normalize_label(line)
        if label in NOISE_EXACT:
            continue
        cleaned.append(line)

    # Keep the last meaningful line before the first section label as title
    first_label_idx = None
    for i, line in enumerate(cleaned):
        if _normalize_label(line) in ALL_LABELS:
            first_label_idx = i
            break

    if first_label_idx is not None and first_label_idx > 0:
        title = None
        for j in range(first_label_idx - 1, -1, -1):
            cand = cleaned[j]
            cand_label = _normalize_label(cand)
            if cand_label in ALL_LABELS:
                continue
            if cand_label in NOISE_EXACT:
                continue
            if cand.startswith("#"):
                continue
            title = cand
            break
        cleaned = ([title] if title else []) + cleaned[first_label_idx:]

    out: list[str] = []
    i = 0
    while i < len(cleaned):
        line = cleaned[i]
        label = _normalize_label(line)

        if label in REMOVE_LABELS:
            i += 1
            if i < len(cleaned) and _normalize_label(cleaned[i]) not in ALL_LABELS:
                i += 1
            continue

        if label == "タグ":
            tags = []
            j = i + 1
            while j < len(cleaned) and cleaned[j].strip().startswith("#"):
                tags.append(cleaned[j].strip())
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
        if label in MERGE_LABELS and i + 1 < len(cleaned):
            nxt = cleaned[i + 1]
            if _is_label_line(nxt):
                out.append(label)
                i += 1
                continue
            out.append(f"{label} {nxt}")
            i += 2
            continue

        # remove 収録商品 section (when it looks like real product block)
        if label == "収録商品":
            look = " ".join(cleaned[i + 1:i + 7])
            is_real_section = any(k in look for k in [
                "Accessories", "Boosters", "発売日", "【使用可能カード】",
                "スタートデッキ", "ブースターパック", "エントリーカップ",
            ])
            if not is_real_section:
                out.append(label)
                i += 1
                continue

            i += 1
            while i < len(cleaned) and not SECTION_START_RE.match(_normalize_label(cleaned[i])):
                i += 1
            continue

        out.append(label if label != line and label in ALL_LABELS else line)
        i += 1

    refined = "\n".join(out).strip()
    return refined if refined else text


def _refine_chunk(rows: list[tuple[int, str]]) -> tuple[int, list[tuple[int, str]]]:
    updates: list[tuple[int, str]] = []
    for print_id, raw_text in rows:
        raw = raw_text or ""
        cleaned = normalize_raw_text(raw)
        if cleaned != raw:
            updates.append((print_id, cleaned))
    return len(rows), updates


def refine_db(db_path: str, jobs: int) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.execute("PRAGMA temp_store=MEMORY;")

    total = conn.execute("SELECT COUNT(*) FROM card_texts_ja").fetchone()[0]
    updated = 0
    seen = 0
    t0 = datetime.now().timestamp()
    chunk_size = 1000

    def _apply_updates(updates: list[tuple[int, str]]) -> None:
        if not updates:
            return
        ts = now_iso()
        batch = [(cleaned, cleaned, ts, pid) for pid, cleaned in updates]
        conn.executemany(
            """
            UPDATE card_texts_ja
            SET raw_text=?, effect_text=?, updated_at=?
            WHERE print_id=?
            """,
            batch,
        )

    cursor = conn.execute("SELECT print_id, raw_text FROM card_texts_ja")
    if jobs <= 1:
        for r in cursor:
            seen += 1
            raw = r["raw_text"] or ""
            cleaned = normalize_raw_text(raw)
            if cleaned != raw:
                _apply_updates([(r["print_id"], cleaned)])
                updated += 1
            if seen % 500 == 0 or seen == total:
                elapsed = max(1e-6, datetime.now().timestamp() - t0)
                pct = (seen / total) * 100 if total else 100.0
                eta = int(elapsed * (total - seen) / seen) if seen > 0 else 0
                print(f"[REFINE] {seen}/{total} updated={updated}", flush=True)
                print(f"[PROGRESS_PCT] stage=refine pct={pct:.2f} eta={eta}", flush=True)
    else:
        futures = []
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            while True:
                rows = cursor.fetchmany(chunk_size)
                if not rows:
                    break
                chunk = [(r["print_id"], r["raw_text"]) for r in rows]
                futures.append(ex.submit(_refine_chunk, chunk))

                if len(futures) >= jobs * 2:
                    for f in as_completed(futures[:jobs]):
                        processed, updates = f.result()
                        seen += processed
                        if updates:
                            _apply_updates(updates)
                            updated += len(updates)
                        futures.remove(f)
                        if seen % 500 == 0 or seen == total:
                            elapsed = max(1e-6, datetime.now().timestamp() - t0)
                            pct = (seen / total) * 100 if total else 100.0
                            eta = int(elapsed * (total - seen) / seen) if seen > 0 else 0
                            print(f"[REFINE] {seen}/{total} updated={updated}", flush=True)
                            print(f"[PROGRESS_PCT] stage=refine pct={pct:.2f} eta={eta}", flush=True)

            for f in as_completed(futures):
                processed, updates = f.result()
                seen += processed
                if updates:
                    _apply_updates(updates)
                    updated += len(updates)
                if seen % 500 == 0 or seen == total:
                    elapsed = max(1e-6, datetime.now().timestamp() - t0)
                    pct = (seen / total) * 100 if total else 100.0
                    eta = int(elapsed * (total - seen) / seen) if seen > 0 else 0
                    print(f"[REFINE] {seen}/{total} updated={updated}", flush=True)
                    print(f"[PROGRESS_PCT] stage=refine pct={pct:.2f} eta={eta}", flush=True)

    conn.commit()
    conn.close()
    print(f"[REFINE] done updated={updated}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--jobs", type=int, default=4, help="Parallel workers for refine")
    args = ap.parse_args()

    jobs = max(1, args.jobs)
    refine_db(args.db, jobs=jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
