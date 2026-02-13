# app/ui.py
from __future__ import annotations

import asyncio
import sqlite3
import threading
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import flet as ft

from app.services.db import (
    open_db,
    query_suggest,
    query_exact,
    load_card_detail,
    get_print_brief,
    db_exists,
    clear_conn_cache,
)
from app.services.pipeline import run_update_and_refine, get_latest_release_db_info
from app.paths import get_default_data_root, get_project_root
from app.services.images import local_image_path, download_image, resolve_url
from app.services.verify import run_startup_checks

COLORS = ft.Colors if hasattr(ft, "Colors") else ft.colors
ICONS = ft.Icons if hasattr(ft, "Icons") else ft.icons
SECTION_LABELS = (
    "カードタイプ",
    "タグ",
    "レアリティ",
    "推しスキル",
    "SP推しスキル",
    "アーツ",
    "エクストラ",
    "Bloomレベル",
    "キーワード",
    "LIFE",
    "HP",
)

DB_MISSING_TOAST = "DB파일이 존재하지 않습니다. 메뉴에서 DB 수동갱신을 실행해주세요"
DB_UPDATING_TOAST = "갱신중..."
DB_UPDATED_TOAST = "갱신완료"
APP_NAME = "hOCG_H"
SEARCH_MODE_PARTIAL = "partial"
SEARCH_MODE_EXACT = "exact"
MOBILE_SAFE_BOTTOM_PADDING = 34

def with_opacity(opacity: float, color: str) -> str:
    return COLORS.with_opacity(opacity, color)

def _center_alignment():
    if hasattr(ft, "Alignment"):
        return ft.Alignment.CENTER if hasattr(ft.Alignment, "CENTER") else ft.Alignment(0.0, 0.0)
    if hasattr(ft, "alignment") and hasattr(ft.alignment, "center"):
        return ft.alignment.center
    return None

ALIGN_CENTER = _center_alignment()

def _image_fit_contain():
    if hasattr(ft, "ImageFit"):
        return ft.ImageFit.CONTAIN
    if hasattr(ft, "BoxFit"):
        return ft.BoxFit.CONTAIN
    return None

IMAGE_FIT_CONTAIN = _image_fit_contain()
MENU_ICON = ICONS.MENU if hasattr(ICONS, "MENU") else ICONS.MORE_VERT

def icon_dir(project_root: Path) -> Path:
    return project_root / "app"

def icon_paths(project_root: Path) -> tuple[Path, Path]:
    d = icon_dir(project_root)
    png_path = d / "app_icon.png"
    return d / "app_icon.ico", png_path


