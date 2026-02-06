import argparse
import shutil
from pathlib import Path

from app.paths import get_default_data_root, get_project_root
from app.ui import launch_app


def _resolve_db_path(db_arg: str | None) -> str:
    if db_arg:
        return str(Path(db_arg).expanduser())
    data_root = get_default_data_root("hOCG_helper")
    return str(data_root / "hololive_ocg.sqlite")


def _copy_bundled_db(db_path: Path) -> None:
    if db_path.exists() and db_path.stat().st_size > 0:
        return

    project_root = get_project_root()
    bundled_candidates = [
        project_root / "data" / "hololive_ocg.sqlite",
        project_root / "assets" / "hololive_ocg.sqlite",
    ]

    for candidate in bundled_candidates:
        if not candidate.exists() or not candidate.is_file():
            continue
        if candidate.resolve() == db_path.resolve():
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate, db_path)
        return


def main() -> None:
    ap = argparse.ArgumentParser(description="Launch hololive OCG helper UI.")
    ap.add_argument("--db", default=None)
    # Flet runtime may pass extra args; ignore unknown to avoid startup crash.
    args, _unknown = ap.parse_known_args()
    db_path = _resolve_db_path(args.db)
    if args.db is None:
        _copy_bundled_db(Path(db_path))
    launch_app(db_path)

if __name__ == "__main__":
    main()
