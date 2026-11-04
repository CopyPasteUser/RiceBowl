"""Interactive, read-only desktop sketches for future RiceBowl families.

These GTK widgets operate on sample data only. No desktop commands, process
launches, session changes or settings writes are performed by the previews.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Concept:
    key: str
    title: str
    caption: str
    menu_title: str
    menu_button: str
    wallpaper: str | None
    applications: tuple[tuple[str, str], ...]


COMMON = (
    ("Terminal", "utilities-terminal-symbolic"),
    ("Settings", "preferences-system-symbolic"),
    ("Text Editor", "accessories-text-editor-symbolic"),
)

CONCEPTS = {
    "winxp": Concept(
        "winxp", "Windows XP Luna", "Blue Luna chrome, meadow and a two-column Start menu",
        "All Programs", "Start", "luna-hills.jpg",
        (("My Computer", "computer-symbolic"), ("My Documents", "folder-documents-symbolic"),
         ("Internet", "web-browser-symbolic"), *COMMON),
    ),
    "winclassic": Concept(
        "winclassic", "Windows 98 SE", "Teal desktop, compact windows and classic Start",
        "Programs", "Start", None,
        (("My Computer", "computer-symbolic"), ("Network", "network-workgroup-symbolic"),
         ("Files", "system-file-manager-symbolic"), *COMMON),
    ),
    "chromeos": Concept(
        "chromeos", "ChromeOS", "Lightweight shelf, app launcher and quick settings",
        "Apps", "Apps", None,
        (("Files", "system-file-manager-symbolic"), ("Browser", "web-browser-symbolic"),
         ("Media", "multimedia-player-symbolic"), *COMMON),
    ),
    "frutiger": Concept(
        "frutiger", "Y2K / Frutiger Aero", "Bright aqua glass, lush landscape and Linux penguin",
        "Applications", "Apps", "frutiger-future.jpg",
        (("Home", "user-home-symbolic"), ("Web", "web-browser-symbolic"),
         ("Music", "audio-x-generic-symbolic"), *COMMON),
    ),
}


def search_apps(key: str, query: str) -> tuple[tuple[str, str], ...]:
    """Filter local sample labels. Preview never queries or launches host apps."""
    needle = query.strip().casefold()
    return tuple(item for item in CONCEPTS[key].applications if needle in item[0].casefold())


CSS = b"""
.concept-xp { background-image: linear-gradient(#2176c6, #0f4ca9); color: #fff; }
.concept-classic { background: #008080; color: #fff; }
.concept-chrome { background-image: linear-gradient(135deg, #daeafa, #f5dbec 52%, #dae0ff); color: #27344f; }
.concept-frutiger { background-image: linear-gradient(120deg, #4fe5cf, #1cbbdb 52%, #91dca6); color: #063956; }
.concept-desktop { padding: 18px; }
.concept-shortcuts { padding: 16px; }
.concept-shortcut { color: #fff; font-weight: bold; font-size: 11px; text-shadow: 0 1px 3px #1b3955; }
.concept-chrome .concept-shortcut, .concept-over-frutiger .concept-shortcut {
  color: #25314a; text-shadow: none; }
.concept-panel { padding: 4px 7px; min-height: 43px; }
.concept-xp-panel { background-image: linear-gradient(#438ce6, #0c46a9); color: #fff; }
.concept-classic-panel { background: #bfbfbf; border-top: 2px solid #fff; color: #111; }
.concept-chrome-panel { background: rgba(245,248,255,.94); color: #25314a; border-radius: 21px 21px 0 0; }
.concept-frutiger-panel { background: rgba(112,240,224,.88); color: #063956; border-top: 1px solid #eaffff; }
.concept-task, .concept-start, .concept-close, .concept-app {
  background-image: none; box-shadow: none; border-radius: 4px; padding: 7px 12px;
  border: 1px solid transparent; color: inherit; }
.concept-task, .concept-close { background-color: rgba(255,255,255,.14); }
.concept-task:hover, .concept-close:hover, .concept-app:hover { background: rgba(100,156,199,.32); }
.concept-start { font-weight: bold; background-color: #389d29; color: #fff; border-radius: 18px; }
.concept-classic-panel .concept-start { color: #111; background: #d4d4d4; border: 2px outset #eee; border-radius: 0; }
.concept-chrome-panel .concept-start { color: #27344f; background: #e2e9ff; border-radius: 22px; }
.concept-frutiger-panel .concept-start { color: #063956; background: #b6fbd8; border: 1px solid #fff; border-radius: 24px; }
.concept-panel label { color: inherit; }
.concept-panel button:focus, .concept-menu button:focus, .concept-window button:focus {
  outline: 2px solid #ffd84e; outline-offset: 1px; }
.concept-menu { background: #f9fbff; border: 2px solid #3b80c9; border-radius: 6px;
  color: #23324b; padding: 12px; }
.concept-menu label, .concept-window label { color: #23324b; }
.concept-classic-menu { background: #c9c9c9; border: 2px outset #f7f7f7; border-radius: 0; }
.concept-chrome-menu { background: #f7f9ff; border: 1px solid #c5d0e6; border-radius: 18px; }
.concept-frutiger-menu { background: #d8fff7; border: 1px solid #91e6d5; border-radius: 18px; }
.concept-menu .concept-app { color: #23324b; background: transparent; }
.concept-xp-links { background: #dfeafe; padding: 10px; border-radius: 4px; }
.concept-menu-head { color: #185bba; font-weight: bold; font-size: 16px; }
.concept-menu entry { background: #fff; color: #1b2e46; border: 1px solid #8dabc7; border-radius: 4px; }
.concept-window { background: #fafcff; color: #23324b; border: 2px solid #2d78bb; border-radius: 5px; }
.concept-classic-window { border: 2px outset #fff; border-radius: 0; }
.concept-chrome-window { border: 1px solid #bacce7; border-radius: 15px; }
.concept-frutiger-window { border: 2px solid #9be7e2; border-radius: 14px; }
.concept-window-title { background: #2876c9; color: #fff; padding: 8px 12px; font-weight: bold; }
.concept-window-title label { color: #fff; }
.concept-classic-window .concept-window-title { background: #092b85; }
.concept-chrome-window .concept-window-title { background: #e1eafa; color: #27344f; }
.concept-chrome-window .concept-window-title label { color: #27344f; }
.concept-frutiger-window .concept-window-title { background: #6eddd8; color: #063956; }
.concept-frutiger-window .concept-window-title label { color: #063956; }
.concept-window-body { padding: 22px; }
.concept-caption { color: #5b6e84; font-size: 11px; }
.concept-teaser { padding: 20px; min-height: 190px; }
.concept-teaser-title { font-size: 22px; font-weight: bold; color: #fff; }
.concept-chrome .concept-teaser-title, .concept-frutiger .concept-teaser-title { color: #173b61; }
.concept-teaser-note { font-size: 12px; color: #fff; }
.concept-chrome .concept-teaser-note, .concept-frutiger .concept-teaser-note { color: #173b61; }
"""

_provider = None


def _style(widget, *classes):
    for name in classes:
        widget.get_style_context().add_class(name)
    return widget


def install_css(Gtk, Gdk):
    """Install the scoped CSS provider once per screen."""
    global _provider
    if _provider is None:
        _provider = Gtk.CssProvider()
        _provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), _provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def teaser(Gtk, key):
    """Compact gallery tile, using the same identity as the interactive preview."""
    concept = CONCEPTS[key]
    card = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=13),
                  "concept-teaser", _theme(key))
    title = _style(Gtk.Label(label=concept.title, xalign=0), "concept-teaser-title")
    card.pack_start(title, False, False, 0)
    note = _style(Gtk.Label(label=concept.caption, xalign=0), "concept-teaser-note")
    card.pack_start(note, False, False, 0)
    card.pack_start(Gtk.Box(), True, True, 0)
    panel = _style(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10),
                   "concept-panel", _panel(key))
    panel.pack_start(Gtk.Label(label=concept.menu_button), False, False, 0)
    panel.pack_start(Gtk.Label(label="Files     Browser     Terminal"), False, False, 0)
    panel.pack_start(Gtk.Box(), True, True, 0)
    panel.pack_start(Gtk.Label(label="12:42"), False, False, 0)
    card.pack_start(panel, False, False, 0)
    return card


def _theme(key):
    return {"winxp": "concept-xp", "winclassic": "concept-classic",
            "chromeos": "concept-chrome", "frutiger": "concept-frutiger"}[key]


def _panel(key):
    return {"winxp": "concept-xp-panel", "winclassic": "concept-classic-panel",
            "chromeos": "concept-chrome-panel", "frutiger": "concept-frutiger-panel"}[key]


def _variant(key):
    return {"winxp": "xp", "winclassic": "classic", "chromeos": "chrome",
            "frutiger": "frutiger"}[key]


def show_dialog(parent, Gtk, Gdk, GLib, key):
    """Open a non-installing, interactive GTK3 desktop concept."""
    concept = CONCEPTS[key]
    install_css(Gtk, Gdk)
    dialog = Gtk.Dialog(title=concept.title + " — RiceBowl prototype", transient_for=parent,
                        flags=Gtk.DialogFlags.MODAL)
    dialog.set_default_size(1050, 720)
    dialog.add_button("Close preview", Gtk.ResponseType.CLOSE)
    content = dialog.get_content_area()
    content.set_spacing(8)
    content.set_margin_start(12)
    content.set_margin_end(12)
    content.set_margin_top(9)
    explanation = Gtk.Label(
        label="Interactive sample desktop · No apps launch and no XFCE settings change", xalign=0)
    content.pack_start(explanation, False, False, 0)

    canvas = Gtk.Overlay()
    canvas.set_size_request(-1, 530)
    content.pack_start(canvas, True, True, 0)
    background = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "concept-desktop")
    if concept.wallpaper:
        _style(background, "concept-over-" + _variant(key))
        # CSS url() backgrounds are not rendered reliably on every GTK theme.
        # Render original local artwork as a cropped pixbuf instead.
        from gi.repository import GdkPixbuf

        from .hub_art import aspect_fill
        from .installer import project_root

        picture = Gtk.Image()
        source = GdkPixbuf.Pixbuf.new_from_file(
            str(project_root() / "assets" / "wallpapers" / concept.wallpaper))
        canvas.add(picture)
        image_size = [0, 0]

        def resize_background(_widget, allocation):
            size = [allocation.width, allocation.height]
            if allocation.width > 0 and allocation.height > 0 and image_size != size:
                image_size[:] = size
                picture.set_from_pixbuf(aspect_fill(
                    source, allocation.width, allocation.height, GdkPixbuf.InterpType.BILINEAR))

        canvas.connect("size-allocate", resize_background)
        canvas.add_overlay(background)
    else:
        _style(background, _theme(key))
        canvas.add(background)

    shortcuts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=19)
    shortcuts.set_halign(Gtk.Align.START)
    for title, icon in concept.applications[:3]:
        item = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        item.set_halign(Gtk.Align.CENTER)
        item.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG), False, False, 0)
        item.pack_start(_style(Gtk.Label(label=title), "concept-shortcut"), False, False, 0)
        shortcuts.pack_start(item, False, False, 0)
    background.pack_start(shortcuts, True, True, 0)

    bar = _style(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6),
                 "concept-panel", _panel(key))
    background.pack_start(bar, False, False, 0)
    start = _style(Gtk.Button(), "concept-start")
    start_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    if key in ("winxp", "winclassic", "frutiger"):
        from gi.repository import GdkPixbuf

        from .installer import project_root

        mark = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(project_root() / "assets" / "ten-start.svg"), 20, 20, True)
        start_content.pack_start(Gtk.Image.new_from_pixbuf(mark), False, False, 0)
    start_content.pack_start(Gtk.Label(label=concept.menu_button), False, False, 0)
    start.add(start_content)
    start.get_accessible().set_name("Toggle sample application launcher")
    bar.pack_start(start, False, False, 0)
    tasks = []
    for title in ("Files", "Browser"):
        task = _style(Gtk.Button(label=title), "concept-task")
        bar.pack_start(task, False, False, 0)
        tasks.append(task)
    bar.pack_start(Gtk.Box(), True, True, 0)
    status = Gtk.Label(label="Sample mode")
    bar.pack_start(status, False, False, 6)
    bar.pack_start(Gtk.Label(label=GLib.DateTime.new_now_local().format("%H:%M")), False, False, 9)

    menu = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                  "concept-menu", "concept-" + _variant(key) + "-menu")
    menu.set_size_request(455 if key == "winxp" else 375 if key == "chromeos" else 300,
                          345 if key == "winxp" else 300)
    menu.set_halign(Gtk.Align.CENTER if key == "chromeos" else Gtk.Align.START)
    menu.set_valign(Gtk.Align.END)
    menu.set_margin_bottom(52)
    menu.set_margin_start(11)
    menu.pack_start(_style(Gtk.Label(label=concept.menu_title, xalign=0),
                           "concept-menu-head"), False, False, 0)
    search = Gtk.SearchEntry()
    search.set_placeholder_text("Search example apps")
    search.get_accessible().set_name("Search sample applications")
    menu.pack_start(search, False, False, 0)
    columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    menu.pack_start(columns, True, True, 0)
    result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    columns.pack_start(result_box, True, True, 0)
    if key == "winxp":
        links = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "concept-xp-links")
        links.set_size_request(140, -1)
        for title in ("My Documents", "My Computer", "Settings"):
            link = _style(Gtk.Button(label=title), "concept-app")
            link.connect("clicked", lambda _button, selected=title: open_example(selected))
            links.pack_start(link, False, False, 0)
        columns.pack_start(links, False, False, 0)
    canvas.add_overlay(menu)

    window = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "concept-window",
                    "concept-" + _variant(key) + "-window")
    window.set_size_request(360, 255)
    window.set_halign(Gtk.Align.END)
    window.set_valign(Gtk.Align.CENTER)
    window.set_margin_end(30)
    header = _style(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "concept-window-title")
    heading = Gtk.Label(label="File Manager", xalign=0)
    header.pack_start(heading, True, True, 0)
    close = _style(Gtk.Button(label="×"), "concept-close")
    close.get_accessible().set_name("Close sample file manager")
    header.pack_start(close, False, False, 0)
    window.pack_start(header, False, False, 0)
    folders = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14), "concept-window-body")
    for folder in ("Desktop", "Documents", "Downloads", "Pictures"):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13)
        row.pack_start(Gtk.Image.new_from_icon_name("folder-symbolic", Gtk.IconSize.MENU),
                       False, False, 0)
        row.pack_start(Gtk.Label(label=folder), False, False, 0)
        folders.pack_start(row, False, False, 0)
    window.pack_start(folders, True, True, 0)
    canvas.add_overlay(window)

    def open_example(title):
        status.set_text(title + " · preview only")
        heading.set_text(title)
        window.show_all()
        menu.hide()

    def refresh(*_args):
        for child in result_box.get_children():
            result_box.remove(child)
        matches = search_apps(key, search.get_text())
        if not matches:
            result_box.pack_start(_style(Gtk.Label(label="No matching sample apps", xalign=0),
                                         "concept-caption"), False, False, 8)
        for title, icon in matches:
            button = _style(Gtk.Button(), "concept-app")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            row.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
            row.pack_start(Gtk.Label(label=title), True, True, 0)
            button.add(row)
            button.connect("clicked", lambda _button, name=title: open_example(name))
            result_box.pack_start(button, False, False, 0)
        result_box.show_all()

    refresh()
    search.connect("search-changed", refresh)
    def toggle_menu(_button):
        if menu.get_visible():
            menu.hide()
        else:
            menu.show_all()
            search.grab_focus()

    def dismiss_menu(_widget, event):
        if event.keyval == Gdk.KEY_Escape and menu.get_visible():
            menu.hide()
            return True
        return False

    start.connect("clicked", toggle_menu)
    close.connect("clicked", lambda _button: window.hide())
    for button in tasks:
        button.connect("clicked", lambda widget: open_example(widget.get_label()))
    dialog.connect("key-press-event", dismiss_menu)
    dialog.show_all()
    if key == "chromeos":
        # A centered app drawer and a right-hand window collide at 1024px.
        # Start the study in launcher mode; shelf buttons open the sample window.
        window.hide()
    menu.show_all()
    try:
        dialog.run()
    finally:
        dialog.destroy()
