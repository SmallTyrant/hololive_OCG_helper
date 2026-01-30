import argparse
from app.ui import launch_app

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    args = ap.parse_args()
    launch_app(args.db)

if __name__ == "__main__":
    main()
