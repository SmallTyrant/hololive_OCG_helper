import sqlite3
from app.constants import TAG_ALIAS
from pathlib import Path

def open_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def _expand_alias(q):
    out = {q}
    for k, vs in TAG_ALIAS.items():
        if q == k:
            out.update(vs)
        elif q in vs:
            out.add(k)
    return out

def _cols(conn, table: str):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}  # r[1] = column name

def _build_tag_joins(conn):
    """
    DB마다 스키마가 달라서 print_tags/tags 컬럼을 보고 JOIN을 결정.
    지원 케이스:
      1) print_tags(print_id, tag) + tags(tag, normalized)
      2) print_tags(print_id, tag_id) + tags(tag_id, tag, normalized)
    """
    pt_cols = _cols(conn, "print_tags")
    t_cols  = _cols(conn, "tags")

    # Case 1
    if "tag" in pt_cols and "tag" in t_cols:
        joins = """
        LEFT JOIN print_tags pt ON pt.print_id = p.print_id
        LEFT JOIN tags t ON t.tag = pt.tag
        """
        return joins

    # Case 2
    if "tag_id" in pt_cols and "tag_id" in t_cols:
        joins = """
        LEFT JOIN print_tags pt ON pt.print_id = p.print_id
        LEFT JOIN tags t ON t.tag_id = pt.tag_id
        """
        return joins

    # Fallback: tags JOIN 불가 → 태그 검색 없이 카드번호/이름만
    return None

def query_suggest(conn, q, limit=40):
    q = (q or "").strip()
    if not q:
        return []

    like = f"%{q}%"
    aliases = _expand_alias(q)

    joins = _build_tag_joins(conn)

    # 태그 JOIN 가능하면 tag까지 검색
    if joins:
        sql = f"""
        SELECT DISTINCT p.print_id, p.card_number, COALESCE(p.name_ja,'') AS name_ja
        FROM prints p
        {joins}
        WHERE
            UPPER(p.card_number) LIKE UPPER(?)
            OR COALESCE(p.name_ja,'') LIKE ?
            OR (t.tag IS NOT NULL AND (t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?))
        """
        params = [like, like, like, like]

        for a in aliases:
            sql += " OR t.tag LIKE ? OR COALESCE(t.normalized,'') LIKE ?"
            params += [f"%{a}%", f"%{a}%"]

        sql += " ORDER BY p.card_number LIMIT ?"
        params.append(limit)

        return [dict(r) for r in conn.execute(sql, params)]

    # 태그 JOIN 불가하면 카드번호/이름만 검색
    sql = """
    SELECT p.print_id, p.card_number, COALESCE(p.name_ja,'') AS name_ja
    FROM prints p
    WHERE UPPER(p.card_number) LIKE UPPER(?)
       OR COALESCE(p.name_ja,'') LIKE ?
    ORDER BY p.card_number
    LIMIT ?
    """
    return [dict(r) for r in conn.execute(sql, (like, like, limit))]

def load_card_detail(conn, pid):
    r = conn.execute(
        "SELECT raw_text FROM card_texts_ja WHERE print_id=?",
        (pid,),
    ).fetchone()
    return dict(r) if r else None

def get_print_brief(conn, print_id: int) -> dict | None:
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