# app/services/pipeline.py
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import json
from pathlib import Path
from typing import Iterator
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CARD_NUMBER_RE = re.compile(r"\b[hH][A-Za-z]{1,5}\d{2}-\d{3}\b")
GITHUB_REPO = "SmallTyrant/hololive_OCG_helper"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LATEST_DB_DIRECT_URL = f"https://github.com/{GITHUB_REPO}/releases/latest/download/hololive_ocg.sqlite"

def _py() -> str:
    return sys.executable

def _mask_card_numbers(text: str) -> str:
    return CARD_NUMBER_RE.sub("[REDACTED]", text)

def _stream_output(process: subprocess.Popen[str]) -> Iterator[str]:
    if process.stdout is None:
        raise RuntimeError("process stdout not available")
    for line in process.stdout:
        yield _mask_card_numbers(line.rstrip("\n"))


def _pick_release_db_asset(release: dict) -> tuple[str, str]:
    assets = release.get("assets") or []
    if not assets:
        raise RuntimeError("latest release has no assets")

    preferred_names = ("hololive_ocg.sqlite",)
    db_extensions = (".sqlite", ".sqlite3", ".db")

    for preferred in preferred_names:
        for asset in assets:
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            if name == preferred and url:
                return name, url

    for asset in assets:
        name = str(asset.get("name") or "")
        url = str(asset.get("browser_download_url") or "")
        if url and any(name.endswith(ext) for ext in db_extensions):
            return name, url

    names = ", ".join(str(a.get("name") or "") for a in assets)
    raise RuntimeError(f"no sqlite asset in latest release: {names}")


def _validate_sqlite(path: Path) -> None:
    if not path.exists() or not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("downloaded DB file is missing or empty")
    with open(path, "rb") as f:
        head = f.read(16)
    if head != b"SQLite format 3\x00":
        raise RuntimeError("downloaded file is not a valid SQLite database")

    conn = sqlite3.connect(path)
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prints'"
        ).fetchone()
        if not row:
            raise RuntimeError("downloaded DB is missing 'prints' table")
    finally:
        conn.close()


def _download_latest_release_db(db_path: str) -> tuple[str, str]:
    release = None
    req = Request(
        LATEST_RELEASE_API,
        headers={
            "User-Agent": "hOCG_H/1.1",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urlopen(req, timeout=20) as response:
            release = json.loads(response.read().decode("utf-8"))
    except Exception:
        release = None

    if release is not None:
        try:
            asset_name, asset_url = _pick_release_db_asset(release)
            tag = str(release.get("tag_name") or "latest")
        except Exception:
            asset_name, asset_url = "hololive_ocg.sqlite", LATEST_DB_DIRECT_URL
            tag = str(release.get("tag_name") or "latest")
    else:
        asset_name, asset_url = "hololive_ocg.sqlite", LATEST_DB_DIRECT_URL
        tag = "latest"

    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".download")

    dl_req = Request(
        asset_url,
        headers={
            "User-Agent": "hOCG_H/1.1",
            "Accept": "application/octet-stream",
        },
    )
    try:
        with urlopen(dl_req, timeout=120) as response, open(tmp, "wb") as f:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        _validate_sqlite(tmp)
        os.replace(tmp, target)
    except HTTPError as ex:
        raise RuntimeError(f"DB asset HTTP {ex.code}") from ex
    except URLError as ex:
        raise RuntimeError(f"DB asset download failed: {ex}") from ex
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass

    return tag, asset_name


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
    1) GitHub Releases 최신 DB 다운로드
    2) 실패 시 로컬 tools 갱신 파이프라인 fallback
    stdout 라인 단위로 yield
    """
    try:
        yield "[INFO] GitHub Releases에서 최신 DB 확인 중..."
        tag, asset_name = _download_latest_release_db(db_path)
        yield f"[INFO] 다운로드 완료: {asset_name} (release: {tag})"
        yield "[DONE] DB 갱신 완료"
        return
    except Exception as ex:
        yield f"[WARN] 릴리즈 DB 다운로드 실패: {ex}"

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
