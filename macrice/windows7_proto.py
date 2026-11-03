"""Interactive, read-only Windows 7-inspired concept for the RiceBowl gallery.

This is not a rice installer. It never launches demo applications, changes the
XFCE panel, installs system assets or writes configuration. The original GTK
widgets are deliberately separate from the eventual real Windows 7 profile.
"""

from __future__ import annotations


SAMPLE_APPS = (
    ("File Manager", "system-file-manager-symbolic"),
    ("Web Browser", "web-browser-symbolic"),
    ("Terminal", "utilities-terminal-symbolic"),
    ("Text Editor", "accessories-text-editor-symbolic"),
    ("Calculator", "accessories-calculator-symbolic"),
    ("Settings", "preferences-system-symbolic"),
)


def matching_apps(query: str) -> tuple[tuple[str, str], ...]:
    needle = query.strip().casefold()
    return tuple(item for item in SAMPLE_APPS if needle in item[0].casefold())


CSS = b"""
.w7-hero, .w7-desktop {
  background-image: linear-gradient(to bottom, #8ad6f3 0%, #408fc9 44%, #164d9e 100%);
  border: 1px solid #5da6e0; border-radius: 12px;
}
.w7-desktop { background-image: none; background-color: transparent; }
.w7-sky-title { color: #ffffff; font-size: 23px; font-weight: bold; }
.w7-sky-small { color: #eaf9ff; font-size: 12px; }
.w7-taskbar {
  background-image: linear-gradient(to bottom, rgba(209,239,255,.70), rgba(24,75,125,.91));
  border-top: 1px solid rgba(255,255,255,.80); padding: 8px 12px;
}
.w7-launcher {
  background-image: linear-gradient(to bottom, #8cdeff, #2181c4);
  border: 1px solid #b4edff; border-radius: 22px;
  color: #ffffff; font-weight: bold; padding: 7px 14px;
  box-shadow: 0 1px 5px rgba(10,45,87,.30);
}
.w7-launcher:hover { background-image: linear-gradient(to bottom, #b9edff, #398fc8); }
.w7-pin { color: #ffffff; font-size: 16px; padding: 4px 12px; }
.w7-clock { color: #ffffff; font-size: 12px; }
.w7-menu {
  background: #e8f2fa; border: 1px solid #79b6df;
  border-radius: 11px; padding: 14px; box-shadow: 0 8px 20px rgba(13,49,87,.32);
}
.w7-menu-title { color: #193a5a; font-size: 16px; font-weight: bold; }
.w7-menu-copy { color: #58738c; font-size: 11px; }
.w7-menu-separator { background: #b1cedf; min-height: 1px; }
.w7-program {
  background: transparent; border: 1px solid transparent;
  border-radius: 6px; color: #173c60; padding: 6px;
  box-shadow: none;
}
.w7-program:hover, .w7-program:focus { background: #d4e9f8; border-color: #a3d1ed; }
.w7-search {
  background: #ffffff; color: #1c405d; border-radius: 6px;
  border: 1px solid #88b8d8; padding: 6px;
}
.w7-preview-note { color: #dceffe; font-size: 12px; }
.w7-prototype-badge { color: #153c5d; font-size: 12px; font-weight: bold; }
.w7-shell { background: #142236; color: #f4faff; }
.w7-heading { color: #f4faff; font-size: 18px; font-weight: bold; }
.w7-intro { color: #bbcede; font-size: 12px; }
.w7-dialog-status { color: #c5d6e9; font-size: 11px; }
"""

_provider = None


def _style(widget, name):
    widget.get_style_context().add_class(name)
    return widget


def install_css(Gtk, Gdk):
    """Install one style provider, even if the preview is opened repeatedly."""
    global _provider
    if _provider is None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        _provider = provider


def teaser(Gtk):
    """Small hero shown when the prototype family is selected in Discover."""
    card = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "w7-hero")
    card.set_size_request(-1, 190)
    card.set_margin_top(0)
    header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    header.set_margin_top(30)
    header.set_margin_start(22)
    header.pack_start(_style(Gtk.Label(label="Windows 7 · Aero-inspired", xalign=0), "w7-sky-title"), False, False, 0)
    header.pack_start(_style(Gtk.Label(label="Interactive Start menu prototype · Preview only", xalign=0),
                             "w7-sky-small"), False, False, 0)
    card.pack_start(header, True, True, 0)
    bar = _style(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16), "w7-taskbar")
    start = _style(Gtk.Label(label="◈  Start"), "w7-clock")
    bar.pack_start(start, False, False, 0)
    for name in ("Files", "Browser", "Terminal"):
        bar.pack_start(_style(Gtk.Label(label=name), "w7-clock"), False, False, 0)
    card.pack_start(bar, False, False, 0)
    return card


