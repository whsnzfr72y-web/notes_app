import subprocess, sys
try:
    import flet as ft
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flet"])
    import flet as ft

import json, uuid, os, threading, urllib.request
from datetime import datetime

DATA_FILE = "notes.json"
COLORS = ["#4A90D9", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6", "#1ABC9C", "#E67E22", "#95A5A6"]


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d.get("folders", ["Без папки"]), d.get("notes", [])
    return ["Без папки"], []


def save_data(folders, notes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"folders": folders, "notes": notes}, f, ensure_ascii=False, indent=2)


def border_all(w, c):
    return ft.Border(
        left=ft.BorderSide(w, c), right=ft.BorderSide(w, c),
        top=ft.BorderSide(w, c), bottom=ft.BorderSide(w, c),
    )


def fmt_date(d):
    return datetime.fromisoformat(d).strftime("%d.%m.%Y")


def main(page: ft.Page):
    page.title = "Smart Notes"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.spacing = 0

    folders, notes = load_data()
    current_id = [None]
    search_q = [""]
    active_folder = ["Все"]

    title_f = ft.TextField(hint_text="Название", border=ft.InputBorder.NONE, text_size=24, expand=True)
    content_f = ft.TextField(
        hint_text="Markdown: **жирный** *курсив* # заголовок", multiline=True,
        min_lines=10, max_lines=30, border=ft.InputBorder.OUTLINE,
        border_color=ft.Colors.OUTLINE, text_size=14, expand=True,
    )
    tags_f = ft.TextField(hint_text="тег", border=ft.InputBorder.UNDERLINE, text_size=13, width=120)
    tags_row = ft.Row(wrap=True, spacing=4, run_spacing=4)
    preview_md = ft.Markdown(value="", extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED, code_theme="monokai-sublime")
    preview_box = ft.Container(
        content=ft.Column([ft.Text("Предпросмотр", size=13), ft.Divider(1), preview_md], scroll=ft.ScrollMode.AUTO),
        padding=15, border=border_all(1, ft.Colors.OUTLINE), border_radius=8, expand=True, visible=False,
    )
    note_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=4, expand=True)
    folder_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=2)
    new_folder_f = ft.TextField(hint_text="Новая папка", text_size=12, width=140, visible=False)

    color_btns = ft.Row(spacing=4)
    chosen_color = [COLORS[0]]

    folder_dd = ft.Dropdown(
        options=[ft.dropdown.Option(f) for f in folders], width=160,
        text_size=13, value=folders[0] if folders else "Без папки",
    )

    def refresh_preview():
        preview_md.value = content_f.value
        preview_md.update()

    def clear_editor():
        title_f.value = ""; content_f.value = ""
        tags_row.controls.clear(); preview_md.value = ""
        current_id[0] = None; chosen_color[0] = COLORS[0]
        for b in color_btns.controls:
            b.opacity = 1.0 if b.data == COLORS[0] else 0.3
        color_btns.update()
        folder_dd.value = folders[0] if folders else "Без папки"
        for ctrl in [title_f, content_f, tags_row, preview_md, folder_dd]:
            ctrl.update()

    def load_note(n):
        current_id[0] = n["id"]
        title_f.value = n["title"]; content_f.value = n["content"]
        tags_row.controls.clear()
        for t in n.get("tags", []):
            c = ft.Chip(label=ft.Text(t, 12), bgcolor=ft.Colors.PRIMARY_CONTAINER,
                        on_delete=lambda e, chip=None: remove_tag(chip),
                        delete_icon=ft.Icons.CLOSE)
            tags_row.controls.append(c)
        chosen_color[0] = n.get("color", COLORS[0])
        for b in color_btns.controls:
            b.opacity = 1.0 if b.data == chosen_color[0] else 0.3
        color_btns.update()
        folder_dd.value = n.get("folder", folders[0] if folders else "Без папки")
        folder_dd.update()
        refresh_preview(); page.update()

    def remove_tag(chip):
        tags_row.controls.remove(chip); tags_row.update()

    def add_tag(e):
        t = tags_f.value.strip()
        if t and not any(c.label.value == t for c in tags_row.controls):
            chip = ft.Chip(label=ft.Text(t, 12), bgcolor=ft.Colors.PRIMARY_CONTAINER,
                          on_delete=lambda e, c=chip: remove_tag(c),
                          delete_icon=ft.Icons.CLOSE)
            tags_row.controls.append(chip)
            tags_f.value = ""; tags_f.update(); tags_row.update()
    tags_f.on_submit = add_tag

    def save_note(e):
        if not title_f.value.strip():
            page.snack_bar = ft.SnackBar(ft.Text("Введите название"), bgcolor=ft.Colors.ERROR)
            page.snack_bar.open = True; page.update(); return
        now = datetime.now().isoformat()
        nd = {
            "id": current_id[0] or str(uuid.uuid4()),
            "title": title_f.value.strip(), "content": content_f.value,
            "tags": [c.label.value for c in tags_row.controls],
            "color": chosen_color[0], "folder": folder_dd.value or folders[0],
            "updated_at": now,
        }
        if current_id[0]:
            for i, n in enumerate(notes):
                if n["id"] == current_id[0]:
                    nd["created_at"] = n.get("created_at", now)
                    notes[i] = nd; break
        else:
            nd["created_at"] = now; notes.append(nd); current_id[0] = nd["id"]
        save_data(folders, notes)
        build_notes(); rebuild_folders()
        page.snack_bar = ft.SnackBar(ft.Text("Сохранено!"), bgcolor=ft.Colors.PRIMARY)
        page.snack_bar.open = True; page.update()

    def delete_note(e):
        if current_id[0]:
            notes[:] = [n for n in notes if n["id"] != current_id[0]]
            save_data(folders, notes); clear_editor(); build_notes(); rebuild_folders(); page.update()

    def new_note(e):
        clear_editor(); build_notes(); title_f.focus(); page.update()

    def filter_folder(name):
        active_folder[0] = name; build_notes(); rebuild_folders(); page.update()

    def add_folder(e):
        name = new_folder_f.value.strip()
        if name and name not in folders:
            folders.append(name); folder_dd.options.append(ft.dropdown.Option(name))
            save_data(folders, notes); rebuild_folders(); folder_dd.update()
        new_folder_f.value = ""; new_folder_f.visible = False; new_folder_f.update()

    def show_folder_input(e):
        new_folder_f.visible = True; new_folder_f.focus(); page.update()

    def build_notes():
        note_list.controls.clear()
        f = notes
        if search_q[0]:
            q = search_q[0].lower()
            f = [n for n in f if q in n["title"].lower() or q in n["content"].lower() or any(q in t.lower() for t in n.get("tags", []))]
        if active_folder[0] != "Все":
            f = [n for n in f if n.get("folder") == active_folder[0]]
        for n in f:
            c = n.get("color", COLORS[0])
            prev = n["content"].replace("\n", " ")[:80]
            if len(n["content"]) > 80: prev += "..."
            tags_s = " ".join(f"#{t}" for t in n.get("tags", []))
            card = ft.Container(
                content=ft.Row([
                    ft.Container(width=4, height=60, bgcolor=c, border_radius=2),
                    ft.Column([
                        ft.Text(n["title"], 14, weight=ft.FontWeight.BOLD),
                        ft.Text(prev, 12, color=ft.Colors.GREY_700),
                        ft.Row([ft.Text(tags_s, 11, color=ft.Colors.PRIMARY), ft.Text(fmt_date(n.get("updated_at", n.get("created_at", ""))), 10, color=ft.Colors.GREY_400)], spacing=8),
                    ], spacing=2, expand=True),
                ], spacing=8),
                padding=ft.Padding(left=0, right=12, top=8, bottom=8),
                border=border_all(1, ft.Colors.PRIMARY if n["id"] == current_id[0] else ft.Colors.OUTLINE),
                border_radius=8, ink=True, on_click=lambda _, note=n: load_note(note),
            )
            note_list.controls.append(card)
        note_list.update()

    def rebuild_folders():
        folder_list.controls.clear()
        counts = {"Все": len(notes)}
        for n in notes:
            f = n.get("folder", "Без папки")
            counts[f] = counts.get(f, 0) + 1
        for f in ["Все"] + folders:
            cnt = counts.get(f, 0)
            is_active = active_folder[0] == f
            folder_list.controls.append(
                ft.Container(
                    ft.Row([
                        ft.Container(width=3, height=16, bgcolor=ft.Colors.PRIMARY if is_active else None, border_radius=2),
                        ft.Text(f, 13, weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL, color=ft.Colors.PRIMARY if is_active else None),
                        ft.Text(str(cnt), 11, color=ft.Colors.GREY),
                    ], spacing=6),
                    padding=8, border_radius=6,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER if is_active else None,
                    ink=True, on_click=lambda _, name=f: filter_folder(name),
                )
            )
        folder_list.update()

    def search_change(e):
        search_q[0] = e.control.value; build_notes()

    def toggle_preview(e):
        preview_box.visible = not preview_box.visible
        content_f.visible = not preview_box.visible
        if preview_box.visible: refresh_preview()
        page.update()

    def toggle_theme(e):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        page.update()

    def pick_color(e):
        chosen_color[0] = e.control.data
        for b in color_btns.controls:
            b.opacity = 1.0 if b.data == chosen_color[0] else 0.3
        color_btns.update()

    for clr in COLORS:
        btn = ft.Container(width=24, height=24, bgcolor=clr, border_radius=12, data=clr, ink=True, opacity=0.3 if clr != COLORS[0] else 1.0, on_click=pick_color)
        color_btns.controls.append(btn)

    search_f = ft.TextField(hint_text="Поиск...", prefix_icon=ft.Icons.SEARCH, border=ft.InputBorder.OUTLINE, border_radius=20, text_size=14, width=250, on_change=search_change)

    top_bar = ft.Container(
        ft.Row([
            ft.Row([ft.Icon(ft.Icons.CREATE_OUTLINED, 28, ft.Colors.PRIMARY), ft.Text("Smart Notes", 20, weight=ft.FontWeight.BOLD)]),
            search_f,
            ft.Row([
                ft.IconButton(icon=ft.Icons.PREVIEW, tooltip="Предпросмотр", on_click=toggle_preview),
                ft.IconButton(icon=ft.Icons.LIGHT_MODE, tooltip="Тема", on_click=toggle_theme),
                ft.FloatingActionButton(content=ft.Icon(ft.Icons.ADD), mini=True, bgcolor=ft.Colors.PRIMARY, on_click=new_note),
            ]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.Padding(20, 10, 20, 10), border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.OUTLINE)),
    )

    sidebar = ft.Container(
        ft.Column([
            ft.Text("Папки", 12, weight=ft.FontWeight.W_500, color=ft.Colors.GREY),
            ft.Row([ft.TextButton("+ папка", on_click=show_folder_input), new_folder_f, ft.IconButton(ft.Icons.CHECK, icon_size=16, on_click=add_folder)], wrap=True),
            folder_list,
            ft.Divider(1),
            ft.Text("Заметки", 12, weight=ft.FontWeight.W_500, color=ft.Colors.GREY),
            note_list,
        ], expand=True, spacing=4),
        width=280, padding=15, border=ft.Border(right=ft.BorderSide(1, ft.Colors.OUTLINE)), bgcolor=ft.Colors.SURFACE_CONTAINER_LOWEST,
    )

    editor = ft.Container(
        ft.Column([
            title_f, ft.Divider(1),
            ft.Row([ft.Text("Папка:", 13), folder_dd, ft.Text("Метка:", 13), color_btns], wrap=True),
            ft.Row([tags_row, tags_f, ft.TextButton("+ тег", on_click=add_tag)], wrap=True),
            ft.Row([content_f, preview_box], expand=True),
            ft.Row([ft.FilledButton("Сохранить", icon=ft.Icons.SAVE, on_click=save_note), ft.OutlinedButton("Удалить", icon=ft.Icons.DELETE, on_click=delete_note)]),
        ], expand=True),
        padding=20, expand=True,
    )

    page.add(top_bar, ft.Row([sidebar, editor], expand=True))
    rebuild_folders(); build_notes()
    if notes: load_note(notes[0])


def keep_alive():
    url = os.getenv("RENDER_URL", "https://notes-app44.onrender.com")
    def ping():
        while True:
            threading.Event().wait(600)
            try: urllib.request.urlopen(url, timeout=10)
            except: pass
    threading.Thread(target=ping, daemon=True).start()

keep_alive()

ft.app(target=main, host="127.0.0.1", port=8765, view=ft.AppView.WEB_BROWSER)
