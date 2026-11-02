"""Read-only Windows 10-inspired desktop concept for the RiceHub gallery.

All program entries and quick actions in this preview are examples. This
module never launches programs, modifies XFCE, or creates background services.
"""

from __future__ import annotations


SAMPLE_APPS = (
    ("File Explorer", "system-file-manager-symbolic"),
    ("Web Browser", "web-browser-symbolic"),
    ("Terminal", "utilities-terminal-symbolic"),
    ("Settings", "preferences-system-symbolic"),
    ("Text Editor", "accessories-text-editor-symbolic"),
    ("Calculator", "accessories-calculator-symbolic"),
    ("Photos", "image-x-generic-symbolic"),
    ("Music", "audio-x-generic-symbolic"),
)


def matching_apps(query: str) -> tuple[tuple[str, str], ...]:
    needle = query.strip().casefold()
    return tuple(app for app in SAMPLE_APPS if needle in app[0].casefold())


CSS = b"""
.w10-dialog { background: #1a222e; }
.w10-hero, .w10-desktop {
  background-image: linear-gradient(120deg, #001e51, #087bce 58%, #003681);
  color: #fff; border-radius: 2px;
}
.w10-hero-title { color: #fff; font-size: 22px; font-weight: 600; }
.w10-hero-sub { color: #e1f2ff; font-size: 12px; }
.w10-wall-label { color: #fff; font-size: 12px; text-shadow: 0 1px 3px #002344; }
.w10-shortcut-icon { color: #fff; }
.w10-taskbar { background: rgba(19,23,30,.97); color: #fff; padding: 3px 7px; }
.w10-task, .w10-start, .w10-tray-button {
  background: transparent; background-image: none; box-shadow: none;
  border: 1px solid transparent; border-radius: 0; color: #fff;
  padding: 6px 10px; min-height: 31px;
}
.w10-task:hover, .w10-start:hover, .w10-tray-button:hover { background: #434a54; }
.w10-task:focus, .w10-start:focus, .w10-tray-button:focus,
.w10-app:focus, .w10-tile:focus { border-color: #75c7ff; outline: 1px solid #75c7ff; }
.w10-active { background: #424951; border-bottom: 2px solid #32a8f6; }
.w10-search-button { background: #f3f5f8; color: #2a3038; border-radius: 0;
  padding: 7px 18px; border: 1px solid #c6d1dc; box-shadow: none; }
.w10-time { color: #fff; font-size: 11px; }
.w10-menu, .w10-action-center { background: rgba(30,35,43,.98); color: #fff;
  border: 1px solid #4b525d; border-radius: 0; padding: 12px; }
.w10-menu-head { color: #fff; font-size: 15px; font-weight: 600; }
.w10-menu-copy { color: #cad4e1; font-size: 11px; }
.w10-search { background: #f9fbff; color: #212933; border: 2px solid #33a8f4;
  border-radius: 0; padding: 7px; }
.w10-app { background: transparent; color: #fff; border: 1px solid transparent;
  border-radius: 0; box-shadow: none; padding: 7px; }
.w10-app:hover { background: #465160; }
.w10-tile { color: #fff; border: 1px solid transparent; border-radius: 0;
  background: #0078d7; background-image: none; box-shadow: none; padding: 8px; }
.w10-tile:hover { background: #168deb; }
.w10-tile-dark { background: #1461ab; }
.w10-tile-dark:hover { background: #2678c4; }
.w10-divider { background: #5c6570; min-height: 1px; }
.w10-quick { border-radius: 0; background: #3a414b; color: #fff;
  border: 1px solid #5a6572; padding: 9px 6px; box-shadow: none; }
.w10-quick:hover { background: #505f70; }
.w10-quick-on { background: #0078d7; border-color: #219cff; }
.w10-close-hint { color: #adbbcc; font-size: 11px; }
"""

_provider = None


def _style(widget, name):
    widget.get_style_context().add_class(name)
    return widget


