import argparse
from app.ui import launch_app

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/hololive_ocg.sqlite")
    args = ap.parse_args()
    launch_app(args.db)

if __name__ == "__main__":
    main()
