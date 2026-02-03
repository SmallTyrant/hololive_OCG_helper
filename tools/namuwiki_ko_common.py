#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for Korean text import."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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


def is_effect_like(raw: str, normalized: str) -> bool:
    if any(marker in raw for marker in BULLET_MARKERS):
        return True
    if "\n" in raw:
        return True
    if "[" in raw or "]" in raw:
        return True
    if "턴" in normalized or "자신" in normalized or "상대" in normalized:
        return True
    return len(normalized) >= 30


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


def pick_effect(cells: list[str], header_map: dict[str, int], *, allow_simple: bool = True) -> str:
    if "effect" in header_map:
        idx = header_map["effect"]
        if 0 <= idx < len(cells):
            return normalize_ws(cells[idx])
    # fallback: pick the most effect-like cell
    candidates: list[tuple[int, str]] = []
    for cell in cells:
        raw = cell
        normalized = normalize_ws(cell)
        if not normalized:
            continue
        if CARDNO_RE.search(normalized):
            continue
        if is_label_cell(normalized):
            continue
        effect_like = is_effect_like(raw, normalized)
        if not allow_simple and not effect_like:
            continue
        score = len(normalized)
        if effect_like:
            score += 40
        if "\n" in raw:
            score += 20
        if any(marker in raw for marker in BULLET_MARKERS):
            score += 30
        candidates.append((score, normalized))
    if not candidates:
        return ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


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