def install_css(Gtk, Gdk):
    """Register one CSS provider regardless of repeated preview openings."""
    global _provider
    if _provider is None:
        from .installer import project_root

        wallpaper = project_root() / "assets/windows10-bloom.svg"
        background = (f'.w10-wallpaper {{ background-image: url("{wallpaper.as_uri()}"); '
                      'background-size: cover; background-position: center; }')
        _provider = Gtk.CssProvider()
        _provider.load_from_data(CSS + background.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), _provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def _label(Gtk, text, style="w10-menu-copy"):
    return _style(Gtk.Label(label=text, xalign=0), style)


def _symbol(Gtk, name, size):
    return Gtk.Image.new_from_icon_name(name, size)


def _box(Gtk, orientation, spacing=0):
    return Gtk.Box(orientation=orientation, spacing=spacing)


def teaser(Gtk):
    """Compact read-only concept preview in RiceHub's Discover gallery."""
    card = _style(_box(Gtk, Gtk.Orientation.VERTICAL, 8), "w10-hero")
    card.set_size_request(-1, 190)
    title = _label(Gtk, "Windows 10 · Fluent-inspired", "w10-hero-title")
    title.set_margin_start(22)
    title.set_margin_top(32)
    card.pack_start(title, False, False, 0)
    note = _label(Gtk, "Start, tiles and Action Center · interactive prototype", "w10-hero-sub")
    note.set_margin_start(22)
    card.pack_start(note, False, False, 0)
    card.pack_start(Gtk.Box(), True, True, 0)
    bar = _style(_box(Gtk, Gtk.Orientation.HORIZONTAL, 12), "w10-taskbar")
    bar.pack_start(_label(Gtk, "⊞", "w10-time"), False, False, 7)
    bar.pack_start(_label(Gtk, "Search    ◈    Files    Browser", "w10-time"), False, False, 0)
    bar.pack_start(Gtk.Box(), True, True, 0)
    bar.pack_start(_label(Gtk, "12:42  ▢", "w10-time"), False, False, 7)
    card.pack_start(bar, False, False, 0)
    return card


