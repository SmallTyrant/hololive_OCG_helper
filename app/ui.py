# app/ui.py
from __future__ import annotations

import asyncio
import sqlite3
import threading
import sys
import time
from pathlib import Path

import flet as ft

from app.services.db import (
    open_db,
    query_suggest,
    load_card_detail,
    get_print_brief,
    db_exists,
    ensure_db,
)
from app.services.pipeline import run_update_and_refine
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

DB_MISSING_TOAST = "DB파일이 존재하지 않습니다. DB갱신을 해주세요"
DB_UPDATING_TOAST = "갱신중..."
DB_UPDATED_TOAST = "갱신완료"
APP_NAME = "hOCG_H"

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

        if not is_mobile_platform():
            page.window_width = 1280
            page.window_height = 820

        # --- Controls ---
        tf_db = ft.TextField(label="DB", value=db_path, expand=True)
        tf_search = ft.TextField(label="카드번호 / 이름 / 태그 검색", expand=True)
        btn_update = ft.ElevatedButton("DB갱신", icon=ICONS.SYNC)
        update_progress = ft.ProgressRing(width=18, height=18, stroke_width=2, visible=False)
        update_status = ft.Text("", size=12, color=COLORS.RED_300, visible=False)

        # --- Results / Detail ---
        lv = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        detail_lv = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        detail_texts = {"ko": "", "ja": ""}

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
        update_state = {"running": False}
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

        for issue in run_startup_checks(tf_db.value, data_root):
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

        def append_detail_lines(text: str, apply_jp_filters: bool) -> None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for line in lines:
                if apply_jp_filters:
                    if line == "色" or line.startswith("色 "):
                        continue
                    if line == "バトンタッチ" or line.startswith("バトンタッチ "):
                        continue
                    detail_lv.controls.append(build_detail_line(line))
                else:
                    detail_lv.controls.append(ft.Text(line))

        def render_detail() -> None:
            detail_lv.controls.clear()
            ja = (detail_texts["ja"] or "").strip()
            ko = (detail_texts["ko"] or "").strip()
            has_any = False

            if ko:
                detail_lv.controls.append(build_section_chip("한국어"))
                append_detail_lines(ko, apply_jp_filters=False)
                has_any = True

            if ja:
                if has_any:
                    detail_lv.controls.append(ft.Divider(height=12))
                detail_lv.controls.append(build_section_chip("日本語"))
                append_detail_lines(ja, apply_jp_filters=True)
                has_any = True

            if not has_any:
                detail_lv.controls.append(ft.Text("(본문 없음)"))

            page.update()

        def set_detail_text(ja_text: str | None, ko_text: str | None) -> None:
            detail_texts["ja"] = (ja_text or "")
            detail_texts["ko"] = (ko_text or "")
            render_detail()

        def clear_selection() -> None:
            selected_print_id["id"] = None
            selected_card_number["no"] = ""
            selected_image_url["url"] = ""
            set_detail_text("", "")
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
                title = f"{row.get('card_number', '')} | {row.get('name_ja', '')}"
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
                set_detail_text(
                    card.get("raw_text", "") if card else None,
                    card.get("ko_text", "") if card else None,
                )

            except Exception as ex:
                set_detail_text(f"[ERROR] 상세 로드 실패: {ex}", None)
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
                append_log("[INFO] DB가 없거나 손상되어 검색 불가. 'DB갱신'을 먼저 실행하세요.")
                show_toast(DB_MISSING_TOAST, persist=True)
                render_result_list()
                clear_selection()
                page.update()
                return

            try:
                conn = get_conn()
                results_state["rows"] = query_suggest(conn, query, limit=80)
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

        def on_db_change(e) -> None:
            invalidate_db_health_cache()

        tf_db.on_change = on_db_change

        def set_update_running(running: bool) -> None:
            update_state["running"] = running
            btn_update.disabled = running
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

        def on_update_click(e) -> None:
            page.run_task(do_update_async)

        btn_update.on_click = on_update_click

        # --- first-run: DB 없으면 안내 로그만 찍고 앱은 뜨게 ---
        if not db_exists(tf_db.value):
            if not tf_db.value or not tf_db.value.strip():
                append_log("[WARN] DB 경로가 비어있습니다. 상단 DB 경로를 지정해주세요.")
            else:
                created = ensure_db(tf_db.value)
                if created:
                    append_log("[INFO] DB 파일이 없어 빈 DB를 생성했습니다.")
                else:
                    append_log("[INFO] DB 파일이 없습니다.")
                append_log("[INFO] 상단 'DB갱신'을 누르면 DB를 생성(크롤링+정제)합니다.")
        else:
            try:
                get_conn()
            except Exception as ex:
                append_log(f"[ERROR] DB open failed: {ex}")

        # --- Layout ---
        layout_state = {"mobile": None}

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

            width = page.window_width or page.width or 0
            height = page.window_height or page.height or 0
            min_dim = min([dim for dim in (width, height) if dim]) if width or height else 0
            size_tablet_hint = min_dim >= 600

            return (is_android or ua_android) and (ua_tablet_hint or size_tablet_hint)

        def is_mobile_layout() -> bool:
            width = page.window_width or page.width or 0
            return bool(width) and width < 900 and not is_android_tablet()

        def build_layout() -> None:
            mobile = is_mobile_layout()
            if layout_state["mobile"] == mobile:
                return
            layout_state["mobile"] = mobile

            page.controls.clear()

            if mobile:
                btn_update.width = 100
                lv.expand = True
                lv.scroll = ft.ScrollMode.AUTO
                detail_lv.expand = False
                detail_lv.scroll = None

                top_row = ft.Row(
                    [
                        tf_search,
                        ft.Row([update_progress, btn_update], tight=True, spacing=8),
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
                            height=260,
                            padding=10,
                            border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
                            border_radius=10,
                        ),
                        ft.Text("이미지"),
                        ft.Container(
                            content=img_container,
                            height=460,
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
                            padding=ft.padding.only(left=10, right=10, top=6, bottom=10),
                        ),
                        expand=True,
                    )
                )
                return

            btn_update.width = None
            lv.expand = True
            lv.scroll = ft.ScrollMode.AUTO
            detail_lv.expand = True
            detail_lv.scroll = ft.ScrollMode.AUTO

            top = ft.Row(
                [
                    tf_db,
                    ft.Row([update_progress, btn_update], tight=True, spacing=8),
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

            body = ft.Row(
                [
                    ft.Container(left, expand=3),
                    ft.VerticalDivider(width=1),
                    ft.Container(middle, expand=6),
                    ft.VerticalDivider(width=1),
                    ft.Container(right, expand=4),
                ],
                expand=True,
            )

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
        if needs_db_update():
            show_toast(DB_MISSING_TOAST, persist=True)

    ft.app(target=main)
