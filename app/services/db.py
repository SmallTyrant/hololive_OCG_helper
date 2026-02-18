import sqlite3
import re
from pathlib import Path

from app.constants import TAG_ALIAS

_COL_CACHE: dict[int, dict[str, set[str]]] = {}
_JOIN_CACHE: dict[int, str | None] = {}
_MISSING = object()
_TOKEN_SPLIT_RE = re.compile(r"[\s,|/]+")


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


def _conn_key(conn: sqlite3.Connection) -> int:
    return id(conn)


def clear_conn_cache(conn: sqlite3.Connection) -> None:
    key = _conn_key(conn)
    _COL_CACHE.pop(key, None)
    _JOIN_CACHE.pop(key, None)

def _normalize_term(text: str) -> str:
    out = (text or "").strip().lower()
    for ch in (" ", "\t", "\n", "\r", "#", "_", "-", "/", "|", ",", "."):
        out = out.replace(ch, "")
    return out


def _unique_terms(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        v = (value or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _is_related_term(a: str, b: str) -> bool:
    na = _normalize_term(a)
    nb = _normalize_term(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) < 2 or len(nb) < 2:
        return False
    return na in nb or nb in na


def _build_search_terms(q: str) -> list[str]:
    split_terms = [
        term
        for term in _TOKEN_SPLIT_RE.split(q)
        if len(_normalize_term(term)) >= 3
    ]
    base_terms = _unique_terms([q, *split_terms])
    expanded = list(base_terms)

    for term in base_terms:
        for key, values in TAG_ALIAS.items():
            alias_terms = [key, *values]
            if any(_is_related_term(term, alias) for alias in alias_terms):
                expanded.extend(alias_terms)

    return _unique_terms(expanded)


def _sql_normalize_expr(column: str) -> str:
    return (
        f"REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(LOWER(COALESCE({column},'')),"
        " ' ', ''), '#', ''), '_', ''), '-', ''), '/', ''), ',', '')"
    )

def _cols(conn: sqlite3.Connection, table: str) -> set[str]:
    key = _conn_key(conn)
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
    key = _conn_key(conn)
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

def query_suggest(conn: sqlite3.Connection, q: str, limit: int | None = None) -> list[dict]:
    q = (q or "").strip()
    if not q:
        return []

    like = f"%{q}%"
    terms = _build_search_terms(q)
    normalized_terms = _unique_terms([_normalize_term(term) for term in terms])

    joins = _build_tag_joins(conn)

    # 태그 JOIN 가능하면 tag까지 검색
    if joins:
        sql = f"""
        SELECT DISTINCT
            p.print_id,
            p.card_number,
            COALESCE(p.name_ja,'') AS name_ja,
            COALESCE(ko.name,'') AS name_ko
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        {joins}
        WHERE
            UPPER(p.card_number) LIKE UPPER(?)
            OR COALESCE(p.name_ja,'') LIKE ?
            OR COALESCE(ko.name,'') LIKE ?
            OR COALESCE(ko.effect_text,'') LIKE ?
            OR (t.tag IS NOT NULL AND (t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?))
        """
        params = [like, like, like, like, like, like]

        for term in terms:
            sql += " OR t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?"
            params += [f"%{term}%", f"%{term}%"]

        if normalized_terms:
            norm_card_number = _sql_normalize_expr("p.card_number")
            norm_tag = _sql_normalize_expr("t.tag")
            norm_normalized = _sql_normalize_expr("t.normalized")
            norm_name_ja = _sql_normalize_expr("p.name_ja")
            norm_name_ko = _sql_normalize_expr("ko.name")
            norm_effect_text = _sql_normalize_expr("ko.effect_text")
            for term in normalized_terms:
                if not term:
                    continue
                sql += (
                    f" OR {norm_card_number} LIKE ? OR {norm_tag} LIKE ? OR {norm_normalized} LIKE ?"
                    f" OR {norm_name_ja} LIKE ? OR {norm_name_ko} LIKE ? OR {norm_effect_text} LIKE ?"
                )
                params += [f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"]

        sql += " ORDER BY p.card_number"
        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params.append(limit)

        return [dict(r) for r in conn.execute(sql, params)]

    # 태그 JOIN 불가하면 카드번호/이름만 검색
    sql = """
    SELECT
        p.print_id,
        p.card_number,
        COALESCE(p.name_ja,'') AS name_ja,
        COALESCE(ko.name,'') AS name_ko
    FROM prints p
    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
    WHERE UPPER(p.card_number) LIKE UPPER(?)
       OR COALESCE(p.name_ja,'') LIKE ?
       OR COALESCE(ko.name,'') LIKE ?
       OR COALESCE(ko.effect_text,'') LIKE ?
    """
    params: list[object] = [like, like, like, like]
    if normalized_terms:
        norm_card_number = _sql_normalize_expr("p.card_number")
        norm_name_ja = _sql_normalize_expr("p.name_ja")
        norm_name_ko = _sql_normalize_expr("ko.name")
        norm_effect_text = _sql_normalize_expr("ko.effect_text")
        for term in normalized_terms:
            if not term:
                continue
            sql += f" OR {norm_card_number} LIKE ? OR {norm_name_ja} LIKE ? OR {norm_name_ko} LIKE ? OR {norm_effect_text} LIKE ?"
            params += [f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"]
    sql += " ORDER BY p.card_number"
    if limit is not None and limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def query_exact(conn: sqlite3.Connection, q: str, limit: int | None = None) -> list[dict]:
    """
    정확 검색 모드:
    - 태그(tag/normalized), 카드번호, 이름(일/한) "정확 일치"만 반환
    - LIKE/부분 일치, 효과문 전문 검색은 수행하지 않음
    """
    q = (q or "").strip()
    if not q:
        return []

    normalized_q = _normalize_term(q)
    joins = _build_tag_joins(conn)
    if joins:
        sql = f"""
        SELECT DISTINCT
            p.print_id,
            p.card_number,
            COALESCE(p.name_ja,'') AS name_ja,
            COALESCE(ko.name,'') AS name_ko
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        {joins}
        WHERE
            UPPER(COALESCE(p.card_number,'')) = UPPER(?)
            OR LOWER(COALESCE(p.name_ja,'')) = LOWER(?)
            OR LOWER(COALESCE(ko.name,'')) = LOWER(?)
            OR (
                t.tag IS NOT NULL
                AND (
                    LOWER(COALESCE(t.tag,'')) = LOWER(?)
                    OR LOWER(COALESCE(t.normalized,'')) = LOWER(?)
        """
        params: list[object] = [q, q, q, q, q]

        if normalized_q:
            norm_tag = _sql_normalize_expr("t.tag")
            norm_normalized = _sql_normalize_expr("t.normalized")
            sql += f" OR {norm_tag} = ? OR {norm_normalized} = ?"
            params += [normalized_q, normalized_q]

        sql += """
                )
            )
        """
        if normalized_q:
            norm_card_number = _sql_normalize_expr("p.card_number")
            norm_name_ja = _sql_normalize_expr("p.name_ja")
            norm_name_ko = _sql_normalize_expr("ko.name")
            sql += f" OR {norm_card_number} = ? OR {norm_name_ja} = ? OR {norm_name_ko} = ?"
            params += [normalized_q, normalized_q, normalized_q]
        sql += " ORDER BY p.card_number"
        if limit is not None and limit > 0:
            sql += " LIMIT ?"
            params.append(limit)

        return [dict(r) for r in conn.execute(sql, params)]

    # 태그 JOIN이 안 되는 스키마에서는 카드번호/이름 정확 검색만 수행
    sql = """
    SELECT
        p.print_id,
        p.card_number,
        COALESCE(p.name_ja,'') AS name_ja,
        COALESCE(ko.name,'') AS name_ko
    FROM prints p
    LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
    WHERE
        UPPER(COALESCE(p.card_number,'')) = UPPER(?)
        OR LOWER(COALESCE(p.name_ja,'')) = LOWER(?)
        OR LOWER(COALESCE(ko.name,'')) = LOWER(?)
    """
    params: list[object] = [q, q, q]
    if normalized_q:
        norm_card_number = _sql_normalize_expr("p.card_number")
        norm_name_ja = _sql_normalize_expr("p.name_ja")
        norm_name_ko = _sql_normalize_expr("ko.name")
        sql += f" OR {norm_card_number} = ? OR {norm_name_ja} = ? OR {norm_name_ko} = ?"
        params += [normalized_q, normalized_q, normalized_q]
    sql += " ORDER BY p.card_number"
    if limit is not None and limit > 0:
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]

def load_card_detail(conn: sqlite3.Connection, pid: int) -> dict | None:
    r = conn.execute(
        """
        SELECT
            ko.effect_text AS ko_text,
            ko.name AS ko_name
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        WHERE p.print_id=?
        """,
        (pid,),
    ).fetchone()
    return dict(r) if r else None

def get_print_brief(conn: sqlite3.Connection, print_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT
            p.print_id,
            p.card_number,
            COALESCE(p.name_ja,'') AS name_ja,
            COALESCE(ko.name,'') AS name_ko,
            COALESCE(p.image_url,'') AS image_url
        FROM prints p
        LEFT JOIN card_texts_ko ko ON ko.print_id = p.print_id
        WHERE p.print_id=?
        """,
        (print_id,),
    ).fetchone()
    return dict(row) if row else None

def db_exists(path: str) -> bool:
    p = Path(path)
    return p.exists() and p.is_file() and p.stat().st_size > 0
