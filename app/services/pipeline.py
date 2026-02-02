# app/services/pipeline.py
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator

CARD_NUMBER_RE = re.compile(r"\b[hH][A-Za-z]{1,5}\d{2}-\d{3}\b")

def _py() -> str:
    return sys.executable

def _mask_card_numbers(text: str) -> str:
    return CARD_NUMBER_RE.sub("[REDACTED]", text)

def _stream_output(process: subprocess.Popen[str]) -> Iterator[str]:
    if process.stdout is None:
        raise RuntimeError("process stdout not available")
    for line in process.stdout:
        yield _mask_card_numbers(line.rstrip("\n"))


def run_update_and_refine(db_path: str, delay: float = 0.1, workers: int = 8):
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
    p1 = subprocess.Popen(
        cmd1,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    for line in _stream_output(p1):
        yield line
    rc1 = p1.wait()
    if rc1 != 0:
        raise RuntimeError(f"scrape failed rc={rc1}")

    # 2) refine
    cmd2 = [_py(), str(tool_refine), "--db", db_path]
    p2 = subprocess.Popen(
        cmd2,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    for line in _stream_output(p2):
        yield line
    rc2 = p2.wait()
    if rc2 != 0:
        raise RuntimeError(f"refine failed rc={rc2}")
