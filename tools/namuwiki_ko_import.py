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
from urllib.parse import parse_qs, quote, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, FeatureNotFound
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

NAMU_BASE = "https://namu.wiki"
CARDNO_RE = re.compile(r"(?<![A-Za-z0-9_])[hH][A-Za-z]{1,5}\d{2}-\d{3}(?![A-Za-z0-9_])")
HANGUL_RE = re.compile(r"[가-힣]")
JAPANESE_CHAR_RE = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff々〆ヵヶ]")

DEFAULT_SOURCE_PAGES: tuple[str, ...] = (
    "https://namu.wiki/w/%EC%98%A4%EC%8B%9C%20%EB%A6%B0%EB%8F%84%20%EC%B9%98%ED%95%98%EC%95%BC",
    "https://namu.wiki/w/%EC%98%A4%EC%8B%9C%20%EC%BD%94%EA%B0%80%EB%84%A4%EC%9D%B4%20%EB%8B%88%EC%BD%94",
    "https://namu.wiki/w/%EC%98%A4%EC%8B%9C%20Advent",
    "https://namu.wiki/w/%EC%98%A4%EC%8B%9C%20Justice",
    "https://namu.wiki/w/%EC%98%A4%EC%8B%9C%20Justice/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%EC%98%A4%EC%8B%9C%20Advent/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%EC%8A%A4%ED%83%80%ED%8A%B8%20%EB%8D%B1%20FLOW%20GLOW/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%EC%98%A4%EC%98%A4%EC%A1%B0%EB%9D%BC%20%EC%8A%A4%EB%B0%94%EB%A3%A8/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%8B%9C%EB%9D%BC%EC%B9%B4%EB%AF%B8%20%ED%9B%84%EB%B6%80%ED%82%A4/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%98%A4%EC%98%A4%EC%B9%B4%EB%AF%B8%20%EB%AF%B8%EC%98%A4/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EB%84%A4%EC%BD%94%EB%A7%88%ED%83%80%20%EC%98%A4%EC%B9%B4%EC%9C%A0/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%9D%B4%EB%88%84%EA%B0%80%EB%AF%B8%20%EC%BD%94%EB%A1%9C%EB%84%A4/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%9A%B0%EC%82%AC%EB%8B%A4%20%ED%8E%98%EC%BD%94%EB%9D%BC/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%8B%9C%EB%9D%BC%EB%88%84%EC%9D%B4%20%ED%9B%84%EB%A0%88%EC%95%84/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%8B%9C%EB%A1%9C%EA%B0%80%EB%84%A4%20%EB%85%B8%EC%97%98/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%ED%98%B8%EC%87%BC%20%EB%A7%88%EB%A6%B0/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%95%84%EB%A7%88%EB%84%A4%20%EC%B9%B4%EB%82%98%ED%83%80/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%B8%A0%EB%85%B8%EB%A7%88%ED%82%A4%20%EC%99%80%ED%83%80%EB%A9%94/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%ED%86%A0%EC%BD%94%EC%95%BC%EB%AF%B8%20%ED%86%A0%EC%99%80/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%ED%9E%88%EB%A9%94%EB%AA%A8%EB%A6%AC%20%EB%A3%A8%EB%82%98/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%9C%A0%ED%82%A4%ED%95%98%EB%82%98%20%EB%9D%BC%EB%AF%B8/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%EC%BD%94%EC%84%B8%ED%82%A4%20%EB%B9%84%EC%A5%AC/%ED%99%80%EB%A1%9C%EB%9D%BC%EC%9D%B4%EB%B8%8C%20%EC%98%A4%ED%94%BC%EC%85%9C%20%EC%B9%B4%EB%93%9C%20%EA%B2%8C%EC%9E%84",
    "https://namu.wiki/w/%ED%86%A0%ED%82%A4%EB%85%B8%20%EC%86%8C%EB%9D%BC%26AZKi/%EC%B9%B4%EB%93%9C#%EC%84%9C%EB%B8%8C%20%EC%BB%B4%ED%93%A8%ED%84%B0",
    "https://namu.wiki/w/%EB%B8%94%EB%A3%A8%EB%B0%8D%20%EB%A0%88%EB%94%94%EC%96%B8%EC%8A%A4/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%ED%80%B8%ED%85%9F%20%EC%8A%A4%ED%8E%99%ED%8A%B8%EB%9F%BC/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%EC%97%98%EB%A6%AC%ED%8A%B8%20%EC%8A%A4%ED%8C%8C%ED%81%AC/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%ED%81%90%EB%A6%AC%EC%96%B4%EC%8A%A4%20%EC%9C%A0%EB%8B%88%EB%B2%84%EC%8A%A4/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%EC%9D%B8%EC%B1%88%ED%8A%B8%20%EB%A0%88%EA%B0%88%EB%A6%AC%EC%95%84/%EC%B9%B4%EB%93%9C",
    "https://namu.wiki/w/%EC%95%84%EC%95%BC%EC%B9%B4%EC%8B%9C%20%EB%B2%84%EB%B0%80%EB%A6%AC%EC%98%A8/%EC%B9%B4%EB%93%9C",
)

