# app/ui.py
from __future__ import annotations

import os
import threading
from pathlib import Path

import flet as ft

import shutil

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

        page.title = "hOCG Tool (Tk) - Viewer + AutoUpdate + Images + Verify"
        page.window_width = 1230
        page.window_height = 820

        # --- Controls ---
        tf_db = ft.TextField(value=db_path, expand=True)
        tf_search = ft.TextField(value="", expand=True, height=36, hint_text="hBP04-002")

        btn_backup = ft.ElevatedButton("DB 백업")
        btn_restore = ft.ElevatedButton("DB 복원 + 자동검증")
        cb_missing_only = ft.Checkbox(label="이미지: 누락분만", value=True)

        btn_update = ft.ElevatedButton("자동 업데이트 + 이미지 + 자동검증")  # DB 없을 때도 이 버튼으로 생성
        pb = ft.ProgressBar(visible=False, width=180)

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

        # --- Right: detail ---
        detail_tf = ft.TextField(
            multiline=True,
            read_only=True,
            expand=True,
        )

        # --- Bottom: log ---
        log_tf = ft.TextField(
            multiline=True,
            read_only=True,
            expand=True,
            bgcolor=ft.colors.BLACK,
            text_style=ft.TextStyle(color=ft.colors.WHITE),
        )

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

            except Exception as ex:
                detail_tf.value = f"[ERROR] 상세 로드 실패: {ex}"
                clear_image()

            page.update()

        def refresh_detail():
            q = (tf_search.value or "").strip()

            if not q:
                page.update()
                return

            if conn_ui is None and not db_exists(tf_db.value):
                append_log("[INFO] DB가 없어서 검색 불가. 상단 버튼으로 DB를 생성하세요.")
                page.update()
                return

            try:
                ensure_conn()
                rows = query_suggest(conn_ui, q, limit=20)
                if not rows:
                    append_log(f"[INFO] 검색 결과 없음: {q}")
                else:
                    if len(rows) > 1:
                        append_log(f"[INFO] {len(rows)}건 중 첫 항목 표시")
                    show_detail(rows[0]["print_id"])
            except Exception as ex:
                append_log(f"[ERROR] 검색 실패: {ex}")

            page.update()

        def on_search_click(e):
            refresh_detail()

        btn_search = ft.ElevatedButton("검색", on_click=on_search_click, height=36)
        tf_search.on_submit = on_search_click

        def backup_db():
            dbp = tf_db.value.strip()
            if not db_exists(dbp):
                append_log("[WARN] DB가 없어서 백업할 수 없습니다.")
                return
            backup_path = f"{dbp}.bak"
            shutil.copy2(dbp, backup_path)
            append_log(f"[OK] DB 백업 완료: {backup_path}")

        def restore_db():
            nonlocal conn_ui
            dbp = tf_db.value.strip()
            backup_path = f"{dbp}.bak"
            if not os.path.exists(backup_path):
                append_log(f"[WARN] 백업 파일이 없습니다: {backup_path}")
                return
            if conn_ui:
                try:
                    conn_ui.close()
                except Exception:
                    pass
                conn_ui = None
            shutil.copy2(backup_path, dbp)
            append_log(f"[OK] DB 복원 완료: {backup_path} -> {dbp}")
            append_log("[INFO] 자동검증: 스킵(미구현)")

        def on_backup_click(e):
            backup_db()

        def on_restore_click(e):
            restore_db()

        btn_backup.on_click = on_backup_click
        btn_restore.on_click = on_restore_click

        def download_images(missing_only: bool):
            if conn_ui is None and not db_exists(tf_db.value):
                append_log("[WARN] DB가 없어서 이미지 다운로드 불가.")
                return
            ensure_conn()
            rows = conn_ui.execute(
                "SELECT card_number, COALESCE(image_url,'') AS image_url FROM prints ORDER BY card_number"
            ).fetchall()
            total = len(rows)
            if total == 0:
                append_log("[INFO] 이미지 대상이 없습니다.")
                return

            append_log(f"[IMG] 대상 {total}건 (누락분만={missing_only})")
            done = 0
            for row in rows:
                card_no = (row["card_number"] or "").strip()
                image_url = (row["image_url"] or "").strip()
                if not card_no or not image_url:
                    continue
                dest = local_image_path(project_root, card_no)
                if missing_only and dest.exists():
                    continue
                try:
                    download_image(image_url, dest)
                    done += 1
                    if done % 10 == 0:
                        append_log(f"[IMG] {done}건 다운로드 완료")
                except Exception as ex:
                    append_log(f"[IMG][WARN] {card_no}: {ex}")
            append_log(f"[IMG] 완료: {done}건")

        # --- Update pipeline (background thread) ---
        def do_update():
            nonlocal conn_ui
            try:
                pb.visible = True
                btn_update.disabled = True
                tf_search.disabled = True
                btn_backup.disabled = True
                btn_restore.disabled = True
                cb_missing_only.disabled = True
                page.update()

                dbp = tf_db.value.strip()
                append_log("[START] update + refine")

                # subprocess로 크롤링/정제
                for line in run_update_and_refine(dbp, delay=0.6):
                    append_log(line)

                append_log("[DONE] update + refine")

                download_images(cb_missing_only.value)
                append_log("[INFO] 자동검증: 스킵(미구현)")

                # UI 스레드용 DB 재연결
                try:
                    if conn_ui:
                        conn_ui.close()
                except Exception:
                    pass
                conn_ui = open_db(dbp)

                # 검색 결과 재갱신
                refresh_detail()

            except Exception as ex:
                append_log(f"[ERROR] 업데이트/정제 실패: {ex}")

            finally:
                pb.visible = False
                btn_update.disabled = False
                tf_search.disabled = False
                btn_backup.disabled = False
                btn_restore.disabled = False
                cb_missing_only.disabled = False
                page.update()

        def on_update_click(e):
            threading.Thread(target=do_update, daemon=True).start()

        btn_update.on_click = on_update_click

        # --- first-run: DB 없으면 안내 로그만 찍고 앱은 뜨게 ---
        if not db_exists(tf_db.value):
            append_log("[INFO] DB 파일이 없습니다.")
            append_log("[INFO] 상단 '자동 업데이트 + 이미지 + 자동검증'을 누르면 DB를 생성(크롤링+정제)합니다.")
        else:
            # DB 있으면 즉시 연결
            try:
                ensure_conn()
            except Exception as ex:
                append_log(f"[ERROR] DB open failed: {ex}")

        # --- Layout ---
        top = ft.Row(
            [
                ft.Text("DB:"),
                tf_db,
                btn_backup,
                btn_restore,
                cb_missing_only,
                btn_update,
                pb,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        search_row = ft.Row(
            [
                ft.Text("카드번호:"),
                tf_search,
                btn_search,
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        middle = ft.Column(
            [
                img_container,
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
                ft.Container(middle, expand=5),
                ft.VerticalDivider(width=1),
                ft.Container(right, expand=6),
            ],
            expand=True,
        )

        bottom = ft.Container(log_tf, padding=10, height=180)

        page.add(
            ft.Column(
                [
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
