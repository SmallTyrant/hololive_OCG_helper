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

def _run_tool(
    cmd: list[str],
    root: Path,
    env: dict[str, str],
    label: str,
) -> Iterator[str]:
    process = subprocess.Popen(
        cmd,
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    for line in _stream_output(process):
        yield line
    rc = process.wait()
    if rc != 0:
        raise RuntimeError(f"{label} failed rc={rc}")


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
    tool_ko = root / "tools" / "namuwiki_ko_import.py"

    if not tool_scrape.exists():
        raise FileNotFoundError(f"missing: {tool_scrape}")
    if not tool_refine.exists():
        raise FileNotFoundError(f"missing: {tool_refine}")
    if not tool_ko.exists():
        raise FileNotFoundError(f"missing: {tool_ko}")

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
    yield from _run_tool(cmd1, root, env, "scrape")

    # 2) refine
    cmd2 = [_py(), str(tool_refine), "--db", db_path]
    yield from _run_tool(cmd2, root, env, "refine")

    sheet_url = ko_sheet_url or os.environ.get("HOCG_KO_SHEET_URL")
    sheet_gid = ko_sheet_gid or os.environ.get("HOCG_KO_SHEET_GID")

    if ko_page or ko_page_file or sheet_url:
        cmd3 = [_py(), str(tool_ko), "--db", db_path]
        if ko_page:
            cmd3.extend(["--page", ko_page])
        if ko_page_file:
            cmd3.extend(["--page-file", ko_page_file])
        if sheet_url:
            cmd3.extend(["--sheet-url", sheet_url])
        if sheet_gid:
            cmd3.extend(["--sheet-gid", sheet_gid])
        if ko_overwrite:
            cmd3.append("--overwrite")
        yield from _run_tool(cmd3, root, env, "namuwiki import")
