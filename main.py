import flet as ft
import json
import threading
import urllib.request
import uuid
from datetime import datetime
import os

DATA_FILE = "notes.json"


def load_notes():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_notes(notes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def border_all(width, color):
    return ft.Border(
        left=ft.BorderSide(width, color),
        right=ft.BorderSide(width, color),
        top=ft.BorderSide(width, color),
        bottom=ft.BorderSide(width, color),
    )


def format_date(d):
    return datetime.fromisoformat(d).strftime("%d.%m.%Y %H:%M")


def main(page: ft.Page):
    page.title = "Smart Notes"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    notes = load_notes()
    current_note_id = [None]
    search_query = [""]

    title_field = ft.TextField(
        hint_text="Название заметки",
        border=ft.InputBorder.NONE,
        text_size=24,
        expand=True,
    )

    content_field = ft.TextField(
        hint_text="Напишите что-нибудь...\n\nПоддерживается Markdown:\n# Заголовок\n**жирный** *курсив*\n- список\n> цитата",
        multiline=True,
        min_lines=10,
        max_lines=30,
        border=ft.InputBorder.OUTLINE,
        border_color=ft.Colors.OUTLINE,
        text_size=14,
        expand=True,
    )

    tags_field = ft.TextField(
        hint_text="Добавить тег",
        border=ft.InputBorder.UNDERLINE,
        text_size=13,
        width=150,
    )

    tags_row = ft.Row(wrap=True, spacing=4, run_spacing=4)
    preview_md = ft.Markdown(
        value="",
        extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
        code_theme="monokai-sublime",
    )

    preview_container = ft.Container(
        content=ft.Column([
            ft.Text("Предпросмотр", size=13, color=ft.Colors.GREY),
            ft.Divider(height=1),
            preview_md,
        ], scroll=ft.ScrollMode.AUTO),
        padding=15,
        border=border_all(1, ft.Colors.OUTLINE),
        border_radius=8,
        expand=True,
        visible=False,
    )

    note_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)

    def refresh_preview():
        preview_md.value = content_field.value
        preview_md.update()

    def clear_editor():
        title_field.value = ""
        content_field.value = ""
        tags_row.controls.clear()
        preview_md.value = ""
        current_note_id[0] = None
        title_field.update()
        content_field.update()
        tags_row.update()
        preview_md.update()

    def load_note(note):
        current_note_id[0] = note["id"]
        title_field.value = note["title"]
        content_field.value = note["content"]
        tags_row.controls.clear()
        for tag in note.get("tags", []):
            add_tag_chip(tag)
        refresh_preview()
        page.update()

    def add_tag_chip(tag_name):
        chip = ft.Chip(
            label=ft.Text(tag_name, size=12),
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            on_delete=lambda e: remove_tag(chip),
            delete_icon=ft.Icons.CLOSE,
            delete_icon_tooltip="Удалить тег",
        )
        tags_row.controls.append(chip)
        tags_row.update()

    def remove_tag(chip):
        tags_row.controls.remove(chip)
        tags_row.update()

    def add_tag(e):
        tag = tags_field.value.strip()
        if tag and not any(
            c.label.value == tag for c in tags_row.controls
        ):
            add_tag_chip(tag)
            tags_field.value = ""
            tags_field.update()

    tags_field.on_submit = add_tag

    def get_current_tags():
        return [c.label.value for c in tags_row.controls]

    def save_note(e):
        if not title_field.value.strip():
            page.snack_bar = ft.SnackBar(
                ft.Text("Введите название заметки"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()
            return

        now = datetime.now().isoformat()
        note_data = {
            "id": current_note_id[0] or str(uuid.uuid4()),
            "title": title_field.value.strip(),
            "content": content_field.value,
            "tags": get_current_tags(),
            "updated_at": now,
        }

        if current_note_id[0]:
            for i, n in enumerate(notes):
                if n["id"] == current_note_id[0]:
                    note_data["created_at"] = n.get("created_at", now)
                    notes[i] = note_data
                    break
        else:
            note_data["created_at"] = now
            notes.append(note_data)
            current_note_id[0] = note_data["id"]

        save_notes(notes)
        build_note_list()
        page.snack_bar = ft.SnackBar(
            ft.Text("Сохранено!"),
            bgcolor=ft.Colors.PRIMARY,
        )
        page.snack_bar.open = True
        page.update()

    def delete_note(e):
        if current_note_id[0]:
            notes[:] = [n for n in notes if n["id"] != current_note_id[0]]
            save_notes(notes)
            clear_editor()
            build_note_list()
            page.update()

    def new_note(e):
        clear_editor()
        build_note_list()
        title_field.focus()
        page.update()

    def build_note_list():
        note_list.controls.clear()
        filtered = notes
        if search_query[0]:
            q = search_query[0].lower()
            filtered = [
                n for n in notes
                if q in n["title"].lower()
                or q in n["content"].lower()
                or any(q in t.lower() for t in n.get("tags", []))
            ]
        for n in filtered:
            preview_text = n["content"].replace("\n", " ")[:80]
            if len(n["content"]) > 80:
                preview_text += "..."
            tags_str = " ".join(f"#{t}" for t in n.get("tags", []))
            card = ft.Container(
                content=ft.Column([
                    ft.Text(n["title"], size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(preview_text, size=12, color=ft.Colors.GREY_700),
                    ft.Row([
                        ft.Text(tags_str, size=11, color=ft.Colors.PRIMARY),
                        ft.Text(format_date(n.get("updated_at", n.get("created_at", ""))), size=10, color=ft.Colors.GREY_400),
                    ], spacing=8),
                ], spacing=2),
                padding=12,
                border=border_all(
                    1,
                    ft.Colors.PRIMARY if n["id"] == current_note_id[0] else ft.Colors.OUTLINE,
                ),
                border_radius=8,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if n["id"] == current_note_id[0] else None,
                ink=True,
                on_click=lambda _, note=n: load_note(note),
            )
            note_list.controls.append(card)
        note_list.update()

    def search_change(e):
        search_query[0] = e.control.value
        build_note_list()

    def toggle_preview(e):
        preview_container.visible = not preview_container.visible
        content_field.visible = not preview_container.visible
        if preview_container.visible:
            refresh_preview()
        page.update()

    def toggle_theme(e):
        page.theme_mode = (
            ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT
            else ft.ThemeMode.LIGHT
        )
        page.update()

    search_field = ft.TextField(
        hint_text="Поиск заметок...",
        prefix_icon=ft.Icons.SEARCH,
        border=ft.InputBorder.OUTLINE,
        border_radius=20,
        text_size=14,
        width=300,
        on_change=search_change,
    )

    top_bar = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.CREATE_OUTLINED, size=28, color=ft.Colors.PRIMARY),
                ft.Text("Smart Notes", size=20, weight=ft.FontWeight.BOLD),
            ]),
            search_field,
            ft.Row([
                ft.IconButton(
                    icon=ft.Icons.PREVIEW,
                    tooltip="Предпросмотр",
                    on_click=toggle_preview,
                ),
                ft.IconButton(
                    icon=ft.Icons.LIGHT_MODE,
                    tooltip="Тема",
                    on_click=toggle_theme,
                ),
                ft.FloatingActionButton(
                    content=ft.Icon(ft.Icons.ADD),
                    mini=True,
                    bgcolor=ft.Colors.PRIMARY,
                    on_click=new_note,
                ),
            ]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.Padding(left=20, right=20, top=10, bottom=10),
        border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.OUTLINE)),
    )

    sidebar = ft.Container(
        content=ft.Column([
            ft.Text("Мои заметки", size=13, weight=ft.FontWeight.W_500, color=ft.Colors.GREY),
            note_list,
        ], expand=True),
        width=280,
        padding=15,
        border=ft.Border(right=ft.BorderSide(1, ft.Colors.OUTLINE)),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
    )

    editor = ft.Container(
        content=ft.Column([
            title_field,
            ft.Divider(height=1),
            ft.Row([
                tags_row,
                tags_field,
                ft.TextButton("+ тег", on_click=add_tag),
            ], wrap=True),
            ft.Row([
                content_field,
                preview_container,
            ], expand=True),
            ft.Row([
                ft.FilledButton("Сохранить", icon=ft.Icons.SAVE, on_click=save_note),
                ft.OutlinedButton("Удалить", icon=ft.Icons.DELETE, on_click=delete_note),
            ]),
        ], expand=True),
        padding=20,
        expand=True,
    )

    main_row = ft.Row([sidebar, editor], expand=True)

    page.add(top_bar, main_row)
    build_note_list()

    if notes:
        load_note(notes[0])


def keep_alive():
    url = os.getenv("RENDER_URL", "https://notes-app44.onrender.com")
    def ping():
        while True:
            threading.Event().wait(600)
            try:
                urllib.request.urlopen(url, timeout=10)
            except Exception:
                pass
    t = threading.Thread(target=ping, daemon=True)
    t.start()

keep_alive()

ft.app(
    target=main,
    host="0.0.0.0",
    port=int(os.getenv("PORT", 8080)),
    view=ft.AppView.WEB_BROWSER,
)
