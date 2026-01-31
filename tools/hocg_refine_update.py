#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import re
import sqlite3
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

        # merge label + next line value (next가 라벨이면 병합하지 않음)
        if label in MERGE_LABELS and i + 1 < len(cleaned):
            nxt = cleaned[i + 1]
            if _normalize_label(nxt) in ALL_LABELS:
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


def refine_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT print_id, raw_text FROM card_texts_ja"
    ).fetchall()

    updated = 0
    total = len(rows)
    for i, r in enumerate(rows, 1):
        raw = r["raw_text"] or ""
        cleaned = normalize_raw_text(raw)
        if cleaned != raw:
            conn.execute(
                """
                UPDATE card_texts_ja
                SET raw_text=?, effect_text=?, updated_at=?
                WHERE print_id=?
                """,
                (cleaned, cleaned, now_iso(), r["print_id"]),
            )
            updated += 1
        if i % 500 == 0 or i == total:
            print(f"[REFINE] {i}/{total} updated={updated}", flush=True)

    conn.commit()
    conn.close()
    print(f"[REFINE] done updated={updated}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    args = ap.parse_args()

    refine_db(args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
