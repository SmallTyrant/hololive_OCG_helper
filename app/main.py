import argparse
import shutil
import sys
import types
from pathlib import Path
from urllib.error import HTTPError as UrlHTTPError
from urllib.error import URLError
from urllib.parse import quote as url_quote
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.paths import get_default_data_root, get_project_root

APP_NAME = "hOCG_H"


def _install_requests_shim_if_missing() -> None:
    try:
        __import__("requests")
        return
    except ModuleNotFoundError:
        pass

    module = types.ModuleType("requests")

    class RequestException(Exception):
        pass

    class HTTPError(RequestException):
        pass

    class _Response:
        def __init__(self, body: bytes, status_code: int, url: str) -> None:
            self._body = body
            self.status_code = status_code
            self.url = url

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise HTTPError(f"{self.status_code} Client Error: {self.url}")

        def iter_content(self, chunk_size: int = 1024 * 256):
            if chunk_size <= 0:
                chunk_size = 1024 * 256
            for start in range(0, len(self._body), chunk_size):
                yield self._body[start : start + chunk_size]

    def get(url: str, timeout: int = 30, stream: bool = False, **kwargs):
        headers = kwargs.get("headers") or {}
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=timeout) as response:
                status = int(getattr(response, "status", 200))
                body = response.read()
                return _Response(body, status, url)
        except UrlHTTPError as ex:
            body = ex.read() if hasattr(ex, "read") else b""
            return _Response(body, int(getattr(ex, "code", 500)), url)
        except URLError as ex:
            raise RequestException(str(ex)) from ex

    module.get = get
    module.RequestException = RequestException
    module.HTTPError = HTTPError
    module.utils = types.SimpleNamespace(quote=url_quote)
    sys.modules["requests"] = module


def _resolve_db_path(db_arg: str | None) -> str:
    if db_arg:
        return str(Path(db_arg).expanduser())
    data_root = get_default_data_root(APP_NAME)
    return str(data_root / "hololive_ocg.sqlite")


def _copy_bundled_db(db_path: Path) -> None:
    if db_path.exists() and db_path.stat().st_size > 0:
        return

    project_root = get_project_root()
    bundled_candidates = [
        project_root / "data" / "hololive_ocg.sqlite",
        project_root / "assets" / "hololive_ocg.sqlite",
    ]

    for candidate in bundled_candidates:
        if not candidate.exists() or not candidate.is_file():
            continue
        if candidate.resolve() == db_path.resolve():
            return
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(candidate, db_path)
        return


def main() -> None:
    _install_requests_shim_if_missing()
    from app.ui import launch_app

    ap = argparse.ArgumentParser(description="Launch hOCG_H UI.")
    ap.add_argument("--db", default=None)
    args = ap.parse_args()
    db_path = _resolve_db_path(args.db)
    if args.db is None:
        _copy_bundled_db(Path(db_path))
    launch_app(db_path)

if __name__ == "__main__":
    main()
