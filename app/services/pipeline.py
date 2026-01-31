# app/services/pipeline.py
import subprocess
import sys
from pathlib import Path

def _py():
    return sys.executable

def run_update_and_refine(db_path: str, delay: float = 0.6, workers: int = 1):
    """
    tools/hocg_tool2.py scrape -> tools/hocg_refine_update.py
    stdout 라인 단위로 yield
    """
    root = Path(__file__).resolve().parents[2]  # project root
    tool_scrape = root / "tools" / "hocg_tool2.py"
    tool_refine = root / "tools" / "hocg_refine_update.py"

    if not tool_scrape.exists():
        raise FileNotFoundError(f"missing: {tool_scrape}")
    if not tool_refine.exists():
        raise FileNotFoundError(f"missing: {tool_refine}")

    # 1) scrape
    cmd1 = [
        _py(),
        str(tool_scrape),
        "--db",
        db_path,
        "scrape",
        "--delay",
        str(delay),
        "--workers",
        str(workers),
    ]
    p1 = subprocess.Popen(cmd1, cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    for line in p1.stdout:
        yield line.rstrip("\n")
    rc1 = p1.wait()
    if rc1 != 0:
        raise RuntimeError(f"scrape failed rc={rc1}")

    # 2) refine
    cmd2 = [_py(), str(tool_refine), "--db", db_path]
    p2 = subprocess.Popen(cmd2, cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    for line in p2.stdout:
        yield line.rstrip("\n")
    rc2 = p2.wait()
    if rc2 != 0:
        raise RuntimeError(f"refine failed rc={rc2}")