EFFECT_HEADER_KEYWORDS = (
    "효과",
    "텍스트",
    "능력",
    "카드 효과",
    "효과 텍스트",
    "effect",
    "text",
    "ability",
    "card effect",
    "effect text",
)
NAME_HEADER_KEYWORDS = (
    "카드명",
    "카드 이름",
    "이름",
    "카드명(한)",
    "name",
    "card name",
    "card_name",
    "english name",
    "eng name",
    "en name",
    "영문명",
    "영문 이름",
    "영문",
)
CARDNO_HEADER_KEYWORDS = (
    "카드번호",
    "카드 번호",
    "카드 넘버",
    "card number",
    "card no",
    "card_no",
    "card #",
    "print",
    "카드넘버",
)

BULLET_MARKERS = ("■", "●", "◆", "◇", "•", "·")

CARD_ID_ATTR_RE = re.compile(r"id=['\"](?P<id>[hH][A-Za-z]{1,5}\d{2}-\d{3})['\"]")
CARD_ID_EXACT_RE = re.compile(r"^[hH][A-Za-z]{1,5}\d{2}-\d{3}$")
RARITY_LINE_RE = re.compile(r"^(?:OSR|OUR|SEC|UR|SR|RR|R|C|U|P|S|PR|HR|AR|SP|SPR|\-)$", re.IGNORECASE)

BAD_NAME_LABELS = {
    "카드넘버",
    "카드 번호",
    "카드번호",
    "card number",
    "card no",
    "card_no",
    "print",
}

EFFECT_START_PREFIXES = (
    "SP 오시 스킬",
    "오시 스킬",
    "SP推しスキル",
    "推しスキル",
    "아츠",
    "콜라보 이펙트",
    "블룸 이펙트",
    "기프트",
    "엑스트라",
)

SUPPORT_DETAIL_PREFIX_RE = re.compile(
    r"^(?:서포트|サポート)\s*[\/／]\s*(?:아이템|스태프|이벤트|이벤타|툴|마스코트|팬|アイテム|スタッフ|イベント|ツール|マスコット|ファン)(?=$|\s|[\/／:：(\[])"
)

SECTION_END_PREFIXES = (
    "카드 넘버",
    "카드번호",
    "카드 번호",
    "수록 팩 일람",
    "수록 팩",
    "레어도",
    "비고",
)

SECTION_HEADING_LINES = {
    "오시 홀로멤",
    "debut 홀로멤",
    "1st 홀로멤",
    "2nd 홀로멤",
    "spot 홀로멤",
    "서포트 카드",
    "support",
}

NOISE_METADATA_LINES = {
    "[편집]",
    "홀로멤",
    "오시 홀로멤",
    "속성",
    "레벨",
    "hp",
    "life",
    "배턴 터치",
    "debut",
    "1st",
    "2nd",
    "spot",
}

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_card_number(card_no: str) -> str:
    return card_no.strip().upper()


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_header(text: str) -> str:
    return normalize_ws(text).lower()

