# app/services/images.py
import os
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE = "https://hololive-official-cardgame.com"
SAFE_CARD_NUMBER_RE = re.compile(r"[^A-Za-z0-9._-]+")

def _sanitize_card_number(card_number: str) -> str:
    safe = card_number.strip()
    if not safe:
        return "unknown"
    safe = safe.replace(os.sep, "_").replace("/", "_")
    safe = SAFE_CARD_NUMBER_RE.sub("_", safe)
    return safe or "unknown"

def images_dir(data_root: Path) -> Path:
    d = data_root / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d

def local_image_path(data_root: Path, card_number: str) -> Path:
    # 파일명은 card_number 그대로. 확장자 png 통일
    safe = _sanitize_card_number(card_number)
    return images_dir(data_root) / f"{safe}.png"

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

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        r = requests.get(u, timeout=timeout, stream=True)
        r.raise_for_status()
        # 원자적 저장(임시→교체)
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass
