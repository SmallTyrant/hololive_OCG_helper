import argparse
from pathlib import Path

from app.paths import get_default_data_root
from app.ui import launch_app

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None)
    args = ap.parse_args()
    if args.db:
        db_path = str(Path(args.db).expanduser())
    else:
        data_root = get_default_data_root("hOCG_helper")
        db_path = str(data_root / "hololive_ocg.sqlite")
    launch_app(db_path)

if __name__ == "__main__":
    main()
