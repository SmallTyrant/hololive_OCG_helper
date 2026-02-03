#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NamuWiki scraping utilities for Korean text import."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from typing import Iterable
from urllib.parse import quote

from bs4 import BeautifulSoup, FeatureNotFound

from tools.namuwiki_ko_common import (
    CARDNO_RE,
    EFFECT_HEADER_KEYWORDS,
    NAME_HEADER_KEYWORDS,
    KoRow,
    cell_has_keyword,
    extract_korean_name,
    find_header_map,
    is_effect_like,
    is_label_cell,
    normalize_card_number,
    normalize_ws,
    pick_card_number,
    pick_effect,
    pick_name,
)

NAMU_BASE = "https://namu.wiki"


def fetch_html(session, page: str, *, timeout: float) -> str:
    if page.startswith("http://") or page.startswith("https://"):
        url = page
    else:
        url = f"{NAMU_BASE}/w/{quote(page)}"
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


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
    if not name:
        for cells in rows:
            for cell in cells:
                name = extract_korean_name(cell)
                if name:
                    break
            if name:
                break

    def _build_effect_lines(rows: list[list[str]]) -> list[str]:
        lines: list[str] = []
        i = 0
        while i < len(rows):
            cells = rows[i]
            if not cells:
                i += 1
                continue
            if any(cell_has_keyword(c, ("카드 넘버", "카드번호", "카드 번호", "카드넘버")) for c in cells):
                i += 1
                continue
            # header/value row pairing
            if len(cells) >= 2 and all(is_label_cell(c) for c in cells):
                if i + 1 < len(rows) and len(rows[i + 1]) == len(cells):
                    values = rows[i + 1]
                    for label, value in zip(cells, values):
                        label_norm = normalize_ws(label)
                        value_norm = normalize_ws(value)
                        if not value_norm:
                            continue
                        if cell_has_keyword(label_norm, ("카드 넘버", "카드번호", "카드 번호", "카드넘버")):
                            continue
                        lines.append(f"{label_norm} {value_norm}")
                    i += 2
                    continue
            # label + value row
            if len(cells) >= 2 and is_label_cell(cells[0]):
                label_norm = normalize_ws(cells[0])
                if cell_has_keyword(label_norm, ("카드 넘버", "카드번호", "카드 번호", "카드넘버")):
                    i += 1
                    continue
                value_norm = " ".join(
                    normalize_ws(c) for c in cells[1:] if normalize_ws(c)
                )
                if value_norm:
                    lines.append(f"{label_norm} {value_norm}")
                i += 1
                continue
            # single-cell effect row
            if len(cells) == 1:
                raw = cells[0]
                text = normalize_ws(raw)
                if not text:
                    i += 1
                    continue
                if name and text == name:
                    i += 1
                    continue
                if is_effect_like(raw, text):
                    lines.append(text)
            i += 1
        return lines

    effect_lines = _build_effect_lines(rows)
    effect = "\n".join(effect_lines).strip()

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
            allow_simple = "effect" in header_map
            effect = pick_effect(cells, header_map, allow_simple=allow_simple)
            name = pick_name(cells, header_map)
            if not effect:
                continue
            rows.append(KoRow(card_number=card_no, name=name, effect=effect, source_url=source_url))
    return rows


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
