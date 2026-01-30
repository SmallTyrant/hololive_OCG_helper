import flet as ft
from app.services.db import open_db, query_suggest, load_card_detail

def launch_app(db_path: str):
    conn = open_db(db_path)

    def main(page: ft.Page):
        page.title = "hololive OCG helper"
        page.window_width = 1100
        page.window_height = 800

        search = ft.TextField(label="카드번호 / 이름 / 태그 검색")
        dropdown = ft.ListView(expand=True)
        detail = ft.TextField(multiline=True, read_only=True, expand=True)

        def on_search(e):
            dropdown.controls.clear()
            for r in query_suggest(conn, search.value):
                dropdown.controls.append(
                    ft.ListTile(
                        title=ft.Text(f"{r['card_number']} | {r['name_ja']}"),
                        on_click=lambda ev, pid=r["print_id"]: show_detail(pid)
                    )
                )
            page.update()

        def show_detail(pid: int):
            card = load_card_detail(conn, pid)
            if not card:
                return
            detail.value = card.get("raw_text","")
            page.update()

        search.on_change = on_search

        page.add(
            search,
            ft.Row([dropdown, detail], expand=True)
        )

    ft.app(target=main)
