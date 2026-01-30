# app/services/images.py
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = "https://hololive-official-cardgame.com"

def images_dir(project_root: Path) -> Path:
    d = project_root / "data" / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d

def local_image_path(project_root: Path, card_number: str) -> Path:
    # 파일명은 card_number 그대로. 확장자 png 통일
    safe = card_number.strip()
    return images_dir(project_root) / f"{safe}.png"

def resolve_url(image_url: str) -> str:
    if not image_url:
        return ""
    # DB에 "/wp-content/..." 같은 상대경로가 들어오는 케이스 대응
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    return urljoin(BASE, image_url)

def download_image(url: str, dest: Path, timeout: int = 30) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    u = resolve_url(url)
    if not u:
        raise ValueError("empty image url")

    r = requests.get(u, timeout=timeout)
    r.raise_for_status()

    # 원자적 저장(임시→교체)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    with open(tmp, "wb") as f:
        f.write(r.content)
    os.replace(tmp, dest)
