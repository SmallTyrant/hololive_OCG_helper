# app/services/images.py
import os
import re
import hashlib
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

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

def local_image_path(data_root: Path, card_number: str, variant: str | None = None) -> Path:
    safe = _sanitize_card_number(card_number)
    if variant and variant.strip():
        variant_hash = hashlib.sha1(variant.strip().encode("utf-8")).hexdigest()[:10]
        safe = f"{safe}__{_sanitize_card_number(variant)}__{variant_hash}"
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
        req = Request(u, headers={"User-Agent": "hOCG_H/1.1"})
        # 원자적 저장(임시→교체)
        with urlopen(req, timeout=timeout) as response, open(tmp, "wb") as f:
            while True:
                chunk = response.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass
