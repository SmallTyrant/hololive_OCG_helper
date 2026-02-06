# app/services/pipeline.py
import os
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


def run_update_and_refine(
    db_path: str,
    delay: float = 0.1,
    workers: int = 8,
    *,
    ko_page: str | None = None,
    ko_page_file: str | None = None,
    ko_overwrite: bool = False,
    ko_sheet_url: str | None = None,
    ko_sheet_gid: str | None = None,
):
    """
    tools/hocg_tool2.py scrape -> tools/hocg_refine_update.py
    stdout 라인 단위로 yield
    """
    root = Path(__file__).resolve().parents[2]  # project root
    tool_scrape = root / "tools" / "hocg_tool2.py"
    tool_refine = root / "tools" / "hocg_refine_update.py"
    tool_ko_sheet = root / "tools" / "namuwiki_ko_import.py"
    tool_ko_bulk = root / "tools" / "namuwiki_ko_bulk_import.py"

    if not tool_scrape.exists():
        raise FileNotFoundError(f"missing: {tool_scrape}")
    if not tool_refine.exists():
        raise FileNotFoundError(f"missing: {tool_refine}")
    if not tool_ko_sheet.exists():
        raise FileNotFoundError(f"missing: {tool_ko_sheet}")
    if not tool_ko_bulk.exists():
        raise FileNotFoundError(f"missing: {tool_ko_bulk}")

    env = dict(**os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

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
        errors="replace",
        env=env,
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
        errors="replace",
        env=env,
    )
    for line in _stream_output(p2):
        yield line
    rc2 = p2.wait()
    if rc2 != 0:
        raise RuntimeError(f"refine failed rc={rc2}")

    sheet_url = ko_sheet_url or os.environ.get("HOCG_KO_SHEET_URL")
    sheet_gid = ko_sheet_gid or os.environ.get("HOCG_KO_SHEET_GID")

    if ko_page or ko_page_file:
        cmd3 = [_py(), str(tool_ko_bulk), "--db", db_path]
        if ko_page:
            cmd3.extend(["--page", ko_page])
        if ko_page_file:
            cmd3.extend(["--page-file", ko_page_file])
        if ko_overwrite:
            cmd3.append("--overwrite")
        p3 = subprocess.Popen(
            cmd3,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        for line in _stream_output(p3):
            yield line
        rc3 = p3.wait()
        if rc3 != 0:
            raise RuntimeError(f"namuwiki bulk import failed rc={rc3}")

    if sheet_url:
        cmd4 = [_py(), str(tool_ko_sheet), "--db", db_path, "--sheet-url", sheet_url]
        if sheet_gid:
            cmd4.extend(["--sheet-gid", sheet_gid])
        if ko_overwrite:
            cmd4.append("--overwrite")
        p4 = subprocess.Popen(
            cmd4,
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        for line in _stream_output(p4):
            yield line
        rc4 = p4.wait()
        if rc4 != 0:
            raise RuntimeError(f"sheet import failed rc={rc4}")