def show_dialog(parent, Gtk, Gdk, GLib, screenshot_paths=None):
    """Show a working Start/search/Action Center preview, with no host writes."""
    from .installer import project_root

    install_css(Gtk, Gdk)
    dialog = Gtk.Dialog(title="Windows 10 — RiceHub prototype", transient_for=parent,
                        flags=Gtk.DialogFlags.MODAL)
    _style(dialog, "w10-dialog")
    dialog.set_default_size(1050, 700)
    dialog.add_button("Close preview", Gtk.ResponseType.CLOSE)
    content = dialog.get_content_area()
    content.set_spacing(9)
    content.set_margin_start(15)
    content.set_margin_end(15)
    content.set_margin_top(10)
    content.pack_start(_label(Gtk, "Windows 10-inspired desktop · First prototype", "w10-menu-head"),
                       False, False, 0)
    content.pack_start(_label(Gtk, "Explore the sample Start menu, search and Action Center. No applications launch and no XFCE settings change."),
                       False, False, 0)

    canvas = Gtk.Overlay()
    canvas.set_size_request(-1, 515)
    content.pack_start(canvas, True, True, 0)
    wallpaper = project_root() / "assets/windows10-bloom.svg"
    background = _box(Gtk, Gtk.Orientation.VERTICAL)
    _style(background, "w10-wallpaper" if wallpaper.is_file() else "w10-desktop")
    canvas.add(background)

    shortcuts = _box(Gtk, Gtk.Orientation.VERTICAL, 13)
    shortcuts.set_margin_top(25)
    shortcuts.set_margin_start(26)
    for name, icon in (("This PC", "computer-symbolic"), ("Documents", "folder-documents-symbolic"),
                       ("Recycle Bin", "user-trash-symbolic")):
        item = _box(Gtk, Gtk.Orientation.VERTICAL, 4)
        item.set_halign(Gtk.Align.START)
        item.pack_start(_style(_symbol(Gtk, icon, Gtk.IconSize.DIALOG), "w10-shortcut-icon"), False, False, 0)
        item.pack_start(_label(Gtk, name, "w10-wall-label"), False, False, 0)
        shortcuts.pack_start(item, False, False, 0)
    background.pack_start(shortcuts, True, True, 0)

    bar = _style(_box(Gtk, Gtk.Orientation.HORIZONTAL, 2), "w10-taskbar")
    background.pack_start(bar, False, False, 0)
    start = _style(Gtk.Button(label="⊞"), "w10-start")
    start.get_accessible().set_name("Toggle Start preview")
    bar.pack_start(start, False, False, 0)
    search_button = _style(Gtk.Button(label="⌕  Type here to search"), "w10-search-button")
    bar.pack_start(search_button, False, False, 0)
    for name, icon in SAMPLE_APPS[:3]:
        button = _style(Gtk.Button(), "w10-task")
        button.set_image(_symbol(Gtk, icon, Gtk.IconSize.LARGE_TOOLBAR))
        button.set_tooltip_text(name + " (sample)")
        button.get_accessible().set_name("Sample shortcut: " + name)
        button.connect("clicked", lambda _button, selected=name: select_sample(selected))
        bar.pack_start(button, False, False, 0)
    bar.pack_start(Gtk.Box(), True, True, 0)
    bar.pack_start(_label(Gtk, "ENG", "w10-time"), False, False, 5)
    clock = _label(Gtk, GLib.DateTime.new_now_local().format("%H:%M"), "w10-time")
    bar.pack_start(clock, False, False, 8)
    action_button = _style(Gtk.Button(label="▤"), "w10-tray-button")
    action_button.get_accessible().set_name("Toggle Action Center preview")
    bar.pack_start(action_button, False, False, 0)

    menu = _style(_box(Gtk, Gtk.Orientation.VERTICAL, 9), "w10-menu")
    menu.set_size_request(595, 415)
    menu.set_halign(Gtk.Align.START)
    menu.set_valign(Gtk.Align.END)
    menu.set_margin_start(0)
    menu.set_margin_bottom(49)
    canvas.add_overlay(menu)

    menu.pack_start(_label(Gtk, "Start", "w10-menu-head"), False, False, 0)
    search = _style(Gtk.SearchEntry(), "w10-search")
    search.set_placeholder_text("Search apps")
    search.get_accessible().set_name("Search sample applications")
    menu.pack_start(search, False, False, 0)

    columns = _box(Gtk, Gtk.Orientation.HORIZONTAL, 14)
    menu.pack_start(columns, True, True, 0)
    list_side = _box(Gtk, Gtk.Orientation.VERTICAL, 4)
    list_side.set_size_request(255, -1)
    columns.pack_start(list_side, False, False, 0)
    list_side.pack_start(_label(Gtk, "All apps", "w10-menu-copy"), False, False, 4)
    results = _box(Gtk, Gtk.Orientation.VERTICAL, 0)
    list_side.pack_start(results, True, True, 0)

    tiles_side = _box(Gtk, Gtk.Orientation.VERTICAL, 9)
    columns.pack_start(tiles_side, True, True, 0)
    tiles_side.pack_start(_label(Gtk, "Productivity", "w10-menu-copy"), False, False, 0)
    tile_grid = Gtk.Grid(column_spacing=5, row_spacing=5)
    tiles_side.pack_start(tile_grid, False, False, 0)

    center = _style(_box(Gtk, Gtk.Orientation.VERTICAL, 10), "w10-action-center")
    center.set_size_request(298, 412)
    center.set_halign(Gtk.Align.END)
    center.set_valign(Gtk.Align.END)
    center.set_margin_bottom(49)
    canvas.add_overlay(center)
    center.pack_start(_label(Gtk, "Action Center", "w10-menu-head"), False, False, 0)
    center.pack_start(_label(Gtk, "Notifications", "w10-menu-copy"), False, False, 0)
    center.pack_start(_label(Gtk, "No new notifications in this preview."), False, False, 0)
    center.pack_start(Gtk.Box(), True, True, 0)
    center.pack_start(_label(Gtk, "Quick actions · examples only", "w10-menu-copy"), False, False, 0)
    actions = Gtk.Grid(column_spacing=5, row_spacing=5)
    center.pack_start(actions, False, False, 0)

    feedback = _label(Gtk, "Preview only — your current desktop is unchanged.", "w10-close-hint")
    content.pack_start(feedback, False, False, 0)

    def select_sample(name):
        feedback.set_text(f"{name} is a sample entry; nothing was launched or changed.")

    for index, (name, icon) in enumerate((SAMPLE_APPS[0], SAMPLE_APPS[1], SAMPLE_APPS[3], SAMPLE_APPS[6])):
        tile = _style(Gtk.Button(), "w10-tile" if index % 3 else "w10-tile-dark")
        tile.set_size_request(122, 71)
        column = _box(Gtk, Gtk.Orientation.VERTICAL, 3)
        column.pack_start(_symbol(Gtk, icon, Gtk.IconSize.LARGE_TOOLBAR), True, True, 0)
        column.pack_start(_label(Gtk, name, "w10-wall-label"), False, False, 0)
        tile.add(column)
        tile.get_accessible().set_name("Sample tile: " + name)
        tile.connect("clicked", lambda _button, selected=name: select_sample(selected))
        tile_grid.attach(tile, index % 2, index // 2, 1, 1)

    for index, name in enumerate(("Network", "Bluetooth", "Night light", "Settings")):
        quick = _style(Gtk.Button(label=name), "w10-quick")
        quick.set_size_request(132, 49)
        quick.get_accessible().set_name("Sample quick action: " + name)
        quick.connect("clicked", lambda _button, selected=name: select_sample(selected))
        actions.attach(quick, index % 2, index // 2, 1, 1)

    def populate(*_args):
        for child in results.get_children():
            results.remove(child)
        matches = matching_apps(search.get_text())[:7]
        if not matches:
            results.pack_start(_label(Gtk, "No matching sample applications."), False, False, 8)
        for name, icon in matches:
            item = _style(Gtk.Button(), "w10-app")
            row = _box(Gtk, Gtk.Orientation.HORIZONTAL, 11)
            row.pack_start(_symbol(Gtk, icon, Gtk.IconSize.MENU), False, False, 0)
            row.pack_start(_label(Gtk, name, "w10-wall-label"), True, True, 0)
            item.add(row)
            item.get_accessible().set_name("Sample app: " + name)
            item.connect("clicked", lambda _button, selected=name: select_sample(selected))
            results.pack_start(item, False, False, 0)
        results.show_all()

    def toggle_menu(_button=None):
        opening = not menu.get_visible()
        center.hide()
        menu.set_visible(opening)
        if opening:
            search.grab_focus()

    def toggle_center(_button=None):
        opening = not center.get_visible()
        menu.hide()
        center.set_visible(opening)

    def on_key(_widget, event):
        if event.keyval == Gdk.KEY_Escape:
            menu.hide()
            center.hide()
            return True
        return False

    search.connect("search-changed", populate)
    start.connect("clicked", toggle_menu)
    search_button.connect("clicked", lambda _button: (menu.show(), center.hide(), search.grab_focus()))
    action_button.connect("clicked", toggle_center)
    dialog.connect("key-press-event", on_key)
    populate()
    dialog.show_all()
    center.hide()
    search.grab_focus()

    if screenshot_paths is not None:
        # Development-only capture path: these are real GTK pixels under X11.
        def capture(path):
            window = dialog.get_window()
            pixels = Gdk.pixbuf_get_from_window(window, 0, 0, *dialog.get_size())
            if pixels is None:
                raise RuntimeError("Unable to capture the GTK dialog")
            pixels.savev(str(path), "png", [], [])

        def capture_center():
            capture(screenshot_paths[1])
            dialog.response(Gtk.ResponseType.CLOSE)
            return False

        def capture_start():
            capture(screenshot_paths[0])
            toggle_center()
            GLib.timeout_add(260, capture_center)
            return False

        GLib.timeout_add(500, capture_start)
    dialog.run()
    dialog.destroy()
