# app/services/pipeline.py
import os
import re
import shutil
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


def _find_project_root_with_tools() -> tuple[Path, Path, Path, Path] | None:
    pipeline_file = Path(__file__).resolve()
    candidates = [
        pipeline_file.parents[2],  # project root in local dev
        pipeline_file.parents[1],  # app root in packaged app
        pipeline_file.parents[2] / "app",  # fallback for unusual layouts
    ]
    seen: set[Path] = set()
    for root in candidates:
        if root in seen:
            continue
        seen.add(root)
        tool_scrape = root / "tools" / "hocg_tool2.py"
        tool_refine = root / "tools" / "hocg_refine_update.py"
        tool_ko = root / "tools" / "namuwiki_ko_import.py"
        if tool_scrape.exists() and tool_refine.exists() and tool_ko.exists():
            return root, tool_scrape, tool_refine, tool_ko
    return None


def _find_bundled_db() -> Path | None:
    pipeline_file = Path(__file__).resolve()
    roots = [
        pipeline_file.parents[1],  # .../app
        pipeline_file.parents[2],  # .../ (project root or extracted bundle root)
    ]
    candidates = [
        roots[0] / "assets" / "hololive_ocg.sqlite",
        roots[1] / "assets" / "hololive_ocg.sqlite",
        roots[1] / "app" / "assets" / "hololive_ocg.sqlite",
        roots[1] / "data" / "hololive_ocg.sqlite",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def _restore_db_from_bundle(db_path: str) -> Path | None:
    source = _find_bundled_db()
    if source is None:
        return None
    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == target.resolve():
        return source
    shutil.copyfile(source, target)
    return source


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
    located = _find_project_root_with_tools()
    if located is None:
        existing_db = Path(db_path)
        if existing_db.exists() and existing_db.is_file() and existing_db.stat().st_size > 0:
            yield "[INFO] DB 갱신 도구가 번들에 없어 기존 DB를 유지합니다."
            return
        restored = _restore_db_from_bundle(db_path)
        if restored is not None:
            yield f"[INFO] 모바일 번들 DB 복원: {restored}"
            yield "[DONE] DB 복원 완료"
            return
        expected_root = Path(__file__).resolve().parents[2]
        raise FileNotFoundError(
            f"missing: {expected_root / 'tools' / 'hocg_tool2.py'}; no bundled DB found"
        )

    root, tool_scrape, tool_refine, tool_ko = located

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
            raise RuntimeError(f"namuwiki import failed rc={rc3}")
