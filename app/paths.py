from __future__ import annotations

import os
import sys
from pathlib import Path


def get_project_root() -> Path:
    # app/paths.py -> app/ -> project root
    return Path(__file__).resolve().parents[1]


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        probe.unlink()
        return True
    except Exception:
        return False


def get_app_data_dir(app_name: str) -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.getenv("APPDATA") or Path.home() / "AppData" / "Roaming")
    else:
        base = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    path = base / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_data_root(app_name: str) -> Path:
    project_root = get_project_root()
    preferred = project_root / "data"
    if _is_writable_dir(preferred):
        return preferred
    return get_app_data_dir(app_name)