def normalize_name_key(text: str) -> str:
    normalized = normalize_ws(text).lower()
    return re.sub(r"[\s·・ㆍ:：()\\[\\]\"'`’“”]", "", normalized)


def sanitize_ko_name(text: str) -> str:
    raw = normalize_ws(text)
    if not raw:
        return ""

    cleaned = JAPANESE_CHAR_RE.sub(" ", raw)
    cleaned = re.split(r"\b(?:LIFE|HP)\b", cleaned, maxsplit=1)[0]
    cleaned = re.sub(r"\s*[|/]+\s*", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_.,:;|/\u2013\u2014\u2015\u30fc")

    # Remove exact duplicate: "IRyS IRyS" → "IRyS", "FUWAMOCO FUWAMOCO" → "FUWAMOCO"
    words = cleaned.split()
    if len(words) >= 2 and len(words) % 2 == 0:
        half = len(words) // 2
        if words[:half] == words[half:]:
            cleaned = " ".join(words[:half])

    # Remove trailing name echo: "IRyS Buzz IRyS" → "IRyS Buzz"
    # Pattern: name is repeated after a suffix like "Buzz"
    if len(words) >= 3 and "Buzz" in words:
        buzz_idx = words.index("Buzz")
        prefix = words[:buzz_idx]
        suffix = words[buzz_idx + 1:]
        if prefix and prefix == suffix:
            cleaned = " ".join(words[: buzz_idx + 1])

    return cleaned


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
        candidates.append(normalized)
    if not candidates:
        return ""
    return max(candidates, key=len)


def pick_name(cells: list[str], header_map: dict[str, int]) -> str:
    def _clean_name_line(line: str) -> str:
        cleaned = re.split(r"\b(?:LIFE|HP)\b", line)[0].strip()
        cleaned = re.split(
            r"(레벨|속성|오시 스킬|SP 오시 스킬|SP오시스킬|아츠|배턴 터치|레어도|코스트|에너지|카드 넘버|카드번호|카드 번호|카드넘버)",
            cleaned,
        )[0].strip()
        cleaned = re.sub(r"\s+\d+.*$", "", cleaned).strip()
        if not cleaned:
            cleaned = line.strip()
        if CARDNO_RE.search(cleaned):
            return ""
        return cleaned

    if "name" in header_map:
        idx = header_map["name"]
        if 0 <= idx < len(cells):
            named = normalize_ws(cells[idx])
            if named:
                return named

    lines: list[str] = []
    for cell in cells:
        for line in cell.splitlines():
            normalized = normalize_ws(line)
            if normalized:
                lines.append(normalized)

    for line in lines:
        if line.startswith("#"):
            continue
        if not HANGUL_RE.search(line):
            continue
        cleaned = _clean_name_line(line)
        if cleaned:
            return cleaned

    for line in lines:
        if line.startswith("#"):
            continue
        if HANGUL_RE.search(line):
            continue
        if not re.search(r"[A-Za-z]", line):
            continue
        if any(marker in line for marker in BULLET_MARKERS):
            continue
        if "[" in line or "]" in line:
            continue
        cleaned = _clean_name_line(line)
        if not cleaned:
            continue
        if len(cleaned) > 50:
            continue
        return cleaned

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


def collect_card_numbers_in_table(table_rows: list[list[str]]) -> set[str]:
    numbers: set[str] = set()
    for cells in table_rows:
        for cell in cells:
            for match in CARDNO_RE.finditer(cell):
                numbers.add(normalize_card_number(match.group(0)))
                if len(numbers) >= 8:
                    return numbers
    return numbers


def infer_card_number_from_table_context(table) -> str:
    for node in table.find_all_previous(attrs={"id": True}, limit=128):
        raw_id = normalize_ws(str(node.get("id") or ""))
        if CARD_ID_EXACT_RE.fullmatch(raw_id):
            return normalize_card_number(raw_id)
    return ""


def is_section_heading_line(line: str) -> bool:
    normalized = normalize_ws(line)
    if not normalized:
        return False
    lowered = normalize_header(normalized)
    if lowered in SECTION_HEADING_LINES:
        return True
    if re.fullmatch(r"\d+(?:\.\d+)*\.?", normalized):
        return True
    return False


def is_noise_metadata_line(line: str) -> bool:
    normalized = normalize_ws(line)
    if not normalized:
        return True
    lowered = normalize_header(normalized)
    if lowered in NOISE_METADATA_LINES:
        return True
    if RARITY_LINE_RE.fullmatch(normalized):
        return True
    if re.fullmatch(r"\d+(?:\.\d+)*\.?", normalized):
        return True
    return False


def merge_split_skill_tokens(lines: list[str]) -> list[str]:
    merged: list[str] = []
    idx = 0
    while idx < len(lines):
        cur = lines[idx]
        nxt = lines[idx + 1] if idx + 1 < len(lines) else ""
        nxt2 = lines[idx + 2] if idx + 2 < len(lines) else ""

        if cur.upper() == "SP" and nxt in {"오시", "推し"} and nxt2 in {"스킬", "スキル"}:
            merged.append("SP 오시 스킬" if nxt == "오시" else "SP推しスキル")
            idx += 3
            continue

        if cur in {"오시", "推し"} and nxt in {"스킬", "スキル"}:
            merged.append("오시 스킬" if cur == "오시" else "推しスキル")
            idx += 2
            continue

        merged.append(cur)
        idx += 1
    return merged


def parse_card_sections_from_ids(html: str, source_url: str) -> list[KoRow]:
    matches = list(CARD_ID_ATTR_RE.finditer(html))
    if not matches:
        return []

    rows: list[KoRow] = []
    seen_cards: set[str] = set()
    for idx, match in enumerate(matches):
        card_no = normalize_card_number(match.group("id"))
        if card_no in seen_cards:
            continue
        seen_cards.add(card_no)

        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(html)
        segment_html = html[start:end]
        segment_text = BeautifulSoup(segment_html, "html.parser").get_text("\n", strip=True)
        raw_lines = [normalize_ws(line) for line in segment_text.splitlines()]
        raw_lines = [line for line in raw_lines if line]
        if not raw_lines:
            continue
        raw_lines = merge_split_skill_tokens(raw_lines)

        name = ""
        for line in raw_lines:
            if line.startswith("#"):
                continue
            if CARDNO_RE.search(line):
                continue
            if SUPPORT_DETAIL_PREFIX_RE.match(line):
                continue
            if is_section_heading_line(line):
                continue
            if is_noise_metadata_line(line):
                continue
            candidate_name = pick_name([line], {})
            if not candidate_name:
                continue
            if normalize_header(candidate_name) in BAD_NAME_LABELS:
                continue
            name = candidate_name
            break

        effect_lines: list[str] = []
        started = False
        for line in raw_lines:
            if CARDNO_RE.search(line):
                continue
            numeric_outline = bool(re.fullmatch(r"\d+(?:\.\d+)*\.?", line))
            if any(line.startswith(prefix) for prefix in SECTION_END_PREFIXES) or (
                is_section_heading_line(line) and not numeric_outline
            ):
                if started:
                    break
                continue

            if not started:
                if (
                    line.startswith("#")
                    or line.startswith("[홀로 파워")
                    or line.startswith(EFFECT_START_PREFIXES)
                    or SUPPORT_DETAIL_PREFIX_RE.match(line)
                ):
                    started = True
                    effect_lines.append(line)
                continue

            if is_noise_metadata_line(line) and not line.startswith("#"):
                continue
            effect_lines.append(line)

        if not effect_lines:
            continue

        effect = normalize_ws(" ".join(effect_lines))
        if not effect:
            continue
        rows.append(KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url))

    return rows


