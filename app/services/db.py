import sqlite3
from pathlib import Path

from app.constants import TAG_ALIAS

_COL_CACHE: dict[int, dict[str, set[str]]] = {}
_JOIN_CACHE: dict[int, str | None] = {}
_MISSING = object()


def ensure_db(path: str) -> bool:
    if not path or not path.strip():
        return False
    p = Path(path)
    if p.exists():
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        from tools.hocg_tool2 import init_db
        init_db(conn)
    finally:
        conn.close()
    return True


def open_db(path: str) -> sqlite3.Connection:
    if not path or not path.strip():
        raise ValueError("DB path is empty")
    ensure_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _cache_key(conn: sqlite3.Connection) -> int:
    return id(conn)


def clear_conn_cache(conn: sqlite3.Connection) -> None:
    key = _cache_key(conn)
    _COL_CACHE.pop(key, None)
    _JOIN_CACHE.pop(key, None)

def _expand_alias(q: str) -> set[str]:
    out = {q}
    for key, values in TAG_ALIAS.items():
        if q == key:
            out.update(values)
        elif q in values:
            out.add(key)
    return out

def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    key = _cache_key(conn)
    table_cache = _COL_CACHE.get(key)
    if table_cache is not None and table in table_cache:
        return table_cache[table]
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    cols = {r[1] for r in rows}  # r[1] = column name
    if table_cache is None:
        table_cache = {}
        _COL_CACHE[key] = table_cache
    table_cache[table] = cols
    return cols

def _build_tag_joins(conn: sqlite3.Connection) -> str | None:
    """
    DB마다 스키마가 달라서 print_tags/tags 컬럼을 보고 JOIN을 결정.
    지원 케이스:
      1) print_tags(print_id, tag) + tags(tag, normalized)
      2) print_tags(print_id, tag_id) + tags(tag_id, tag, normalized)
    """
    key = _cache_key(conn)
    cached = _JOIN_CACHE.get(key, _MISSING)
    if cached is not _MISSING:
        return cached

    pt_cols = _cols(conn, "print_tags")
    t_cols = _cols(conn, "tags")

    # Case 1
    if "tag" in pt_cols and "tag" in t_cols:
        joins = """
        LEFT JOIN print_tags pt ON pt.print_id = p.print_id
        LEFT JOIN tags t ON t.tag = pt.tag
        """
        _JOIN_CACHE[key] = joins
        return joins

    # Case 2
    if "tag_id" in pt_cols and "tag_id" in t_cols:
        joins = """
        LEFT JOIN print_tags pt ON pt.print_id = p.print_id
        LEFT JOIN tags t ON t.tag_id = pt.tag_id
        """
        _JOIN_CACHE[key] = joins
        return joins

    # Fallback: tags JOIN 불가 → 태그 검색 없이 카드번호/이름만
    _JOIN_CACHE[key] = None
    return None

def query_suggest(conn: sqlite3.Connection, q: str, limit: int = 40) -> list[dict]:
    q = (q or "").strip()
    if not q:
        return []

    like = f"%{q}%"
    aliases = _expand_alias(q)

    joins = _build_tag_joins(conn)
    ko_join = "LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id"

    # 태그 JOIN 가능하면 tag까지 검색
    if joins:
        sql = f"""
        SELECT DISTINCT p.print_id,
               p.card_number,
               COALESCE(p.name_ja,'') AS name_ja,
               COALESCE(ko.name,'') AS name_ko
        FROM prints p
        {ko_join}
        {joins}
        WHERE
            UPPER(p.card_number) LIKE UPPER(?)
            OR COALESCE(p.name_ja,'') LIKE ?
            OR COALESCE(ko.name,'') LIKE ?
            OR (t.tag IS NOT NULL AND (t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?))
        """
        params = [like, like, like, like, like]

        for alias in aliases:
            sql += " OR t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?"
            params += [f"%{alias}%", f"%{alias}%"]

        sql += " ORDER BY p.card_number LIMIT ?"
        params.append(limit)

        return [dict(r) for r in conn.execute(sql, params)]

    # 태그 JOIN 불가하면 카드번호/이름만 검색
    sql = f"""
    SELECT p.print_id,
           p.card_number,
           COALESCE(p.name_ja,'') AS name_ja,
           COALESCE(ko.name,'') AS name_ko
    FROM prints p
    {ko_join}
    WHERE UPPER(p.card_number) LIKE UPPER(?)
       OR COALESCE(p.name_ja,'') LIKE ?
       OR COALESCE(ko.name,'') LIKE ?
    ORDER BY p.card_number
    LIMIT ?
    """
    return [dict(r) for r in conn.execute(sql, (like, like, like, limit))]

def load_card_detail(conn: sqlite3.Connection, pid: int) -> dict | None:
    r = conn.execute(
        """
        SELECT
            ja.raw_text AS raw_text,
            ko.effect_text AS ko_text,
            ko.name AS ko_name
        FROM prints p
        LEFT JOIN card_texts_ja ja ON ja.print_id = p.print_id
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        WHERE p.print_id=?
        """,
        (pid,),
    ).fetchone()
    return dict(r) if r else None

def get_print_brief(conn: sqlite3.Connection, print_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT print_id, card_number, COALESCE(name_ja,'') AS name_ja, COALESCE(image_url,'') AS image_url
        FROM prints
        WHERE print_id=?
        """,
        (print_id,),
    ).fetchone()
    return dict(row) if row else None

def db_exists(path: str) -> bool:
    p = Path(path)
    return p.exists() and p.is_file() and p.stat().st_size > 0