def show_dialog(parent, Gtk, Gdk, GLib):
    """Open an interactive desktop concept; it cannot modify the host desktop."""
    from gi.repository import GdkPixbuf
    from .installer import project_root

    install_css(Gtk, Gdk)
    dialog = Gtk.Dialog(title="Windows 7 — RiceBowl prototype", transient_for=parent,
                        flags=Gtk.DialogFlags.MODAL)
    _style(dialog, "w7-shell")
    dialog.set_default_size(920, 680)
    dialog.add_button("Close preview", Gtk.ResponseType.CLOSE)
    _style(dialog.get_action_area(), "w7-shell")
    root = dialog.get_content_area()
    _style(root, "w7-shell")
    root.set_spacing(12)
    root.set_margin_start(16)
    root.set_margin_end(16)
    root.set_margin_top(14)

    heading = Gtk.Label(label="Windows 7-inspired desktop  ·  Early prototype", xalign=0)
    heading.get_style_context().add_class("w7-heading")
    root.pack_start(heading, False, False, 0)
    root.pack_start(_style(Gtk.Label(label="Explore the Start menu and search. Nothing here installs or launches software.",
                                      xalign=0), "w7-intro"), False, False, 0)

    overlay = Gtk.Overlay()
    overlay.set_size_request(-1, 490)
    root.pack_start(overlay, True, True, 0)
    scenery = Gtk.Overlay()
    wallpaper = project_root() / "assets/wallpapers/aero-meadow.jpg"
    if wallpaper.is_file():
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(wallpaper), 920, 490, False)
        background_image = Gtk.Image.new_from_pixbuf(pixbuf)
        background_image.set_halign(Gtk.Align.FILL)
        background_image.set_valign(Gtk.Align.FILL)
        scenery.add(background_image)
    background = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "w7-desktop")
    background.set_border_width(0)
    if wallpaper.is_file():
        scenery.add_overlay(background)
        overlay.add(scenery)
    else:
        overlay.add(background)

    desktop = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11)
    desktop.set_margin_top(25)
    desktop.set_margin_start(24)
    for title, icon_name in (("Computer", "computer-symbolic"),
                             ("Documents", "folder-documents-symbolic"),
                             ("Recycle Bin", "user-trash-symbolic")):
        shortcut = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        shortcut.set_halign(Gtk.Align.START)
        shortcut.pack_start(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG), False, False, 0)
        shortcut.pack_start(_style(Gtk.Label(label=title), "w7-sky-small"), False, False, 0)
        desktop.pack_start(shortcut, False, False, 0)
    background.pack_start(desktop, True, True, 0)

    taskbar = _style(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13), "w7-taskbar")
    taskbar.set_margin_start(1)
    taskbar.set_margin_end(1)
    taskbar.set_margin_bottom(1)
    background.pack_start(taskbar, False, False, 0)
    start_button = _style(Gtk.Button(), "w7-launcher")
    start_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    logo = project_root() / "assets/aero-penguin.svg"
    if logo.is_file():
        start_content.pack_start(Gtk.Image.new_from_pixbuf(
            GdkPixbuf.Pixbuf.new_from_file_at_scale(str(logo), 24, 24, True)), False, False, 0)
    start_content.pack_start(Gtk.Label(label="Start"), False, False, 0)
    start_button.add(start_content)
    start_button.get_accessible().set_name("Toggle Start menu")
    taskbar.pack_start(start_button, False, False, 0)
    for icon in ("system-file-manager-symbolic", "web-browser-symbolic", "utilities-terminal-symbolic"):
        tile = _style(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.LARGE_TOOLBAR), "w7-pin")
        taskbar.pack_start(tile, False, False, 0)
    taskbar.pack_start(Gtk.Box(), True, True, 0)
    taskbar.pack_start(_style(Gtk.Label(label=GLib.DateTime.new_now_local().format("%H:%M")),
                              "w7-clock"), False, False, 0)

    menu = _style(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10), "w7-menu")
    menu.set_size_request(325, 376)
    menu.set_halign(Gtk.Align.START)
    menu.set_valign(Gtk.Align.END)
    menu.set_margin_start(16)
    menu.set_margin_bottom(57)
    overlay.add_overlay(menu)
    menu.pack_start(_style(Gtk.Label(label="Start", xalign=0), "w7-menu-title"), False, False, 0)
    menu.pack_start(_style(Gtk.Label(label="Sample programs", xalign=0), "w7-menu-copy"), False, False, 0)
    search = _style(Gtk.SearchEntry(), "w7-search")
    search.set_placeholder_text("Search programs and files")
    search.get_accessible().set_name("Search prototype programs")
    menu.pack_start(search, False, False, 0)
    results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    menu.pack_start(results, True, True, 0)

    status = _style(Gtk.Label(label="Preview-only · No desktop settings changed.", xalign=0),
                    "w7-dialog-status")
    root.pack_start(status, False, False, 0)

    def populate(*_args):
        for child in results.get_children():
            results.remove(child)
        matches = matching_apps(search.get_text())
        if not matches:
            results.pack_start(_style(Gtk.Label(label="No sample programs found.", xalign=0),
                                      "w7-menu-copy"), False, False, 0)
        for name, icon_name in matches:
            btn = _style(Gtk.Button(), "w7-program")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.pack_start(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU), False, False, 0)
            row.pack_start(Gtk.Label(label=name, xalign=0), True, True, 0)
            btn.add(row)
            btn.get_accessible().set_name("Sample app: " + name)
            btn.connect("clicked", lambda _button, item=name: status.set_text(
                f"{item} is a visual example — nothing was launched."))
            results.pack_start(btn, False, False, 0)
        results.show_all()

    search.connect("search-changed", populate)
    populate()

    def toggle(_button):
        menu.set_visible(not menu.get_visible())
        if menu.get_visible():
            search.grab_focus()

    start_button.connect("clicked", toggle)
    dialog.show_all()
    dialog.run()
    dialog.destroy()