def row_quality_score(row: KoRow) -> float:
    score = 0.0
    normalized_name = normalize_header(row.name)
    if row.name and normalized_name not in BAD_NAME_LABELS:
        score += 8.0
    else:
        score -= 20.0

    effect = row.effect or ""
    if any(marker in effect for marker in EFFECT_START_PREFIXES) or "#" in effect or SUPPORT_DETAIL_PREFIX_RE.match(effect):
        score += 8.0

    refs = {normalize_card_number(m.group(0)) for m in CARDNO_RE.finditer(effect)}
    if len(refs) > 1:
        score -= len(refs) * 6.0

    lowered_effect = normalize_header(effect)
    if "카드넘버 카드명 종류" in lowered_effect or "카드 넘버 카드명 종류" in lowered_effect:
        score -= 60.0

    score += min(len(effect), 1200) / 120.0
    return score


def is_better_candidate(candidate: KoRow, previous: KoRow | None) -> bool:
    if previous is None:
        return True
    candidate_score = row_quality_score(candidate)
    previous_score = row_quality_score(previous)
    if candidate_score != previous_score:
        return candidate_score > previous_score
    return len(candidate.effect) > len(previous.effect)


def parse_tables(
    html: str,
    source_url: str,
    *,
    fallback_card_numbers: list[str] | None = None,
) -> list[KoRow]:
    _ = fallback_card_numbers
    try:
        soup = BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(html, "html.parser")

    rows: list[KoRow] = []
    best_by_card: dict[str, KoRow] = {}

    for table in soup.select("table"):
        context_card_no = infer_card_number_from_table_context(table)
        table_rows: list[list[str]] = []
        for tr in table.select("tr"):
            cells = [normalize_ws(c.get_text(" ", strip=True)) for c in tr.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if cells:
                table_rows.append(cells)

        if not table_rows:
            continue

        table_card_numbers = collect_card_numbers_in_table(table_rows)

        card_no = ""
        card_row_idx = -1
        for idx, cells in enumerate(table_rows):
            for cell in cells:
                match = CARDNO_RE.search(cell)
                if match:
                    card_no = normalize_card_number(match.group(0))
                    card_row_idx = idx
                    break
            if card_no:
                break

        if len(table_card_numbers) == 1 and context_card_no and context_card_no != card_no:
            card_no = context_card_no

        if card_no and len(table_card_numbers) == 1:
            first_row = table_rows[0]
            name = pick_name([first_row[0]] if first_row else [], {})
            if not name and first_row:
                name = normalize_ws(first_row[0].split("/", 1)[0])

            effect_parts: list[str] = []
            for idx, cells in enumerate(table_rows):
                if idx == card_row_idx or idx == 0:
                    continue
                line = normalize_ws(" ".join(cells))
                if not line:
                    continue
                normalized_line = normalize_header(line)
                if normalized_line in {
                    "홀로멤",
                    "오시 홀로멤",
                    "레벨 속성",
                    "레벨",
                    "속성",
                    "debut",
                    "1st",
                    "2nd",
                    "spot",
                }:
                    continue
                effect_parts.append(line)

            effect = normalize_ws(" ".join(effect_parts))
            if not effect:
                continue

            candidate = KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url)
            previous = best_by_card.get(card_no)
            if is_better_candidate(candidate, previous):
                best_by_card[card_no] = candidate
            continue

        header_map: dict[str, int] = {}
        header_cells: list[str] = []
        body_rows: list[list[str]] = []
        for cells in table_rows:
            if not header_cells:
                candidate = find_header_map(cells)
                if candidate:
                    header_cells = cells
                    header_map = candidate
                    continue
            body_rows.append(cells)

        if not header_cells and body_rows:
            candidate = find_header_map(body_rows[0])
            if candidate:
                header_cells = body_rows[0]
                header_map = candidate
                body_rows = body_rows[1:]

        if not header_map:
            continue

        if "effect" not in header_map:
            continue

        for cells in body_rows:
            card_no = pick_card_number(cells, header_map)
            if not card_no:
                continue
            effect = pick_effect(cells, header_map)
            normalized_effect = normalize_header(effect)
            if normalized_effect in {"카드 넘버", "카드 번호", "카드번호", "card number", "card no", "card_no", "print"}:
                continue
            name = pick_name(cells, header_map)
            if not effect:
                continue

            candidate = KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url)
            previous = best_by_card.get(card_no)
            if is_better_candidate(candidate, previous):
                best_by_card[card_no] = candidate

    for candidate in parse_card_sections_from_ids(html, source_url):
        previous = best_by_card.get(candidate.card_number)
        if is_better_candidate(candidate, previous):
            best_by_card[candidate.card_number] = candidate

    rows.extend(best_by_card.values())
    return rows


