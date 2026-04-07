#!/usr/bin/env python3
"""
import_illustrations.py
hocg-fan-sim-assets 의 hocg_cards.json 에서 레어리티별 일러스트 정보를
app/assets/hololive_ocg.sqlite 의 card_illustrations 테이블에 upsert합니다.

Usage:
    .venv/bin/python3 tools/import_illustrations.py
"""
from __future__ import annotations
import json, re, sqlite3, sys
from pathlib import Path

import requests

DB_PATH  = Path(__file__).parent.parent / "app" / "assets" / "hololive_ocg.sqlite"
CARDS_URL = "https://qrimpuff.github.io/hocg-fan-sim-assets/hocg_cards.json"
OFFICIAL_BASE = "https://hololive-official-cardgame.com"
CARDLIST_BASE  = f"{OFFICIAL_BASE}/wp-content/images/cardlist"

# image_url 필드가 null 인 경우 카드번호+레어리티로 추정 URL 생성
# 패턴: /wp-content/images/cardlist/<SET>/<CARD>_<RARITY>.png
# 단, hPR 세트는 예외(프로모)라 추정 불가 → None 반환
_SET_RE = re.compile(r'^([hH][A-Za-z]+\d+)-\d+$')
HY_COMMON_FALLBACK = {
    "HY01": f"{CARDLIST_BASE}/COMMON/hY01-001_C.png",
    "HY02": f"{CARDLIST_BASE}/COMMON/hY02-001_C.png",
    "HY03": f"{CARDLIST_BASE}/COMMON/hY03-001_C.png",
    "HY04": f"{CARDLIST_BASE}/COMMON/hY04-001_C.png",
    "HY05": f"{CARDLIST_BASE}/COMMON/hY05-001_C.png",
    "HY06": f"{CARDLIST_BASE}/hSD07/hY06-001_C.png",
}

