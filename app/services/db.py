import sqlite3
from app.constants import CARDNO_RE, TAG_ALIAS

def open_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def _expand_alias(q):
    out = {q}
    for k, vs in TAG_ALIAS.items():
        if q == k or q in vs:
            out.add(k)
            out.update(vs)
    return out

def query_suggest(conn, q, limit=40):
    q = (q or "").strip()
    if not q:
        return []
    like = f"%{q}%"
    aliases = _expand_alias(q)

    sql = '''
    SELECT DISTINCT p.print_id, p.card_number, COALESCE(p.name_ja,'') name_ja
    FROM prints p
    LEFT JOIN print_tags pt ON pt.print_id=p.print_id
    LEFT JOIN tags t ON t.tag=pt.tag
    WHERE p.card_number LIKE ?
       OR p.name_ja LIKE ?
       OR t.tag LIKE ?
       OR t.normalized LIKE ?
    '''
    params = [like, like, like, like]
    for a in aliases:
        sql += " OR t.tag LIKE ? OR t.normalized LIKE ?"
        params += [f"%{a}%", f"%{a}%"]

    sql += " ORDER BY p.card_number LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]

def load_card_detail(conn, pid):
    r = conn.execute(
        '''SELECT raw_text FROM card_texts_ja WHERE print_id=?''', (pid,)
    ).fetchone()
    return dict(r) if r else None