def parse_search_results(html: str, query: str) -> list[str]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(html, "html.parser")
    normalized_query = normalize_ws(query).lower()
    urls: list[str] = []
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if not href.startswith("/w/"):
            continue
        if href.startswith("/w/검색"):
            continue
        text = normalize_ws(link.get_text(" ", strip=True)).lower()
        if normalized_query and normalized_query not in text and normalized_query not in href.lower():
            continue
        urls.append(f"{NAMU_BASE}{href}")
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def extract_card_numbers(html: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for match in CARDNO_RE.finditer(html):
        normalized = normalize_card_number(match.group(0))
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def collect_linked_pages(
    html: str,
    *,
    include_re: re.Pattern[str] | None,
    exclude_re: re.Pattern[str] | None,
) -> list[str]:
    try:
        soup = BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for link in soup.select("a[href]"):
        href = link.get("href", "")
        if not href:
            continue
        if href.startswith("/w/검색") or href.startswith("/w/파일"):
            continue
        if href.startswith("/w/"):
            url = f"{NAMU_BASE}{href}"
        elif href.startswith(f"{NAMU_BASE}/w/"):
            url = href
        else:
            continue
        if include_re and not include_re.search(url):
            continue
        if exclude_re and exclude_re.search(url):
            continue
        urls.append(url)
    seen: set[str] = set()
    deduped: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


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


def dedupe_pages(pages: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for page in pages:
        normalized = (page or "").strip()
        if normalized.startswith("http://") or normalized.startswith("https://"):
            parsed = urlparse(normalized)
            normalized = urlunparse(parsed._replace(fragment=""))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def iter_card_numbers_for_search(
    print_map: dict[str, int],
    existing_ko: dict[int, tuple[str, str, int]],
    *,
    overwrite: bool,
) -> Iterable[str]:
    if overwrite:
        yield from sorted(print_map)
        return
    for card_no, print_id in sorted(print_map.items()):
        cached = existing_ko.get(print_id)
        if cached and cached[1].strip():
            continue
        yield card_no


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


def has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
        if row[1] == column:
            return True
    return False


def upsert_ko_text(
    conn: sqlite3.Connection,
    print_id: int,
    name: str,
    effect: str,
    source_url: str,
    *,
    include_source: bool,
    overwrite: bool,
    existing: dict[int, tuple[str, str, int]] | None = None,
) -> bool:
    name = sanitize_ko_name(name)
    cached = existing.get(print_id) if existing is not None else None
    if not name and cached:
        name = sanitize_ko_name(cached[0])

    # Strip duplicate card name from the beginning of effect_text (may repeat)
    if name and effect:
        stripped = effect.lstrip()
        while stripped.startswith(name):
            stripped = stripped[len(name):].lstrip()
        effect = stripped

    if cached and not overwrite:
        if cached[1].strip():
            return False
    version = 1
    if cached:
        version = int(cached[2] or 1)
        if cached[1] != effect or cached[0] != name:
            version += 1
    if include_source:
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
    else:
        conn.execute(
            """
            INSERT INTO card_texts_ko(print_id,name,effect_text,memo,version,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(print_id) DO UPDATE SET
              name=excluded.name,
              effect_text=excluded.effect_text,
              memo=excluded.memo,
              version=excluded.version,
              updated_at=excluded.updated_at
            """,
            (print_id, name, effect, source_url, version, now_iso()),
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


def load_print_name_map(conn: sqlite3.Connection) -> dict[str, int]:
    mapping: dict[str, int] = {}
    duplicates: set[str] = set()
    for row in conn.execute("SELECT print_id, name_ja FROM prints"):
        name = normalize_name_key(row["name_ja"] or "")
        if not name:
            continue
        if name in mapping:
            duplicates.add(name)
            continue
        mapping[name] = int(row["print_id"])
    for row in conn.execute("SELECT print_id, name FROM card_texts_ja WHERE name IS NOT NULL"):
        name = normalize_name_key(row["name"] or "")
        if not name:
            continue
        if name in mapping and mapping[name] != int(row["print_id"]):
            duplicates.add(name)
            continue
        mapping[name] = int(row["print_id"])
    for name in duplicates:
        mapping.pop(name, None)
    return mapping


def import_rows(
    conn: sqlite3.Connection,
    rows: Iterable[KoRow],
    *,
    include_source: bool,
    overwrite: bool,
    print_map: dict[str, int],
    existing_ko: dict[int, tuple[str, str, int]],
    name_map: dict[str, int],
) -> int:
    updated = 0
    for row in rows:
        print_id = None
        if row.card_number:
            print_id = print_map.get(normalize_card_number(row.card_number))
        if not print_id and row.name:
            print_id = name_map.get(normalize_name_key(row.name))
        if not print_id:
            missing = row.card_number or row.name or "unknown"
            print(f"[SKIP] missing print for {missing}")
            continue
        if upsert_ko_text(
            conn,
            print_id,
            row.name,
            row.effect,
            row.source_url,
            include_source=include_source,
            overwrite=overwrite,
            existing=existing_ko,
        ):
            updated += 1
    return updated


def _apply_db_pragmas(conn: sqlite3.Connection) -> None:
    """DB 쓰기 성능 향상을 위한 PRAGMA 설정."""
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-32768;")  # 32 MiB page cache
    conn.execute("PRAGMA temp_store=MEMORY;")


def import_from_pages(
    db_path: str,
    pages: list[str],
    page_file: str | None,
    *,
    timeout: float,
    overwrite: bool,
    search_card_numbers: bool,
    crawl_linked: bool,
    link_include: re.Pattern[str] | None,
    link_exclude: re.Pattern[str] | None,
    delay: float = 0.5,
) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _apply_db_pragmas(conn)
    session = build_session()
    print_map = load_print_map(conn)
    existing_ko = load_existing_ko(conn)
    name_map = load_print_name_map(conn)
    include_source = has_column(conn, "card_texts_ko", "source")

    updated = 0
    seen_pages: set[str] = set()
    for page in iter_pages(pages, page_file):
        source_url = page if page.startswith("http") else f"{NAMU_BASE}/w/{quote(page)}"
        if source_url in seen_pages:
            continue
        seen_pages.add(source_url)
        try:
            html = fetch_html(session, page, timeout=timeout)
        except requests.RequestException as exc:
            print(f"[WARN] fetch failed for {source_url}: {exc}")
            continue
        fallback_card_numbers = extract_card_numbers(html)
        updated += import_rows(
            conn,
            parse_tables(html, source_url, fallback_card_numbers=fallback_card_numbers),
            include_source=include_source,
            overwrite=overwrite,
            print_map=print_map,
            existing_ko=existing_ko,
            name_map=name_map,
        )
        if crawl_linked:
            linked_urls = collect_linked_pages(html, include_re=link_include, exclude_re=link_exclude)
            for url in linked_urls:
                if url in seen_pages:
                    continue
                seen_pages.add(url)
                if delay > 0:
                    import time as _time
                    _time.sleep(delay)
                try:
                    page_html = fetch_html(session, url, timeout=timeout)
                except requests.RequestException as exc:
                    print(f"[WARN] fetch failed for {url}: {exc}")
                    continue
                fallback_card_numbers = extract_card_numbers(page_html)
                updated += import_rows(
                    conn,
                    parse_tables(page_html, url, fallback_card_numbers=fallback_card_numbers),
                    include_source=include_source,
                    overwrite=overwrite,
                    print_map=print_map,
                    existing_ko=existing_ko,
                    name_map=name_map,
                )

    if search_card_numbers:
        import time as _time
        for card_no in iter_card_numbers_for_search(print_map, existing_ko, overwrite=overwrite):
            query = normalize_card_number(card_no)
            search_url = f"{NAMU_BASE}/Search?q={quote(query)}"
            if delay > 0:
                _time.sleep(delay)
            try:
                html = fetch_html(session, search_url, timeout=timeout)
            except requests.RequestException as exc:
                print(f"[WARN] search failed for {query}: {exc}")
                continue
            result_urls = parse_search_results(html, query)
            if not result_urls:
                if search_url not in seen_pages:
                    seen_pages.add(search_url)
                continue
            for url in result_urls:
                if url in seen_pages:
                    continue
                seen_pages.add(url)
                if delay > 0:
                    _time.sleep(delay)
                try:
                    page_html = fetch_html(session, url, timeout=timeout)
                except requests.RequestException as exc:
                    print(f"[WARN] fetch failed for {url}: {exc}")
                    continue
                fallback_card_numbers = extract_card_numbers(page_html)
                updated += import_rows(
                    conn,
                    parse_tables(page_html, url, fallback_card_numbers=fallback_card_numbers),
                    include_source=include_source,
                    overwrite=overwrite,
                    print_map=print_map,
                    existing_ko=existing_ko,
                    name_map=name_map,
                )
    conn.commit()
    conn.close()
    return updated


def import_from_sheet(db_path: str, sheet_url: str, *, timeout: float, overwrite: bool, gid: str | None) -> int:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _apply_db_pragmas(conn)
    session = build_session()
    csv_url = build_sheet_csv_url(sheet_url, gid)
    print_map = load_print_map(conn)
    existing_ko = load_existing_ko(conn)
    name_map = load_print_name_map(conn)
    include_source = has_column(conn, "card_texts_ko", "source")
    resp = session.get(csv_url, timeout=timeout)
    resp.raise_for_status()
    updated = import_rows(
        conn,
        parse_sheet_csv(resp.text, csv_url),
        include_source=include_source,
        overwrite=overwrite,
        print_map=print_map,
        existing_ko=existing_ko,
        name_map=name_map,
    )
    conn.commit()
    conn.close()
    return updated


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="SQLite DB path")
    ap.add_argument("--page", action="append", default=[], help="NamuWiki page title or full URL")
    ap.add_argument("--page-file", help="Text file containing page titles/URLs")
    ap.add_argument(
        "--skip-default-pages",
        action="store_true",
        help="Do not include built-in NamuWiki source pages",
    )
    ap.add_argument("--sheet-url", help="Google Sheets URL (share or export CSV)")
    ap.add_argument("--sheet-gid", help="Google Sheets gid (optional)")
    ap.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout seconds")
    ap.add_argument("--delay", type=float, default=0.5, help="Delay seconds between linked/search page requests")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing Korean texts")
    ap.add_argument("--crawl-linked", action="store_true", help="Crawl linked NamuWiki pages from sources")
    ap.add_argument("--link-include", help="Regex for linked URLs to include")
    ap.add_argument("--link-exclude", help="Regex for linked URLs to exclude")
    ap.add_argument(
        "--search-card-numbers",
        action="store_true",
        help="Search NamuWiki by card number and crawl matching pages",
    )
    args = ap.parse_args()

    default_pages = [] if args.skip_default_pages else list(DEFAULT_SOURCE_PAGES)
    page_sources = dedupe_pages([*args.page, *default_pages])

    if not page_sources and not args.page_file and not args.sheet_url and not args.search_card_numbers:
        print("No sources provided. Use --page/--page-file or --sheet-url.")
        return 1

    updated = 0
    if page_sources or args.page_file or args.search_card_numbers:
        link_include = re.compile(args.link_include) if args.link_include else None
        link_exclude = re.compile(args.link_exclude) if args.link_exclude else None
        updated += import_from_pages(
            args.db,
            page_sources,
            args.page_file,
            timeout=args.timeout,
            overwrite=args.overwrite,
            search_card_numbers=args.search_card_numbers,
            crawl_linked=args.crawl_linked,
            link_include=link_include,
            link_exclude=link_exclude,
            delay=args.delay,
        )
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
