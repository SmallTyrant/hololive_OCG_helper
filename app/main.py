import argparse
from pathlib import Path

from app.paths import get_default_data_root
from app.ui import launch_app


def _resolve_db_path(db_arg: str | None) -> str:
    if db_arg:
        return str(Path(db_arg).expanduser())
    data_root = get_default_data_root("hOCG_helper")
    return str(data_root / "hololive_ocg.sqlite")


def main() -> None:
    ap = argparse.ArgumentParser(description="Launch hololive OCG helper UI.")
    ap.add_argument("--db", default=None)
    # Flet runtime may pass extra args; ignore unknown to avoid startup crash.
    args, _unknown = ap.parse_known_args()
    db_path = _resolve_db_path(args.db)
    launch_app(db_path)

if __name__ == "__main__":
    main()