def infer_image_url(card_number: str, rarity: str) -> str | None:
    m = _SET_RE.match(card_number)
    if not m:
        return None
    set_code = m.group(1)
    if rarity == "P":
        hy_fallback = HY_COMMON_FALLBACK.get(set_code.upper())
        if hy_fallback:
            return hy_fallback
        return None
    return f"{CARDLIST_BASE}/{set_code}/{card_number}_{rarity}.png"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS card_illustrations(
          illustration_id INTEGER PRIMARY KEY AUTOINCREMENT,
          card_number     TEXT NOT NULL,
          rarity          TEXT NOT NULL,
          manage_id_jp    INTEGER,
          manage_id_en    INTEGER,
          image_url       TEXT,
          is_default      INTEGER NOT NULL DEFAULT 0,
          UNIQUE(card_number, rarity)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_card_illustrations_cn
        ON card_illustrations(card_number)
    """)
    conn.commit()


def upsert_illustration(
    conn: sqlite3.Connection,
    card_number: str,
    rarity: str,
    manage_id_jp: int | None,
    manage_id_en: int | None,
    image_url: str | None,
    is_default: int,
) -> None:
    conn.execute("""
        INSERT INTO card_illustrations(card_number, rarity, manage_id_jp, manage_id_en, image_url, is_default)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(card_number, rarity) DO UPDATE SET
          manage_id_jp = excluded.manage_id_jp,
          manage_id_en = excluded.manage_id_en,
          image_url    = COALESCE(excluded.image_url, card_illustrations.image_url),
          is_default   = excluded.is_default
    """, (card_number, rarity, manage_id_jp, manage_id_en, image_url, is_default))


def backfill_hy_common_fallbacks(conn: sqlite3.Connection) -> int:
    updated = 0
    rows = conn.execute(
        """
        SELECT illustration_id, card_number
        FROM card_illustrations
        WHERE UPPER(card_number) LIKE 'HY%'
          AND UPPER(rarity) = 'P'
          AND (image_url IS NULL OR TRIM(image_url) = '')
        """
    ).fetchall()
    for illustration_id, card_number in rows:
        fallback = infer_image_url(card_number, "P")
        if not fallback:
            continue
        existing_c = conn.execute(
            "SELECT illustration_id FROM card_illustrations WHERE card_number=? AND UPPER(rarity)='C' LIMIT 1",
            (card_number,),
        ).fetchone()
        if existing_c:
            conn.execute(
                "UPDATE card_illustrations SET image_url=COALESCE(NULLIF(image_url,''), ?) WHERE illustration_id=?",
                (fallback, existing_c[0]),
            )
            conn.execute(
                "DELETE FROM card_illustrations WHERE illustration_id=?",
                (illustration_id,),
            )
        else:
            conn.execute(
                "UPDATE card_illustrations SET rarity='C', image_url=? WHERE illustration_id=?",
                (fallback, illustration_id),
            )
        updated += 1
    return updated


def normalize_hy_common_fallback_rarity(conn: sqlite3.Connection) -> int:
    updated = 0
    rows = conn.execute(
        """
        SELECT illustration_id, card_number, COALESCE(image_url, '') AS image_url
        FROM card_illustrations
        WHERE UPPER(card_number) LIKE 'HY%'
          AND UPPER(rarity) = 'P'
        """
    ).fetchall()
    for illustration_id, card_number, image_url in rows:
        fallback = infer_image_url(card_number, "P")
        if not fallback or (image_url or '').strip() != fallback:
            continue
        existing_c = conn.execute(
            "SELECT illustration_id FROM card_illustrations WHERE card_number=? AND UPPER(rarity)='C' LIMIT 1",
            (card_number,),
        ).fetchone()
        if existing_c:
            conn.execute(
                "UPDATE card_illustrations SET image_url=COALESCE(NULLIF(image_url,''), ?) WHERE illustration_id=?",
                (fallback, existing_c[0]),
            )
            conn.execute("DELETE FROM card_illustrations WHERE illustration_id=?", (illustration_id,))
        else:
            conn.execute(
                "UPDATE card_illustrations SET rarity='C' WHERE illustration_id=?",
                (illustration_id,),
            )
        updated += 1
    return updated


def derive_default_rarity(image_url: str | None) -> str | None:
    """prints.image_url 에서 레어리티 suffix 추출"""
    if not image_url:
        return None
    stem = image_url.rsplit('/', 1)[-1]  # e.g. hBP01-001_OUR.png
    stem = stem.rsplit('.', 1)[0]         # hBP01-001_OUR
    parts = stem.split('_')
    if len(parts) >= 2:
        return parts[-1]                  # OUR
    return None


def main() -> None:
    print(f"[INFO] fetching {CARDS_URL} ...", flush=True)
    resp = requests.get(CARDS_URL, timeout=60)
    resp.raise_for_status()
    cards: dict = resp.json()
    print(f"[INFO] fetched {len(cards)} cards", flush=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=OFF")  # 크로스 참조 없으므로 OFF

    # 기존 prints 테이블에서 card_number → image_url 매핑 (is_default 결정용)
    default_rarity_map: dict[str, str] = {}
    for row in conn.execute("SELECT card_number, image_url FROM prints"):
        cn, img = row
        r = derive_default_rarity(img)
        if cn and r:
            default_rarity_map[cn] = r

    try:
        ensure_schema(conn)

        upserted = 0
        skipped  = 0

        for card_number, card in cards.items():
            illustrations = card.get("illustrations") or []
            if not illustrations:
                skipped += 1
                continue

            default_rarity = default_rarity_map.get(card_number)

            for ill in illustrations:
                rarity = ill.get("rarity") or ""
                if not rarity:
                    continue

                manage_ids = ill.get("manage_id") or {}
                jp_ids = manage_ids.get("jp") or []
                en_ids = manage_ids.get("en") or []
                manage_id_jp = int(jp_ids[0]) if jp_ids else None
                manage_id_en = int(en_ids[0]) if en_ids else None

                # image_url: hocg_cards.json 의 image 필드가 보통 null
                raw_img = ill.get("image") or None
                if not raw_img:
                    raw_img = infer_image_url(card_number, rarity)

                is_default = 1 if (default_rarity and rarity == default_rarity) else 0

                upsert_illustration(
                    conn, card_number, rarity,
                    manage_id_jp, manage_id_en,
                    raw_img, is_default,
                )
                upserted += 1

        # is_default 가 하나도 없는 카드는 첫 번째 레어리티를 default로 설정
        no_default = conn.execute("""
            SELECT DISTINCT card_number FROM card_illustrations
            WHERE card_number NOT IN (
                SELECT DISTINCT card_number FROM card_illustrations WHERE is_default=1
            )
        """).fetchall()
        for (cn,) in no_default:
            first = conn.execute(
                "SELECT illustration_id FROM card_illustrations WHERE card_number=? ORDER BY illustration_id LIMIT 1",
                (cn,),
            ).fetchone()
            if first:
                conn.execute(
                    "UPDATE card_illustrations SET is_default=1 WHERE illustration_id=?",
                    (first[0],),
                )

        hy_backfilled = backfill_hy_common_fallbacks(conn)
        hy_normalized = normalize_hy_common_fallback_rarity(conn)

        conn.commit()
        print(f"[INFO] upserted {upserted} illustrations, skipped {skipped} cards without data", flush=True)
        print(f"[INFO] HY common fallback backfilled: {hy_backfilled}", flush=True)
        print(f"[INFO] HY fallback rarity normalized to C: {hy_normalized}", flush=True)

        # 통계
        total    = conn.execute("SELECT COUNT(*) FROM card_illustrations").fetchone()[0]
        defaults = conn.execute("SELECT COUNT(*) FROM card_illustrations WHERE is_default=1").fetchone()[0]
        multi    = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT card_number FROM card_illustrations GROUP BY card_number HAVING COUNT(*)>1
            )
        """).fetchone()[0]
        print(f"[INFO] total illustrations: {total}", flush=True)
        print(f"[INFO] cards with default rarity: {defaults}", flush=True)
        print(f"[INFO] cards with multiple rarities: {multi}", flush=True)

        # 샘플 출력
        print("\n[SAMPLE] 복수 레어리티 카드:", flush=True)
        rows = conn.execute("""
            SELECT ci.card_number, ci.rarity, ci.manage_id_jp, ci.is_default, ci.image_url
            FROM card_illustrations ci
            WHERE ci.card_number IN (
                SELECT card_number FROM card_illustrations
                GROUP BY card_number HAVING COUNT(*) > 2
                LIMIT 3
            )
            ORDER BY ci.card_number, ci.illustration_id
        """).fetchall()
        for row in rows:
            cn, r, mid, isdef, img = row
            print(f"  {cn} | {r} | manage_id_jp={mid} | default={isdef} | img={img or '(none)'}", flush=True)

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main() or 0)
