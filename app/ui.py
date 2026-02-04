# app/ui.py
from __future__ import annotations

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

def icon_paths(project_root: Path, data_root: Path | None = None) -> tuple[Path, Path]:
    d = icon_dir(project_root)
    png_path = d / "app_icon.png"
    ico_root = data_root if data_root is not None else d
    return ico_root / "app_icon.ico", png_path


def launch_app(db_path: str) -> None:
    project_root = get_project_root()
    data_root = get_default_data_root("hOCG_helper")

    def main(page: ft.Page) -> None:
        thread_local = threading.local()
        conn_epoch = {"value": 0}
        db_health_cache = {"path": None, "value": None, "checked_at": 0.0}
        DB_HEALTH_CACHE_TTL = 2.0

        page.title = "hOCG_helper"
        page.window_width = 1280
        page.window_height = 820

        # --- Controls ---
        tf_db = ft.TextField(label="DB", value=db_path, expand=True)
        tf_search = ft.TextField(label="카드번호 / 이름 / 태그 검색", expand=True)

        btn_update = ft.ElevatedButton("DB갱신")  # DB 없을 때도 이 버튼으로 생성
        # Progress bar removed (user requested no ETA/loader in UI)

        # --- Left: results ---
        lv = ft.ListView(expand=True, spacing=2, padding=0)

        # --- Image area (중요: ft.Image()를 빈 생성자로 만들지 않음) ---
        def build_image_widget(image_path: Path | None, image_url: str | None = None) -> ft.Control:
            # 이미지 파일이 존재할 때만 ft.Image(src=...) 생성
            if image_path and image_path.exists():
                return ft.Image(
                    src=str(image_path),
                    fit=IMAGE_FIT_CONTAIN,
                    expand=True,
                )
            # 로컬이 없으면 URL로 표시
            if image_url:
                return ft.Image(
                    src=image_url,
                    fit=IMAGE_FIT_CONTAIN,
                    expand=True,
                )
            # 이미지 없을 때 플레이스홀더
            return ft.Container(
                content=ft.Text("이미지 없음", color=COLORS.GREY_400),
                alignment=ALIGN_CENTER,
                expand=True,
                border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
            )

        img_container = ft.Container(
            content=build_image_widget(None),
            expand=True,
            padding=10,
            bgcolor=None,
            border=ft.border.all(1, with_opacity(0.15, COLORS.WHITE)),
        )

        # --- Right: detail ---
        detail_lv = ft.ListView(expand=True, spacing=4, padding=0, auto_scroll=False)
        # currently selected
        selected_print_id = {"id": None}
        selected_card_number = {"no": ""}
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
            toast_host.update()

            if duration_ms is not None and duration_ms > 0:
                def _after():
                    if toast_state["seq"] != seq:
                        return
                    if persist:
                        return
                    toast_host.visible = False
                    toast_host.update()
                    if restore_missing_after and needs_db_update():
                        show_toast(DB_MISSING_TOAST, persist=True)

                threading.Timer(duration_ms / 1000.0, _after).start()

        def setup_window_icon() -> None:
            ico_path, png_path = icon_paths(project_root, data_root)

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

        def set_image_for_card(card_number: str, image_url: str | None = None) -> None:
            p = local_image_path(data_root, card_number)
            img_container.content = build_image_widget(p if p.exists() else None, image_url)
            page.update()

        def clear_image() -> None:
            img_container.content = build_image_widget(None)
            page.update()

        def ensure_image_download(card_number: str, image_url: str) -> None:
            if not card_number or not image_url:
                return
            dest = local_image_path(data_root, card_number)
            if dest.exists():
                return
            with download_lock:
                if card_number in downloading:
                    return
                downloading.add(card_number)

            def worker() -> None:
                try:
                    append_log(f"[IMG] downloading: {card_number} -> {dest.name}")
                    download_image(image_url, dest)
                    append_log("[IMG] done")
                    if selected_card_number["no"] == card_number:
                        set_image_for_card(card_number, image_url)
                except Exception as ex:
                    append_log(f"[IMG][ERROR] {ex}")
                finally:
                    with download_lock:
                        downloading.discard(card_number)

            threading.Thread(target=worker, daemon=True).start()

        def build_section_chip(text: str) -> ft.Control:
            return ft.Container(
                content=ft.Text(text, weight=ft.FontWeight.BOLD, size=12),
                bgcolor=with_opacity(0.18, COLORS.BLUE_GREY_700),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=12,
            )

        def build_detail_line(line: str) -> ft.Control | None:
            if line in SECTION_LABELS:
                return build_section_chip(line)

            for label in SECTION_LABELS:
                if line.startswith(label + " "):
                    rest = line[len(label):]
                    if label == "カードタイプ" and ("ホロメン" in rest or "홀로멤" in rest):
                        return None
                    if label == "HP":
                        rest_txt = rest.strip()
                        if "200" in rest_txt:
                            hp_text = ft.Text(
                                spans=[
                                    ft.TextSpan(rest_txt.replace("200", "")),
                                    ft.TextSpan(
                                        "200",
                                        style=ft.TextStyle(
                                            weight=ft.FontWeight.BOLD,
                                            color=getattr(COLORS, "RED_400", COLORS.RED),
                                        ),
                                    ),
                                ]
                            )
                            return ft.Row(
                                [build_section_chip(label), hp_text],
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            )
                        return ft.Row(
                            [build_section_chip(label), ft.Text(rest_txt)],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        )
                    if label == "Bloomレベル":
                        return ft.Row(
                            [build_section_chip(label), ft.Text(rest.strip())],
                            spacing=6,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        )
                    return ft.Text(
                        spans=[
                            ft.TextSpan(label, style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                            ft.TextSpan(rest),
                        ]
                    )
            return ft.Text(line)

        def append_detail_lines(text: str, apply_jp_filters: bool) -> None:
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line:
                    i += 1
                    continue
                if apply_jp_filters:
                    if line == "Bloomレベル" and i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line:
                            merged = f"Bloomレベル {next_line}"
                            item = build_detail_line(merged)
                            if item:
                                detail_lv.controls.append(item)
                            i += 2
                            continue
                    if line == "色" or line.startswith("色 "):
                        i += 1
                        continue
                    if line == "バトンタッチ" or line.startswith("バトンタッチ "):
                        i += 1
                        continue
                    item = build_detail_line(line)
                    if item:
                        detail_lv.controls.append(item)
                else:
                    detail_lv.controls.append(ft.Text(line))
                i += 1

        def set_detail_text(ja_text: str | None, ko_text: str | None) -> None:
            detail_lv.controls.clear()
            ja = (ja_text or "").strip()
            ko = (ko_text or "").strip()
            has_any = False

            if ko:
                detail_lv.controls.append(build_section_chip("한국어"))
                append_detail_lines(ko, apply_jp_filters=False)
                has_any = True

            if ja:
                if ko:
                    detail_lv.controls.append(ft.Divider(height=8))
                    detail_lv.controls.append(build_section_chip("日本語"))
                append_detail_lines(ja, apply_jp_filters=True)
                has_any = True

            if not has_any:
                detail_lv.controls.append(ft.Text("(본문 없음)"))

            page.update()

        def show_detail(pid: int) -> None:
            selected_print_id["id"] = pid

            try:
                conn = get_conn()
                brief = get_print_brief(conn, pid) or {}
                selected_card_number["no"] = (brief.get("card_number") or "").strip()
                image_url = resolve_url((brief.get("image_url") or "").strip())

                # 이미지 패널 갱신
                if selected_card_number["no"]:
                    set_image_for_card(selected_card_number["no"], image_url)
                else:
                    clear_image()

                # 이미지 자동 다운로드 (없으면)
                ensure_image_download(selected_card_number["no"], image_url)

                # 본문 갱신
                card = load_card_detail(conn, pid)
                set_detail_text(
                    card.get("raw_text", "") if card else None,
                    card.get("ko_text", "") if card else None,
                )

            except Exception as ex:
                set_detail_text(f"[ERROR] 상세 로드 실패: {ex}", None)
                clear_image()

            page.update()

        def refresh_list() -> None:
            q = (tf_search.value or "").strip()
            lv.controls.clear()

            if not q:
                page.update()
                return

            if needs_db_update():
                append_log("[INFO] DB가 없거나 손상되어 검색 불가. 'DB갱신'을 먼저 실행하세요.")
                show_toast(DB_MISSING_TOAST, persist=True)
                page.update()
                return

            try:
                conn = get_conn()
                rows = query_suggest(conn, q, limit=80)
                for r in rows:
                    title = f"{r.get('card_number','')} | {r.get('name_ja','')}"
                    pid = r["print_id"]
                    lv.controls.append(
                        ft.ListTile(
                            title=ft.Text(title),
                            on_click=lambda e, _pid=pid: show_detail(_pid),
                        )
                    )
            except Exception as ex:
                append_log(f"[ERROR] 검색 실패: {ex}")

            page.update()

        def on_search_change(e) -> None:
            refresh_list()

        tf_search.on_change = on_search_change

        def on_db_change(e) -> None:
            invalidate_db_health_cache()

        tf_db.on_change = on_db_change

        # --- Update pipeline (background thread) ---
        def do_update() -> None:
            try:
                show_toast(DB_UPDATING_TOAST, persist=True)
                btn_update.disabled = True
                tf_search.disabled = True
                page.update()

                dbp = tf_db.value.strip()
                append_log("[START] DB 갱신")

                # subprocess로 크롤링/정제
                done_seen = False
                for line in run_update_and_refine(dbp):
                    append_log(line)
                    if line.strip().startswith("[DONE]"):
                        done_seen = True
                        show_toast(
                            DB_UPDATED_TOAST,
                            duration_ms=3000,
                            restore_missing_after=True,
                        )

                append_log("[DONE] DB 갱신")
                if not done_seen:
                    done_seen = True
                    show_toast(
                        DB_UPDATED_TOAST,
                        duration_ms=3000,
                        restore_missing_after=True,
                    )

                # 모든 스레드의 DB 연결 갱신 유도
                conn_epoch["value"] += 1
                close_thread_conn()
                invalidate_db_health_cache()

                # 검색 결과 재갱신
                refresh_list()

            except Exception as ex:
                append_log(f"[ERROR] DB 갱신 실패: {ex}")
                if needs_db_update():
                    show_toast(DB_MISSING_TOAST, persist=True)

            finally:
                btn_update.disabled = False
                tf_search.disabled = False
                page.update()

        def on_update_click(e) -> None:
            threading.Thread(target=do_update, daemon=True).start()

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
            # DB 있으면 즉시 연결
            try:
                get_conn()
            except Exception as ex:
                append_log(f"[ERROR] DB open failed: {ex}")

        if needs_db_update():
            show_toast(DB_MISSING_TOAST, persist=True)

        # --- Layout ---
        layout_state = {"mobile": None}

        def is_mobile_layout() -> bool:
            width = page.window_width or page.width or 0
            return bool(width) and width < 900

        def build_layout() -> None:
            mobile = is_mobile_layout()
            if layout_state["mobile"] == mobile:
                return
            layout_state["mobile"] = mobile

            page.controls.clear()

            if mobile:
                top_row = ft.Row(
                    [tf_search, btn_update],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                )
                db_row = ft.Row([tf_db], vertical_alignment=ft.CrossAxisAlignment.CENTER)
                list_section = ft.Column(
                    [
                        ft.Container(ft.Text("목록"), padding=ft.padding.only(left=10, top=4)),
                        ft.Container(lv, height=240, padding=10),
                    ],
                    spacing=0,
                )
                image_section = ft.Column(
                    [
                        ft.Container(ft.Text("이미지"), padding=ft.padding.only(left=10, top=4)),
                        ft.Container(img_container, height=320),
                    ],
                    spacing=0,
                )
                effect_section = ft.Column(
                    [
                        ft.Container(ft.Text("효과"), padding=ft.padding.only(left=10, top=4)),
                        ft.Container(detail_lv, height=320, padding=10),
                    ],
                    spacing=0,
                )
                page.add(
                    ft.Column(
                        [
                            top_row,
                            ft.Divider(height=1),
                            list_section,   # 카드번호/검색 아래에 목록
                            image_section,  # 이미지 중간
                            effect_section, # 본문 하위
                            db_row,
                        ],
                        expand=True,
                        spacing=8,
                        scroll=ft.ScrollMode.AUTO,
                    )
                )
                return

            top = ft.Row([tf_db, btn_update], vertical_alignment=ft.CrossAxisAlignment.CENTER)
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

            page.add(
                ft.Column(
                    [
                        top,
                        search_row,
                        ft.Divider(height=1),
                        body,
                    ],
                    expand=True,
                    spacing=8,
                )
            )

        def on_resize(e) -> None:
            build_layout()

        page.on_resize = on_resize
        build_layout()

    ft.app(target=main)