def launch_app(db_path: str) -> None:
    project_root = get_project_root()
    data_root = get_default_data_root(APP_NAME)

    def main(page: ft.Page) -> None:
        thread_local = threading.local()
        conn_epoch = {"value": 0}
        db_health_cache = {"path": None, "value": None, "checked_at": 0.0}
        DB_HEALTH_CACHE_TTL = 2.0

        page.title = APP_NAME
        page.padding = 0

        def is_mobile_platform() -> bool:
            platform = getattr(page, "platform", None)
            if hasattr(ft, "PagePlatform") and platform in (
                ft.PagePlatform.IOS,
                ft.PagePlatform.ANDROID,
            ):
                return True
            platform_name = str(platform).lower()
            user_agent = (getattr(page, "client_user_agent", "") or "").lower()
            return any(token in platform_name for token in ("ios", "android")) or any(
                token in user_agent for token in ("iphone", "ipad", "android")
            )

        def get_view_size() -> tuple[float, float]:
            # Flet 0.80+에서는 page.window_width/page.window_height가 기본 속성이 아님.
            # 모바일에서 해당 속성을 직접 읽으면 AttributeError가 날 수 있어 안전하게 조회.
            window = getattr(page, "window", None)
            window_width = getattr(window, "width", None) if window is not None else None
            window_height = getattr(window, "height", None) if window is not None else None
            legacy_width = getattr(page, "window_width", None)
            legacy_height = getattr(page, "window_height", None)
            width = window_width or legacy_width or getattr(page, "width", None) or 0
            height = window_height or legacy_height or getattr(page, "height", None) or 0
            return float(width), float(height)

        def set_desktop_window_size(width: int, height: int) -> None:
            window = getattr(page, "window", None)
            if window is not None:
                try:
                    window.width = width
                    window.height = height
                    return
                except Exception:
                    pass
            # 구버전/호환 경로
            page.window_width = width
            page.window_height = height

        if not is_mobile_platform():
            set_desktop_window_size(1280, 820)

        # --- Controls ---
        tf_db = ft.TextField(label="DB", value=db_path, expand=True)
        tf_search = ft.TextField(label="카드번호 / 이름 / 태그 검색", expand=True)
        btn_menu = ft.IconButton(icon=MENU_ICON, tooltip="메뉴")
        update_progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        update_status = ft.Text("", size=12, color=COLORS.RED_300, visible=False)

        # --- Results / Detail ---
        lv = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        detail_lv = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        detail_texts = {"ko": ""}

        # --- Image area ---
        def build_image_placeholder(text: str, loading: bool = False) -> ft.Control:
            marker: ft.Control
            if loading:
                marker = ft.ProgressRing(width=24, height=24, stroke_width=2)
            else:
                marker = ft.Icon(ICONS.IMAGE_NOT_SUPPORTED_OUTLINED, size=28, color=COLORS.GREY_400)
            return ft.Container(
                content=ft.Column(
                    [marker, ft.Text(text, color=COLORS.GREY_400)],
                    spacing=8,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                alignment=ALIGN_CENTER,
                expand=True,
                border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
            )

        def build_image_widget(
            image_path: Path | None,
            image_url: str | None = None,
            *,
            loading: bool = False,
            placeholder_text: str = "이미지 없음",
        ) -> ft.Control:
            if loading:
                return build_image_placeholder("이미지 로딩 중...", loading=True)

            error_content = build_image_placeholder("이미지 로딩 실패")
            if image_path and image_path.exists():
                return ft.Image(
                    src=str(image_path),
                    fit=IMAGE_FIT_CONTAIN,
                    expand=True,
                    error_content=error_content,
                )
            if image_url:
                return ft.Image(
                    src=image_url,
                    fit=IMAGE_FIT_CONTAIN,
                    expand=True,
                    error_content=error_content,
                )
            return build_image_placeholder(placeholder_text)

        img_container = ft.Container(
            content=build_image_widget(None),
            expand=True,
            padding=10,
            bgcolor=None,
            border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
        )

        selected_print_id = {"id": None}
        selected_card_number = {"no": ""}
        selected_image_url = {"url": ""}
        results_state = {"rows": []}
        image_panel_state = {"collapsed": False}
        search_mode_state = {"value": SEARCH_MODE_PARTIAL}
        update_state = {"running": False}
        update_prompt_state = {"shown": False}
        downloading = set()
        download_lock = threading.Lock()

        def append_log(s: str) -> None:
            print(s, flush=True)

        toast_text = ft.Text(
            "",
            size=14,
            weight=ft.FontWeight.W_600,
            color=COLORS.WHITE,
            text_align=ft.TextAlign.CENTER,
        )
        toast_card = ft.Container(
            content=toast_text,
            padding=ft.padding.symmetric(horizontal=18, vertical=10),
            bgcolor=with_opacity(0.88, COLORS.BLACK),
            border=ft.border.all(1, with_opacity(0.12, COLORS.WHITE)),
            border_radius=18,
            shadow=[
                ft.BoxShadow(
                    blur_radius=18,
                    color=with_opacity(0.35, COLORS.BLACK),
                    offset=ft.Offset(0, 6),
                )
            ],
        )
        toast_host = ft.Container(
            content=toast_card,
            alignment=ALIGN_CENTER,
            expand=True,
            visible=False,
        )
        page.overlay.append(ft.TransparentPointer(content=toast_host, expand=True))
        page.update()

        toast_state = {"seq": 0, "message": None}

        def invalidate_db_health_cache() -> None:
            db_health_cache["path"] = None
            db_health_cache["value"] = None
            db_health_cache["checked_at"] = 0.0

        def needs_db_update() -> bool:
            path = (tf_db.value or "").strip()
            now = time.monotonic()
            if (
                db_health_cache["path"] == path
                and db_health_cache["value"] is not None
                and now - db_health_cache["checked_at"] < DB_HEALTH_CACHE_TTL
            ):
                return bool(db_health_cache["value"])
            if not path:
                db_health_cache.update({"path": path, "value": True, "checked_at": now})
                return True
            try:
                p = Path(path)
                if not p.exists() or not p.is_file() or p.stat().st_size == 0:
                    db_health_cache.update({"path": path, "value": True, "checked_at": now})
                    return True
            except Exception:
                db_health_cache.update({"path": path, "value": True, "checked_at": now})
                return True
            try:
                conn = sqlite3.connect(path)
                try:
                    row = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='prints'"
                    ).fetchone()
                    if not row:
                        db_health_cache.update({"path": path, "value": True, "checked_at": now})
                        return True
                    count = conn.execute("SELECT COUNT(1) FROM prints").fetchone()
                    value = (count[0] if count else 0) == 0
                    db_health_cache.update(
                        {"path": path, "value": value, "checked_at": now}
                    )
                    return value
                finally:
                    conn.close()
            except Exception:
                db_health_cache.update({"path": path, "value": True, "checked_at": now})
                return True

        def show_toast(
            message: str,
            persist: bool = False,
            duration_ms: int | None = None,
            restore_missing_after: bool = False,
        ) -> None:
            if (
                toast_state["message"] == message
                and persist
                and duration_ms is None
            ):
                return

            toast_state["seq"] += 1
            seq = toast_state["seq"]
            toast_state["message"] = message

            toast_text.value = message
            toast_host.visible = True
            if toast_host.page is None:
                page.update()
            if toast_host.page is not None:
                toast_host.update()

            if duration_ms is not None and duration_ms > 0:
                async def _after_hide(
                    token: int,
                    delay_ms: int,
                    should_restore_missing: bool,
                    keep_persist: bool,
                ) -> None:
                    await asyncio.sleep(delay_ms / 1000.0)
                    if toast_state["seq"] != token:
                        return
                    if keep_persist:
                        return
                    toast_host.visible = False
                    if should_restore_missing and needs_db_update():
                        show_toast(DB_MISSING_TOAST, persist=True)
                    page.update()

                page.run_task(
                    _after_hide,
                    seq,
                    duration_ms,
                    restore_missing_after,
                    persist,
                )

        def format_iso_date(value: str | None) -> str | None:
            raw = (value or "").strip()
            if not raw:
                return None
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(raw)
            except Exception:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).date().isoformat()

        def local_db_date(path_value: str) -> str | None:
            path = (path_value or "").strip()
            if not path:
                return None
            try:
                p = Path(path)
                if not p.exists() or not p.is_file() or p.stat().st_size == 0:
                    return None
                conn = sqlite3.connect(str(p))
                try:
                    has_meta = conn.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
                    ).fetchone()
                    if has_meta:
                        for key in (
                            "release_asset_updated_at",
                            "release_published_at",
                            "release_created_at",
                        ):
                            row = conn.execute(
                                "SELECT value FROM meta WHERE key=?",
                                (key,),
                            ).fetchone()
                            if row and row[0]:
                                normalized = format_iso_date(str(row[0]))
                                if normalized:
                                    return normalized

                    for table in ("prints", "card_texts_ko", "card_texts_ja"):
                        has_table = conn.execute(
                            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                            (table,),
                        ).fetchone()
                        if not has_table:
                            continue
                        row = conn.execute(
                            f"SELECT MAX(updated_at) FROM {table} WHERE updated_at IS NOT NULL AND updated_at <> ''"
                        ).fetchone()
                        if row and row[0]:
                            normalized = format_iso_date(str(row[0]))
                            if normalized:
                                return normalized
                finally:
                    conn.close()

                ts = p.stat().st_mtime
                return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
            except Exception:
                return None

        def setup_window_icon() -> None:
            ico_path, png_path = icon_paths(project_root)

            def set_icon(path: Path) -> bool:
                try:
                    page.window.icon = str(path)
                    return True
                except Exception as ex:
                    append_log(f"[WARN] 앱 아이콘 설정 실패: {ex}")
                    return False

            def ensure_ico_from_png() -> bool:
                if not png_path.exists():
                    return False
                try:
                    if ico_path.exists() and ico_path.stat().st_mtime >= png_path.stat().st_mtime:
                        return True
                except Exception:
                    pass
                try:
                    from PIL import Image
                except Exception as ex:
                    append_log(f"[WARN] 앱 아이콘 변환 실패(PIL): {ex}")
                    return False
                try:
                    ico_path.parent.mkdir(parents=True, exist_ok=True)
                    img = Image.open(png_path)
                    if img.mode not in ("RGBA", "RGB"):
                        img = img.convert("RGBA")
                    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
                    img.save(ico_path, format="ICO", sizes=sizes)
                    return True
                except Exception as ex:
                    append_log(f"[WARN] 앱 아이콘 변환 실패: {ex}")
                    return False

            is_windows = sys.platform.startswith("win")

            # Windows: prefer ICO; PNG can be ignored by the OS without error.
            if is_windows:
                if ico_path.exists() or ensure_ico_from_png():
                    if set_icon(ico_path):
                        return
                if png_path.exists():
                    set_icon(png_path)
                return

            # Non-Windows: PNG first, ICO fallback.
            if png_path.exists() and set_icon(png_path):
                return
            if ico_path.exists() and set_icon(ico_path):
                return
            if ensure_ico_from_png():
                set_icon(ico_path)

        setup_window_icon()

        async def run_startup_checks_async() -> None:
            issues = await asyncio.to_thread(run_startup_checks, tf_db.value, data_root)
            for issue in issues:
                append_log(f"[WARN] {issue}")

        def get_conn() -> sqlite3.Connection:
            path = tf_db.value
            if not path or not path.strip():
                raise ValueError("DB 경로가 비어있습니다.")
            conn = getattr(thread_local, "conn", None)
            if (
                conn is None
                or getattr(thread_local, "epoch", -1) != conn_epoch["value"]
                or getattr(thread_local, "path", None) != path
            ):
                try:
                    if conn is not None:
                        clear_conn_cache(conn)
                        conn.close()
                except Exception:
                    pass
                conn = open_db(path)
                thread_local.conn = conn
                thread_local.epoch = conn_epoch["value"]
                thread_local.path = path
            return conn

        def close_thread_conn() -> None:
            conn = getattr(thread_local, "conn", None)
            if conn is not None:
                try:
                    clear_conn_cache(conn)
                    conn.close()
                except Exception:
                    pass
            thread_local.conn = None
            thread_local.epoch = -1
            thread_local.path = None

        def set_image_for_card(
            card_number: str,
            image_url: str | None = None,
            *,
            loading: bool = False,
            placeholder_text: str = "이미지 없음",
        ) -> None:
            image_path = local_image_path(data_root, card_number) if card_number else None
            resolved = resolve_url((image_url or "").strip())
            img_container.content = build_image_widget(
                image_path if image_path and image_path.exists() else None,
                resolved,
                loading=loading and not (image_path and image_path.exists()),
                placeholder_text=placeholder_text,
            )
            page.update()

        def clear_image(placeholder_text: str = "이미지 없음") -> None:
            img_container.content = build_image_widget(None, placeholder_text=placeholder_text)
            page.update()

        async def download_selected_image(
            card_number: str,
            image_url: str,
        ) -> None:
            dest = local_image_path(data_root, card_number)
            try:
                append_log(f"[IMG] downloading: {card_number} -> {dest.name}")
                await asyncio.to_thread(download_image, image_url, dest)
                append_log("[IMG] done")
                if selected_card_number["no"] == card_number:
                    set_image_for_card(card_number, image_url)
            except Exception as ex:
                append_log(f"[IMG][ERROR] {ex}")
                if selected_card_number["no"] == card_number:
                    clear_image("이미지 로딩 실패")
            finally:
                with download_lock:
                    downloading.discard(card_number)
                page.update()

        def ensure_image_download(card_number: str, image_url: str) -> None:
            if not card_number:
                clear_image()
                return

            resolved_url = resolve_url((image_url or "").strip())
            dest = local_image_path(data_root, card_number)

            if dest.exists():
                set_image_for_card(card_number, resolved_url)
                return

            if not resolved_url:
                clear_image("이미지 URL 없음")
                return

            with download_lock:
                if card_number in downloading:
                    return
                downloading.add(card_number)

            page.run_task(download_selected_image, card_number, resolved_url)

        def build_section_chip(text: str) -> ft.Control:
            return ft.Container(
                content=ft.Text(text, weight=ft.FontWeight.BOLD, size=12),
                bgcolor=with_opacity(0.18, COLORS.BLUE_GREY_700),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=12,
            )

        def build_detail_line(line: str) -> ft.Control:
            if line in SECTION_LABELS:
                return build_section_chip(line)

            for label in SECTION_LABELS:
                if line.startswith(label + " "):
                    rest = line[len(label):]
                    return ft.Text(
                        spans=[
                            ft.TextSpan(label, style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                            ft.TextSpan(rest),
                        ]
                    )
            return ft.Text(line)

        def append_detail_lines(text: str) -> None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for line in lines:
                detail_lv.controls.append(build_detail_line(line))

        def render_detail() -> None:
            detail_lv.controls.clear()
            ko = (detail_texts["ko"] or "").strip()

            if ko:
                detail_lv.controls.append(build_section_chip("한국어"))
                append_detail_lines(ko)
            else:
                detail_lv.controls.append(ft.Text("(한국어 본문 없음)"))

            page.update()

        def set_detail_text(ko_text: str | None) -> None:
            detail_texts["ko"] = (ko_text or "")
            render_detail()

        def clear_selection() -> None:
            selected_print_id["id"] = None
            selected_card_number["no"] = ""
            selected_image_url["url"] = ""
            set_detail_text("")
            clear_image("카드를 선택하세요")

        def render_result_list() -> None:
            lv.controls.clear()
            rows = results_state["rows"]
            if not rows:
                lv.controls.append(
                    ft.Container(
                        content=ft.Text("검색 결과가 없습니다.", color=COLORS.GREY_400),
                        padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    )
                )
                return

            for row in rows:
                pid = row["print_id"]
                card_number = (row.get("card_number") or "").strip()
                name_ko = (row.get("name_ko") or "").strip()
                name_ja = (row.get("name_ja") or "").strip()
                display_name = name_ko or name_ja or "(이름 없음)"
                title = f"{card_number} | {display_name}" if card_number else display_name
                is_selected = selected_print_id["id"] == pid
                lv.controls.append(
                    ft.ListTile(
                        title=ft.Text(title),
                        selected=is_selected,
                        selected_tile_color=with_opacity(0.22, COLORS.BLUE_GREY_700),
                        selected_color=COLORS.WHITE,
                        dense=True,
                        on_click=lambda e, _pid=pid: show_detail(_pid),
                    )
                )

        def show_detail(pid: int) -> None:
            selected_print_id["id"] = pid
            render_result_list()

            try:
                conn = get_conn()
                brief = get_print_brief(conn, pid) or {}
                selected_card_number["no"] = (brief.get("card_number") or "").strip()
                selected_image_url["url"] = resolve_url((brief.get("image_url") or "").strip())

                if selected_card_number["no"]:
                    set_image_for_card(
                        selected_card_number["no"],
                        selected_image_url["url"],
                        loading=True,
                        placeholder_text="이미지 없음",
                    )
                    ensure_image_download(
                        selected_card_number["no"],
                        selected_image_url["url"],
                    )
                else:
                    clear_image("이미지 없음")

                card = load_card_detail(conn, pid)
                set_detail_text(card.get("ko_text", "") if card else None)

            except Exception as ex:
                set_detail_text(f"[ERROR] 상세 로드 실패: {ex}")
                clear_image("이미지 로딩 실패")

            page.update()

        def refresh_list() -> None:
            query = (tf_search.value or "").strip()
            results_state["rows"] = []
            selected_print_id["id"] = None

            if not query:
                render_result_list()
                clear_selection()
                page.update()
                return

            if needs_db_update():
                append_log("[INFO] DB가 없거나 손상되어 검색 불가. 메뉴에서 DB 수동갱신을 실행하세요.")
                show_toast(DB_MISSING_TOAST, persist=True)
                render_result_list()
                clear_selection()
                page.update()
                return

            try:
                conn = get_conn()
                if search_mode_state["value"] == SEARCH_MODE_EXACT:
                    results_state["rows"] = query_exact(conn, query)
                else:
                    results_state["rows"] = query_suggest(conn, query)
                render_result_list()
                if results_state["rows"]:
                    show_detail(results_state["rows"][0]["print_id"])
                else:
                    clear_selection()
            except Exception as ex:
                message = f"검색 실패: {ex}"
                append_log(f"[ERROR] {message}")
                update_status.value = message
                update_status.visible = True
                update_status.color = COLORS.RED_300
                render_result_list()
                clear_selection()

            page.update()

        def on_search_change(e) -> None:
            refresh_list()

        tf_search.on_change = on_search_change
        tf_search.on_submit = on_search_change

        def on_search_mode_change(e) -> None:
            selected_mode = (
                (getattr(e, "data", None) if e is not None else None)
                or (getattr(getattr(e, "control", None), "value", None) if e is not None else None)
                or search_mode_group.value
                or SEARCH_MODE_PARTIAL
            ).strip()
            if selected_mode not in (SEARCH_MODE_PARTIAL, SEARCH_MODE_EXACT):
                selected_mode = SEARCH_MODE_PARTIAL
            if search_mode_state["value"] == selected_mode:
                return
            search_mode_state["value"] = selected_mode
            show_toast(
                "검색 모드: 정확 일치(태그/카드번호/이름)"
                if selected_mode == SEARCH_MODE_EXACT
                else "검색 모드: 일부 일치",
                duration_ms=1300,
            )
            refresh_list()

        def on_db_change(e) -> None:
            invalidate_db_health_cache()
            update_prompt_state["shown"] = False

        tf_db.on_change = on_db_change

        def set_update_running(running: bool) -> None:
            update_state["running"] = running
            btn_menu.disabled = running
            btn_manual_update.disabled = running
            tf_search.disabled = running
            tf_db.disabled = running
            update_progress.visible = running

        def set_update_status(message: str = "", is_error: bool = False) -> None:
            text = (message or "").strip()
            update_status.value = text
            update_status.visible = bool(text)
            update_status.color = COLORS.RED_300 if is_error else COLORS.GREEN_300

        def run_update_pipeline_blocking(dbp: str) -> None:
            for line in run_update_and_refine(dbp):
                append_log(line)

        async def do_update_async() -> None:
            if update_state["running"]:
                return

            dbp = (tf_db.value or "").strip()
            if not dbp:
                set_update_status("DB 경로가 비어 있습니다.", is_error=True)
                show_toast("DB 경로가 비어 있습니다.", duration_ms=3000)
                page.update()
                return

            try:
                set_update_running(True)
                set_update_status("DB 갱신 중...")
                show_toast(DB_UPDATING_TOAST, persist=True)
                page.update()

                append_log("[START] DB 갱신")
                await asyncio.to_thread(run_update_pipeline_blocking, dbp)
                append_log("[DONE] DB 갱신")

                conn_epoch["value"] += 1
                close_thread_conn()
                invalidate_db_health_cache()

                set_update_status("DB 갱신 완료")
                show_toast(
                    DB_UPDATED_TOAST,
                    duration_ms=3000,
                    restore_missing_after=True,
                )
                refresh_list()
            except Exception as ex:
                message = f"DB 갱신 실패: {ex}"
                append_log(f"[ERROR] {message}")
                set_update_status(message, is_error=True)
                show_toast(message, duration_ms=4000, restore_missing_after=True)
                if needs_db_update():
                    show_toast(DB_MISSING_TOAST, persist=True)
            finally:
                set_update_running(False)
                page.update()

        search_mode_group = ft.RadioGroup(
            value=search_mode_state["value"],
            on_change=on_search_mode_change,
            content=ft.Column(
                [
                    ft.Radio(
                        value=SEARCH_MODE_PARTIAL,
                        label="일부 일치 검색 (기본)",
                    ),
                    ft.Radio(
                        value=SEARCH_MODE_EXACT,
                        label="정확 검색",
                    ),
                ],
                tight=True,
                spacing=4,
            ),
        )

        db_update_dialog = ft.AlertDialog(modal=True)
        btn_manual_update = ft.ElevatedButton(
            "DB 수동갱신",
            icon=ICONS.SYNC,
        )
        menu_panel = ft.NavigationDrawer(
            controls=[
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text("메뉴", weight=ft.FontWeight.W_700),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.padding.only(left=16, right=16, top=14, bottom=4),
                ),
                ft.Container(
                    content=btn_manual_update,
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                ),
                ft.Divider(height=8),
                ft.Container(
                    content=ft.Text("DB 검색 옵션", weight=ft.FontWeight.W_600),
                    padding=ft.padding.only(left=16, right=16, top=4, bottom=2),
                ),
                ft.Container(
                    content=search_mode_group,
                    padding=ft.padding.symmetric(horizontal=16, vertical=4),
                ),
            ],
        )
        page.end_drawer = menu_panel

        async def close_menu_panel_async() -> None:
            try:
                await page.close_end_drawer()
            except Exception:
                pass

        async def open_menu_panel_async() -> None:
            if update_state["running"]:
                return
            search_mode_group.value = search_mode_state["value"]
            page.update()
            try:
                await page.show_end_drawer()
            except Exception as ex:
                append_log(f"[ERROR] 메뉴 패널 열기 실패: {ex}")

        async def run_manual_update_from_panel_async() -> None:
            await close_menu_panel_async()
            await do_update_async()

        def on_manual_update_click(e=None) -> None:
            page.run_task(run_manual_update_from_panel_async)

        btn_manual_update.on_click = on_manual_update_click

        def close_db_update_dialog(e=None) -> None:
            if db_update_dialog.open:
                page.pop_dialog()

        def on_db_update_confirm(e=None) -> None:
            close_db_update_dialog()
            page.run_task(do_update_async)

        def open_db_update_dialog(local_date_value: str | None, remote_date_value: str) -> None:
            local_label = local_date_value or "없음"
            db_update_dialog.title = ft.Text("DB 업데이트")
            db_update_dialog.content = ft.Column(
                [
                    ft.Text("DB 업데이트가 있습니다. 업데이트 하시겠습니까?"),
                    ft.Text(f"로컬 DB 날짜: {local_label}", size=12, color=COLORS.GREY_400),
                    ft.Text(f"GitHub DB 날짜: {remote_date_value}", size=12, color=COLORS.GREY_400),
                ],
                tight=True,
                spacing=6,
            )
            db_update_dialog.actions = [
                ft.TextButton("나중에", on_click=close_db_update_dialog),
                ft.ElevatedButton("업데이트", on_click=on_db_update_confirm),
            ]
            db_update_dialog.actions_alignment = ft.MainAxisAlignment.END
            if db_update_dialog.open:
                return
            page.show_dialog(db_update_dialog)

        async def check_remote_db_update_async() -> None:
            if update_prompt_state["shown"]:
                return

            dbp = (tf_db.value or "").strip()
            if not dbp:
                return

            def _resolve_dates(path_value: str) -> tuple[str | None, str | None]:
                local_date_value = local_db_date(path_value)
                info = get_latest_release_db_info()
                if not info:
                    return local_date_value, None
                remote_date_value = format_iso_date(
                    info.get("asset_updated_at")
                    or info.get("published_at")
                    or info.get("created_at")
                )
                return local_date_value, remote_date_value

            local_date_value, remote_date_value = await asyncio.to_thread(_resolve_dates, dbp)
            if not remote_date_value:
                return
            if local_date_value == remote_date_value:
                return

            update_prompt_state["shown"] = True
            open_db_update_dialog(local_date_value, remote_date_value)

        def on_menu_click(e=None) -> None:
            if not is_mobile_layout():
                return
            page.run_task(open_menu_panel_async)

        btn_menu.on_click = on_menu_click

        # --- first-run: 초기 렌더 속도를 위해 DB open/init은 지연 ---
        if not db_exists(tf_db.value):
            if not tf_db.value or not tf_db.value.strip():
                append_log("[WARN] DB 경로가 비어있습니다. 상단 DB 경로를 지정해주세요.")
            else:
                append_log("[INFO] DB 파일이 없습니다.")
                append_log("[INFO] 메뉴의 'DB 수동갱신'으로 GitHub Releases 최신 DB를 내려받습니다.")

        # --- Layout ---
        layout_state = {"mobile": None, "size": (0, 0)}

        def image_toggle_label() -> str:
            return "이미지 펼치기" if image_panel_state["collapsed"] else "이미지 접기"

        def image_section_header_mobile() -> ft.Control:
            return ft.Row(
                [
                    ft.Text("이미지"),
                    ft.TextButton(image_toggle_label(), on_click=toggle_image_panel),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )

        def toggle_image_panel(e=None) -> None:
            image_panel_state["collapsed"] = not image_panel_state["collapsed"]
            build_layout(force=True)
            page.update()

        def is_android_tablet() -> bool:
            platform = getattr(page, "platform", None)
            is_android = False
            if platform is not None:
                if hasattr(ft, "PagePlatform") and platform == ft.PagePlatform.ANDROID:
                    is_android = True
                elif isinstance(platform, str) and platform.lower() == "android":
                    is_android = True

            user_agent = (getattr(page, "client_user_agent", "") or "").lower()
            ua_android = "android" in user_agent
            ua_mobile = "mobile" in user_agent
            ua_tablet_hint = "tablet" in user_agent or (ua_android and not ua_mobile)

            width, height = get_view_size()
            min_dim = min([dim for dim in (width, height) if dim]) if width or height else 0
            size_tablet_hint = min_dim >= 600

            return (is_android or ua_android) and (ua_tablet_hint or size_tablet_hint)

        def is_mobile_layout() -> bool:
            width, _ = get_view_size()
            if width <= 0:
                # 초기 사이즈가 아직 확정되지 않은 모바일 환경은 플랫폼 정보로 우선 판정.
                return is_mobile_platform() and not is_android_tablet()
            return bool(width) and width < 900 and not is_android_tablet()

        def mobile_scaled_height(ratio: float, min_px: int, max_px: int) -> int:
            _, height = get_view_size()
            if height <= 0:
                height = 844.0  # iPhone 기준 fallback
            scaled = int(height * ratio)
            return max(min_px, min(max_px, scaled))

        def build_layout(force: bool = False) -> None:
            mobile = is_mobile_layout()
            width, height = get_view_size()
            size_key = (int(width or 0), int(height or 0))
            if (
                not force
                and layout_state["mobile"] == mobile
                and layout_state["size"] == size_key
            ):
                return
            layout_state["mobile"] = mobile
            layout_state["size"] = size_key

            page.controls.clear()

            if mobile:
                lv.expand = True
                lv.scroll = ft.ScrollMode.AUTO
                detail_lv.expand = False
                detail_lv.scroll = None
                list_height = mobile_scaled_height(0.30, 190, 360)
                image_height = mobile_scaled_height(0.45, 240, 560)

                top_row = ft.Row(
                    [
                        tf_search,
                        btn_menu,
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )

                mobile_root = ft.Column(
                    [
                        top_row,
                        update_status,
                        ft.Divider(height=1),
                        ft.Text("목록"),
                        ft.Container(
                            content=lv,
                            height=list_height,
                            padding=10,
                            border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
                            border_radius=10,
                        ),
                        image_section_header_mobile(),
                        ft.Text("이미지를 접었습니다.", color=COLORS.GREY_400)
                        if image_panel_state["collapsed"]
                        else ft.Container(
                            content=img_container,
                            height=image_height,
                            border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
                            border_radius=10,
                        ),
                        ft.Text("효과"),
                        ft.Container(
                            content=detail_lv,
                            padding=10,
                            border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
                            border_radius=10,
                        ),
                    ],
                    expand=True,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                )

                page.add(
                    ft.SafeArea(
                        content=ft.Container(
                            content=mobile_root,
                            padding=ft.padding.only(
                                left=10,
                                right=10,
                                top=6,
                                bottom=MOBILE_SAFE_BOTTOM_PADDING,
                            ),
                        ),
                        expand=True,
                    )
                )
                return

            lv.expand = True
            lv.scroll = ft.ScrollMode.AUTO
            detail_lv.expand = True
            detail_lv.scroll = ft.ScrollMode.AUTO

            top = ft.Row(
                [
                    tf_db,
                    update_progress,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
            search_row = ft.Row([tf_search], vertical_alignment=ft.CrossAxisAlignment.CENTER)

            left = ft.Column(
                [
                    ft.Container(ft.Text("목록"), padding=ft.padding.only(left=10, top=4)),
                    ft.Container(lv, expand=True, padding=10),
                ],
                expand=True,
                spacing=0,
            )

            middle = ft.Column(
                [
                    ft.Container(ft.Text("이미지"), padding=ft.padding.only(left=10, top=4)),
                    img_container,
                ],
                expand=True,
                spacing=0,
            )

            right = ft.Column(
                [
                    ft.Container(ft.Text("효과"), padding=ft.padding.only(left=10, top=4)),
                    ft.Container(detail_lv, expand=True, padding=10),
                ],
                expand=True,
                spacing=0,
            )

            body_controls: list[ft.Control] = [ft.Container(left, expand=3)]
            body_controls.extend(
                [
                    ft.VerticalDivider(width=1),
                    ft.Container(middle, expand=6),
                    ft.VerticalDivider(width=1),
                    ft.Container(right, expand=4),
                ]
            )
            body = ft.Row(body_controls, expand=True)

            desktop_root = ft.Column(
                [
                    top,
                    search_row,
                    update_status,
                    ft.Divider(height=1),
                    body,
                ],
                expand=True,
                spacing=8,
            )

            page.add(
                ft.SafeArea(
                    content=ft.Container(
                        content=desktop_root,
                        padding=ft.padding.only(left=10, right=10, top=6, bottom=10),
                    ),
                    expand=True,
                )
            )

        def on_resize(e) -> None:
            build_layout()

        page.on_resize = on_resize
        clear_selection()
        render_result_list()
        build_layout()
        page.run_task(run_startup_checks_async)
        if not is_mobile_layout():
            page.run_task(check_remote_db_update_async)
        if needs_db_update():
            show_toast(DB_MISSING_TOAST, persist=True)

    ft.app(target=main)
