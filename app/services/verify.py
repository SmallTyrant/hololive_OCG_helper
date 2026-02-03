from __future__ import annotations

from pathlib import Path
import sqlite3


def inspect_db(path: str) -> list[str]:
    issues: list[str] = []
    if not path or not path.strip():
        return ["DB 경로가 비어있습니다."]

    db_path = Path(path)
    if not db_path.exists() or not db_path.is_file() or db_path.stat().st_size == 0:
        return ["DB 파일이 없거나 비어 있습니다."]

    try:
        conn = sqlite3.connect(path)
        try:
            row = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prints'"
            ).fetchone()
            if not row:
                issues.append("prints 테이블이 없습니다.")
            else:
                cols = {
                    r[1]
                    for r in conn.execute("PRAGMA table_info(prints)").fetchall()
                }
                required = {"print_id", "card_number", "name_ja", "image_url"}
                missing = required - cols
                if missing:
                    issues.append(f"prints 컬럼 누락: {', '.join(sorted(missing))}")
        finally:
            conn.close()
    except Exception as ex:
        issues.append(f"DB 점검 실패: {ex}")
    return issues


def inspect_data_root(data_root: Path) -> list[str]:
    issues: list[str] = []
    try:
        data_root.mkdir(parents=True, exist_ok=True)
    except Exception as ex:
        issues.append(f"데이터 폴더 생성 실패: {ex}")
    return issues


def run_startup_checks(db_path: str, data_root: Path) -> list[str]:
    issues: list[str] = []
    issues.extend(inspect_data_root(data_root))
    issues.extend(inspect_db(db_path))
    return issues
