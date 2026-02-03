#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NamuWiki scraping utilities for Korean text import."""

from __future__ import annotations

from typing import Iterable
from urllib.parse import quote

from bs4 import BeautifulSoup, FeatureNotFound

from tools.namuwiki_ko_common import (
    CARDNO_RE,
    EFFECT_HEADER_KEYWORDS,
    NAME_HEADER_KEYWORDS,
    KoRow,
    cell_has_keyword,
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

    effect = ""
    for cells in rows:
        if len(cells) >= 2 and cell_has_keyword(cells[0], EFFECT_HEADER_KEYWORDS):
            effect = normalize_ws(cells[1])
            break

    if not effect:
        candidates: list[tuple[int, str]] = []
        for cells in rows:
            for cell in cells:
                raw = cell
                text = normalize_ws(cell)
                if not text:
                    continue
                if CARDNO_RE.search(text):
                    continue
                if is_label_cell(text):
                    continue
                if name and normalize_ws(text) == name:
                    continue
                if not is_effect_like(raw, text):
                    continue
                score = len(text)
                if "\n" in raw:
                    score += 20
                candidates.append((score, text))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            effect = candidates[0][1]

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
