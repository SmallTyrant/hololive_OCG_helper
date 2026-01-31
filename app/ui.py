# app/ui.py
from __future__ import annotations

import os
import threading
from pathlib import Path

import flet as ft

from app.services.db import (
    open_db,
    query_suggest,
    load_card_detail,
    get_print_brief,
    db_exists,
)
from app.services.pipeline import run_update_and_refine
from app.services.images import local_image_path, download_image


def launch_app(db_path: str):
    # UI 스레드용 DB 연결: DB 없으면 일단 None으로 시작
    conn_ui = None

    project_root = Path(__file__).resolve().parents[1]  # .../app
    project_root = project_root.parent                  # project root

    def main(page: ft.Page):
        nonlocal conn_ui

        page.title = "hololive OCG helper"
        page.window_width = 1280
        page.window_height = 820

        # --- Controls ---
        tf_db = ft.TextField(label="DB", value=db_path, expand=True)
        tf_search = ft.TextField(
            label="카드번호 / 이름 / 태그 검색",
            hint_text="예: 카드번호 / 이름 / 태그",
            expand=True,
        )

        btn_update = ft.ElevatedButton("DB 생성/업데이트+정제")  # DB 없을 때도 이 버튼으로 생성
        pb = ft.ProgressBar(visible=False, width=180)

        # --- Left: results ---
        lv = ft.ListView(expand=True, spacing=2, padding=0)

        # --- Image area (중요: ft.Image()를 빈 생성자로 만들지 않음) ---
        def build_image_widget(image_path: Path | None):
            # 이미지 파일이 존재할 때만 ft.Image(src=...) 생성
            if image_path and image_path.exists():
                return ft.Image(
                    src=str(image_path),
                    fit=ft.ImageFit.CONTAIN,
                    expand=True,
                )
            # 이미지 없을 때 플레이스홀더
            return ft.Container(
                content=ft.Text("이미지 없음", color=ft.colors.GREY_400),
                alignment=ft.alignment.center,
                expand=True,
                border=ft.border.all(1, ft.colors.with_opacity(0.15, ft.colors.WHITE)),
            )

        img_container = ft.Container(
            content=build_image_widget(None),
            expand=True,
            padding=10,
            bgcolor=None,
            border=ft.border.all(1, ft.colors.with_opacity(0.15, ft.colors.WHITE)),
        )

        btn_img_dl = ft.ElevatedButton("현재 카드 이미지 다운로드")
        btn_img_dl.disabled = True  # 카드 선택 후 활성화

        # --- Right: detail ---
        detail_tf = ft.TextField(
            label="본문(raw_text)",
            multiline=True,
            read_only=True,
            expand=True,
        )

        # --- Bottom: log ---
        log_tf = ft.TextField(label="로그", multiline=True, read_only=True, expand=True)

        # currently selected
        selected_print_id = {"id": None}
        selected_image_url = {"url": ""}
        selected_card_number = {"no": ""}

        def append_log(s: str):
            log_tf.value = (log_tf.value or "") + s + "\n"
            page.update()

        def ensure_conn():
            nonlocal conn_ui
            if conn_ui is None:
                conn_ui = open_db(tf_db.value)

        def set_image_for_card(card_number: str):
            p = local_image_path(project_root, card_number)
            img_container.content = build_image_widget(p if p.exists() else None)
            page.update()

        def clear_image():
            img_container.content = build_image_widget(None)
            page.update()

        def show_detail(pid: int):
            selected_print_id["id"] = pid

            try:
                ensure_conn()
                brief = get_print_brief(conn_ui, pid) or {}
                selected_image_url["url"] = (brief.get("image_url") or "").strip()
                selected_card_number["no"] = (brief.get("card_number") or "").strip()

                # 이미지 패널 갱신
                if selected_card_number["no"]:
                    set_image_for_card(selected_card_number["no"])
                else:
                    clear_image()

                # 본문 갱신
                card = load_card_detail(conn_ui, pid)
                if not card:
                    detail_tf.value = "(본문 없음)"
                else:
                    detail_tf.value = card.get("raw_text", "") or "(본문 없음)"

                # 이미지 다운로드 버튼 활성화 조건
                btn_img_dl.disabled = not (selected_card_number["no"] and selected_image_url["url"])

            except Exception as ex:
                detail_tf.value = f"[ERROR] 상세 로드 실패: {ex}"
                btn_img_dl.disabled = True
                clear_image()

            page.update()

        def refresh_list():
            q = (tf_search.value or "").strip()
            lv.controls.clear()

            if not q:
                page.update()
                return

            if conn_ui is None and not db_exists(tf_db.value):
                append_log("[INFO] DB가 없어서 검색 불가. 'DB 생성/업데이트+정제'를 먼저 실행하세요.")
                page.update()
                return

            try:
                ensure_conn()
                rows = query_suggest(conn_ui, q, limit=80)
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

        # --- image download for selected card ---
        def do_download_current_image():
            try:
                btn_img_dl.disabled = True
                page.update()

                cn = selected_card_number["no"]
                url = selected_image_url["url"]
                if not cn or not url:
                    append_log("[WARN] 카드/이미지 URL이 없습니다.")
                    return

                dest = local_image_path(project_root, cn)
                append_log(f"[IMG] downloading: {cn} -> {dest.name}")
                download_image(url, dest)
                append_log("[IMG] done")

                # 화면 갱신
                set_image_for_card(cn)

            except Exception as ex:
                append_log(f"[IMG][ERROR] {ex}")
            finally:
                # 선택 상태에 따라 다시 활성화
                btn_img_dl.disabled = not (selected_card_number["no"] and selected_image_url["url"])
                page.update()

        def on_img_dl_click(e):
            threading.Thread(target=do_download_current_image, daemon=True).start()

        btn_img_dl.on_click = on_img_dl_click

        # --- Update pipeline (background thread) ---
        def do_update():
            nonlocal conn_ui
            try:
                pb.visible = True
                btn_update.disabled = True
                tf_search.disabled = True
                btn_img_dl.disabled = True
                page.update()

                dbp = tf_db.value.strip()
                append_log("[START] update + refine")

                # subprocess로 크롤링/정제
                for line in run_update_and_refine(dbp, delay=0.6):
                    append_log(line)

                append_log("[DONE] update + refine")

                # UI 스레드용 DB 재연결
                try:
                    if conn_ui:
                        conn_ui.close()
                except Exception:
                    pass
                conn_ui = open_db(dbp)

                # 검색 결과 재갱신
                refresh_list()

            except Exception as ex:
                append_log(f"[ERROR] 업데이트/정제 실패: {ex}")

            finally:
                pb.visible = False
                btn_update.disabled = False
                tf_search.disabled = False
                btn_img_dl.disabled = not (selected_card_number["no"] and selected_image_url["url"])
                page.update()

        def on_update_click(e):
            threading.Thread(target=do_update, daemon=True).start()

        btn_update.on_click = on_update_click

        # --- first-run: DB 없으면 안내 로그만 찍고 앱은 뜨게 ---
        if not db_exists(tf_db.value):
            append_log("[INFO] DB 파일이 없습니다.")
            append_log("[INFO] 상단 'DB 생성/업데이트+정제'를 누르면 DB를 생성(크롤링+정제)합니다.")
        else:
            # DB 있으면 즉시 연결
            try:
                ensure_conn()
            except Exception as ex:
                append_log(f"[ERROR] DB open failed: {ex}")

        # --- Layout ---
        example_card = ft.Container(
            content=ft.Column(
                [
                    ft.Text("UI 예시", weight=ft.FontWeight.BOLD),
                    ft.Text("1) 검색창에 카드번호/이름/태그를 입력하면"),
                    ft.Text("2) 좌측에서 결과를 선택하고"),
                    ft.Text("3) 가운데에서 이미지, 우측에서 본문을 확인합니다."),
                    ft.Text("4) 하단 로그에서 처리 상태를 볼 수 있습니다."),
                ],
                spacing=2,
            ),
            padding=10,
            border=ft.border.all(1, ft.colors.with_opacity(0.15, ft.colors.WHITE)),
            bgcolor=ft.colors.with_opacity(0.03, ft.colors.WHITE),
        )

        top = ft.Row([tf_db, btn_update, pb], vertical_alignment=ft.CrossAxisAlignment.CENTER)
        search_row = ft.Row([tf_search], vertical_alignment=ft.CrossAxisAlignment.CENTER)

        left = ft.Column(
            [
                ft.Container(ft.Text("결과"), padding=ft.padding.only(left=10, top=4)),
                ft.Container(lv, expand=True, padding=10),
            ],
            expand=True,
            spacing=0,
        )

        middle = ft.Column(
            [
                ft.Container(ft.Text("이미지"), padding=ft.padding.only(left=10, top=4)),
                img_container,
                ft.Container(btn_img_dl, padding=10),
            ],
            expand=True,
            spacing=0,
        )

        right = ft.Column(
            [
                ft.Container(detail_tf, expand=True, padding=10),
            ],
            expand=True,
            spacing=0,
        )

        body = ft.Row(
            [
                ft.Container(left, expand=3),
                ft.VerticalDivider(width=1),
                ft.Container(middle, expand=4),
                ft.VerticalDivider(width=1),
                ft.Container(right, expand=5),
            ],
            expand=True,
        )

        bottom = ft.Container(log_tf, padding=10, height=200)

        page.add(
            ft.Column(
                [
                    example_card,
                    top,
                    search_row,
                    ft.Divider(height=1),
                    body,
                    ft.Divider(height=1),
                    bottom,
                ],
                expand=True,
                spacing=8,
            )
        )

    ft.app(target=main)
