# app/ui.py
from __future__ import annotations

import threading
from datetime import datetime, timedelta
from pathlib import Path

import flet as ft

from app.services.db import (
    open_db,
    query_suggest,
    load_card_detail,
    load_card_detail_ko,
    get_print_brief,
    db_exists,
    ensure_db,
)
from app.services.pipeline import run_update_and_refine
from app.paths import get_default_data_root, get_project_root
from app.services.images import local_image_path, download_image, resolve_url

COLORS = ft.Colors if hasattr(ft, "Colors") else ft.colors

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
    return d / "app_icon.ico", d / "app_icon.png"


def launch_app(db_path: str):
    project_root = get_project_root()
    data_root = get_default_data_root("hOCG_helper")

    def main(page: ft.Page):
        thread_local = threading.local()
        conn_epoch = {"value": 0}

        page.title = "hOCG_helper"
        page.window_width = 1280
        page.window_height = 820

        # --- Controls ---
        tf_db = ft.TextField(label="DB", value=db_path, expand=True)
        tf_search = ft.TextField(label="카드번호 / 이름 / 태그 검색", expand=True)

        btn_update = ft.ElevatedButton("DB 생성/업데이트+정제")  # DB 없을 때도 이 버튼으로 생성
        # Progress bar removed (user requested no ETA/loader in UI)

        # --- Left: results ---
        lv = ft.ListView(expand=True, spacing=2, padding=0)

        # --- Image area (중요: ft.Image()를 빈 생성자로 만들지 않음) ---
        def build_image_widget(image_path: Path | None, image_url: str | None = None):
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

        def append_log(s: str):
            print(s, flush=True)

        def setup_window_icon():
            ico_path, png_path = icon_paths(project_root)
            # Always try to use PNG from /app/app_icon.png first.
            if png_path.exists():
                try:
                    page.window.icon = str(png_path)
                    return
                except Exception:
                    pass

            # If PNG doesn't work on the current platform, fall back to ICO.
            if ico_path.exists():
                page.window.icon = str(ico_path)
                return

            # Last resort: generate ICO from PNG if PNG exists.
            if png_path.exists():
                try:
                    from PIL import Image

                    ico_path.parent.mkdir(parents=True, exist_ok=True)
                    img = Image.open(png_path)
                    if img.mode not in ("RGBA", "RGB"):
                        img = img.convert("RGBA")
                    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
                    img.save(ico_path, format="ICO", sizes=sizes)
                    page.window.icon = str(ico_path)
                except Exception as ex:
                    append_log(f"[WARN] 앱 아이콘 설정 실패: {ex}")

        setup_window_icon()

        def get_conn():
            path = tf_db.value
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

        def close_thread_conn():
            conn = getattr(thread_local, "conn", None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            thread_local.conn = None
            thread_local.epoch = -1
            thread_local.path = None

        def set_image_for_card(card_number: str, image_url: str | None = None):
            p = local_image_path(data_root, card_number)
            img_container.content = build_image_widget(p if p.exists() else None, image_url)
            page.update()

        def clear_image():
            img_container.content = build_image_widget(None)
            page.update()

        def ensure_image_download(card_number: str, image_url: str):
            if not card_number or not image_url:
                return
            dest = local_image_path(data_root, card_number)
            if dest.exists():
                return
            if card_number in downloading:
                return
            downloading.add(card_number)

            def worker():
                try:
                    append_log(f"[IMG] downloading: {card_number} -> {dest.name}")
                    download_image(image_url, dest)
                    append_log("[IMG] done")
                    set_image_for_card(card_number, image_url)
                except Exception as ex:
                    append_log(f"[IMG][ERROR] {ex}")
                finally:
                    downloading.discard(card_number)

            threading.Thread(target=worker, daemon=True).start()

        def build_section_chip(text: str):
            return ft.Container(
                content=ft.Text(text, weight=ft.FontWeight.BOLD, size=12),
                bgcolor=with_opacity(0.18, COLORS.BLUE_GREY_700),
                padding=ft.padding.symmetric(horizontal=8, vertical=3),
                border_radius=12,
            )

        def build_detail_line(line: str):
            section_labels = (
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
            if line in section_labels:
                return build_section_chip(line)

            for label in section_labels:
                if line.startswith(label + " "):
                    rest = line[len(label):]
                    return ft.Text(
                        spans=[
                            ft.TextSpan(label, style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                            ft.TextSpan(rest),
                        ]
                    )
            return ft.Text(line)

        def _append_plain_lines(lines: list[str]):
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                detail_lv.controls.append(ft.Text(line))

        def set_detail_text(text_ja: str | None, text_ko: str | None):
            detail_lv.controls.clear()
            if not text_ja and not text_ko:
                detail_lv.controls.append(ft.Text("(본문 없음)"))
            else:
                if text_ja:
                    detail_lv.controls.append(build_section_chip("日本語"))
                    lines = [ln.strip() for ln in text_ja.splitlines() if ln.strip()]
                    i = 0
                    while i < len(lines):
                        line = lines[i]
                        if line == "色":
                            i += 1
                            continue
                        if line.startswith("色 "):
                            i += 1
                            continue
                        line = line.strip()
                        if not line:
                            i += 1
                            continue
                        if line == "バトンタッチ" or line.startswith("バトンタッチ "):
                            i += 1
                            continue
                        detail_lv.controls.append(build_detail_line(line))
                        i += 1

                if text_ko:
                    detail_lv.controls.append(build_section_chip("한국어"))
                    ko_lines = [ln.strip() for ln in text_ko.splitlines() if ln.strip()]
                    _append_plain_lines(ko_lines)
            page.update()

        def show_detail(pid: int):
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
                ko = load_card_detail_ko(conn, pid)
                ko_text = None
                if ko:
                    ko_text = (ko.get("memo") or ko.get("effect_text") or "").strip()
                set_detail_text(card.get("raw_text", "") if card else None, ko_text)

            except Exception as ex:
                set_detail_text(None, f"[ERROR] 상세 로드 실패: {ex}")
                clear_image()

            page.update()

        def refresh_list():
            q = (tf_search.value or "").strip()
            lv.controls.clear()

            if not q:
                page.update()
                return

            if not db_exists(tf_db.value):
                append_log("[INFO] DB가 없어서 검색 불가. 'DB 생성/업데이트+정제'를 먼저 실행하세요.")
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

        def on_search_change(e):
            refresh_list()

        tf_search.on_change = on_search_change

        # --- Update pipeline (background thread) ---
        def do_update():
            try:
                btn_update.disabled = True
                tf_search.disabled = True
                page.update()

                dbp = tf_db.value.strip()
                append_log("[START] update + refine")

                # subprocess로 크롤링/정제
                for line in run_update_and_refine(dbp):
                    append_log(line)

                append_log("[DONE] update + refine")

                # 모든 스레드의 DB 연결 갱신 유도
                conn_epoch["value"] += 1
                close_thread_conn()

                # 검색 결과 재갱신
                refresh_list()

            except Exception as ex:
                append_log(f"[ERROR] 업데이트/정제 실패: {ex}")

            finally:
                btn_update.disabled = False
                tf_search.disabled = False
                page.update()

        def on_update_click(e):
            threading.Thread(target=do_update, daemon=True).start()

        btn_update.on_click = on_update_click

        # --- first-run: DB 없으면 안내 로그만 찍고 앱은 뜨게 ---
        if not db_exists(tf_db.value):
            created = ensure_db(tf_db.value)
            if created:
                append_log("[INFO] DB 파일이 없어 빈 DB를 생성했습니다.")
            else:
                append_log("[INFO] DB 파일이 없습니다.")
            append_log("[INFO] 상단 'DB 생성/업데이트+정제'를 누르면 DB를 생성(크롤링+정제)합니다.")
        else:
            # DB 있으면 즉시 연결
            try:
                get_conn()
            except Exception as ex:
                append_log(f"[ERROR] DB open failed: {ex}")

        # --- Layout ---
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

    ft.app(target=main)
