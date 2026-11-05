"""Opt-in ricePlate GTK desktop preview; never claims the XFDesktop surface.

Real desktop entries are only read and rendered. The preview stays a normal
XFWM-managed window: no desktop-type hints, grabs, autostart or file mutations.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from . import plate
from .worker import LatestRequestRunner


def visible_items(view: plate.DesktopSnapshot, settings: plate.DesktopAppearance):
    """Filter display rows, leaving the original snapshot and filesystem intact."""
    if not settings.show_icons:
        return ()
    return tuple(item for item in view.items
                 if settings.show_hidden or not (item.hidden or item.filename.startswith(".")))


def wallpaper_file(style: str, root: Path | None = None) -> Path:
    """Resolve checked-in RiceBowl wallpaper only, not arbitrary user paths."""
    from ..installer import project_root
    from ..rice import STYLES

    directory = root or project_root()
    return directory / "assets/wallpapers" / STYLES[style].wallpaper


def build_window(style: str, *, folder: Path | None = None,
                 config_root: Path | None = None):
    """Create a normal interactive window (caller owns GTK's main loop)."""
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

    preferences = plate.appearance(style, config_root=config_root)
    theme = Gtk.IconTheme.get_default()
    family = preferences.family
    styles = {
        "win98": ("#008080", "#c0c0c0", "#000080", 0),
        "winxp": ("#194da1", "#f4f7fe", "#316ac5", 5),
        "win7": ("#1e355b", "#f7fbff", "#275b99", 6),
        "win10": ("#101014", "#f1f1f1", "#0078d7", 0),
        "chromeos": ("#e7e9f8", "#242841", "#4b66d7", 14),
        "frutiger": ("#0d658e", "#ffffff", "#1388a7", 12),
        "macos": ("#202a37", "#ffffff", "#637eae", 11),
    }
    fallback, text_color, accent, radius = styles[family]
    css = Gtk.CssProvider()
    css.load_from_data((
        f"#riceplate-preview {{ background: {fallback}; }}\n"
        "#riceplate-preview iconview, #riceplate-preview scrolledwindow, "
        "#riceplate-preview viewport { background: transparent; border: none; }\n"
        f"#riceplate-preview iconview {{ color: {text_color}; "
        "font-family: Sans; font-size: 12px; }}\n"
        f"#riceplate-preview iconview:selected {{ background: {accent}; "
        f"border-radius: {radius}px; }}\n"
        "#riceplate-preview .riceplate-footer { background: #18212c; "
        "color: #f3f6fa; padding: 9px 12px; }\n"
        "#riceplate-preview .riceplate-hint { background: rgba(0,0,0,0.68); "
        "color: white; padding: 14px; border-radius: 8px; }\n"
        "#riceplate-preview .riceplate-status { color: #ebf1f8; }\n"
    ).encode("utf-8"))
    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(screen, css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    window = Gtk.Window(title=f"ricePlate · {style} · Desktop preview")
    window.set_name("riceplate-preview")
    window.set_default_size(1120, 720)
    window.set_size_request(640, 420)
    window.set_position(Gtk.WindowPosition.CENTER)

    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    window.add(root)
    intro = Gtk.Label(xalign=0)
    intro.set_text("ricePlate preview · XFDesktop still owns your desktop. No files or global settings are changed.")
    intro.set_line_wrap(True)
    intro.set_margin_start(14)
    intro.set_margin_end(14)
    intro.set_margin_top(9)
    intro.set_margin_bottom(9)
    root.pack_start(intro, False, False, 0)

    canvas = Gtk.Overlay()
    canvas.set_hexpand(True)
    canvas.set_vexpand(True)
    root.pack_start(canvas, True, True, 0)
    image = Gtk.DrawingArea()
    image.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    canvas.add(image)

    try:
        wallpaper = GdkPixbuf.Pixbuf.new_from_file(str(wallpaper_file(style)))
    except (OSError, GLib.Error):
        wallpaper = None
    cache = {"size": None, "pixbuf": None}

    def draw_background(widget, context):
        width, height = widget.get_allocated_width(), widget.get_allocated_height()
        if wallpaper is None or width <= 0 or height <= 0:
            context.set_source_rgb(*(int(fallback[i:i + 2], 16) / 255 for i in (1, 3, 5)))
            context.paint()
            return False
        if cache["size"] != (width, height):
            scale = max(width / wallpaper.get_width(), height / wallpaper.get_height())
            scaled = wallpaper.scale_simple(max(1, round(wallpaper.get_width() * scale)),
                                            max(1, round(wallpaper.get_height() * scale)),
                                            GdkPixbuf.InterpType.BILINEAR)
            cache.update(size=(width, height), pixbuf=scaled)
        scaled = cache["pixbuf"]
        Gdk.cairo_set_source_pixbuf(context, scaled,
                                   (width - scaled.get_width()) / 2,
                                   (height - scaled.get_height()) / 2)
        context.paint()
        return False

    image.connect("draw", draw_background)
    store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, str)
    icons = Gtk.IconView.new_with_model(store)
    icons.set_pixbuf_column(0)
    icons.set_text_column(1)
    icons.set_selection_mode(Gtk.SelectionMode.SINGLE)
    icons.set_item_width(105)
    icons.set_row_spacing(12)
    icons.set_column_spacing(8)
    icons.set_margin(13)
    icons.get_accessible().set_name("Real Desktop files")
    icons.set_has_tooltip(True)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_size_request(260, -1)
    scroll.add(icons)
    scroller_holder = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    scroller_holder.set_halign(Gtk.Align.START if preferences.placement == "left" else Gtk.Align.END)
    scroller_holder.set_valign(Gtk.Align.FILL)
    scroller_holder.pack_start(scroll, False, False, 0)
    canvas.add_overlay(scroller_holder)

    hint = Gtk.Label(label="Reading Desktop…")
    hint.get_style_context().add_class("riceplate-hint")
    hint.set_halign(Gtk.Align.CENTER)
    hint.set_valign(Gtk.Align.CENTER)
    hint.set_margin_start(12)
    hint.set_margin_end(12)
    hint.set_line_wrap(True)
    canvas.add_overlay(hint)

    footer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
    footer.get_style_context().add_class("riceplate-footer")
    root.pack_end(footer, False, False, 0)
    controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    footer.pack_start(controls, False, False, 0)
    size = Gtk.ComboBoxText()
    for pixels in (32, 40, 48, 56, 64, 80, 96):
        size.append(str(pixels), f"{pixels}px")
    if preferences.icon_size not in (32, 40, 48, 56, 64, 80, 96):
        size.append(str(preferences.icon_size), f"{preferences.icon_size}px")
    size.set_active_id(str(preferences.icon_size))
    size.get_accessible().set_name("Desktop icon size")
    controls.pack_start(Gtk.Label(label="Icons:"), False, False, 0)
    controls.pack_start(size, False, False, 0)
    placement = Gtk.ComboBoxText()
    placement.append("left", "Left")
    placement.append("right", "Right")
    placement.set_active_id(preferences.placement)
    placement.get_accessible().set_name("Desktop icon alignment")
    controls.pack_start(placement, False, False, 0)
    show_icons = Gtk.CheckButton(label="Show icons")
    show_icons.set_active(preferences.show_icons)
    controls.pack_start(show_icons, False, False, 0)
    hidden = Gtk.CheckButton(label="Hidden files")
    hidden.set_active(preferences.show_hidden)
    controls.pack_start(hidden, False, False, 0)
    save = Gtk.Button(label="Save for this rice")
    save.get_accessible().set_name("Save ricePlate layout for this rice")
    controls.pack_end(save, False, False, 0)
    refresh = Gtk.Button(label="Refresh")
    controls.pack_end(refresh, False, False, 0)
    status = Gtk.Label(label="Desktop items are read-only in preview mode.", xalign=0)
    status.set_line_wrap(True)
    status.get_style_context().add_class("riceplate-status")
    footer.pack_end(status, False, False, 0)

    runner = LatestRequestRunner(GLib.idle_add, workers=1)
    state = {"snapshot": None, "closed": False}

    def chosen_appearance():
        return plate.DesktopAppearance(style, family, int(size.get_active_id()),
                                       placement.get_active_id(), show_icons.get_active(),
                                       hidden.get_active())

    def icon_for(item, pixels):
        fallback_name = {"directory": "folder", "link": "emblem-symbolic-link",
                         "launcher": "application-x-executable", "file": "text-x-generic"}
        name = item.icon_name or fallback_name.get(item.kind, "text-x-generic")
        if not re.fullmatch(r"[\w.-]{1,120}", name, flags=re.ASCII):
            name = fallback_name.get(item.kind, "text-x-generic")
        for candidate in (name, "text-x-generic"):
            try:
                if theme is not None:
                    return theme.load_icon(candidate, pixels, Gtk.IconLookupFlags.FORCE_SIZE)
            except (GLib.Error, OSError):
                continue
        blank = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, pixels, pixels)
        blank.fill(0x667788ff)
        return blank

    def render():
        current = state["snapshot"]
        if current is None:
            return
        selected = chosen_appearance()
        store.clear()
        visible = visible_items(current, selected)
        icons.set_item_width(max(92, selected.icon_size + 46))
        scroller_holder.set_halign(Gtk.Align.START if selected.placement == "left" else Gtk.Align.END)
        if not selected.show_icons:
            hint.set_text("Desktop icons are hidden in this rice. Enable Show icons to preview them.")
        elif not current.exists:
            hint.set_text("Your Desktop folder does not exist. ricePlate will not create it automatically.")
        elif not visible:
            hint.set_text("No visible Desktop items. Add a file using your file manager, then Refresh.")
        else:
            hint.hide()
        for item in visible:
            title = plate._clean(item.display_name or item.filename, 120) or "Untitled"
            store.append([icon_for(item, selected.icon_size), title, item.path, item.kind])
        if not visible:
            hint.show()
        suffix = " · listing truncated at 256" if current.truncated else ""
        status.set_text(f"{len(visible)} of {len(current.items)} Desktop entries shown{suffix} · Preview only")

    def refresh_files(_button=None):
        status.set_text("Reading Desktop…")

        def ready(response):
            if state["closed"]:
                return
            if response.error:
                status.set_text("Could not read Desktop: " + response.error[:160])
                hint.set_text("Desktop is unavailable. Check its permissions, then Refresh.")
                hint.show()
                return
            state["snapshot"] = response.value
            render()

        runner.submit("desktop", lambda: plate.snapshot(folder=folder, limit=256), ready)

    def selected_row():
        selection = icons.get_selected_items()
        if not selection:
            return None
        iterator = store.get_iter(selection[0])
        return store.get_value(iterator, 2), store.get_value(iterator, 3)

    def open_item(_widget=None, _path=None):
        row = selected_row()
        if row is None:
            status.set_text("Select a Desktop item first.")
            return
        path, kind = row
        target = Path(path)
        # The directory may have changed after the snapshot was taken. Never
        # knowingly follow a symlink that replaced a previously normal item.
        if kind == "link" or target.is_symlink():
            status.set_text("Symbolic links are not launched by the preview. Open them in your file manager.")
            return
        if not target.exists():
            status.set_text("The selected Desktop item no longer exists. Refresh to update the list.")
            return
        try:
            Gio.AppInfo.launch_default_for_uri(target.as_uri(), None)
            status.set_text("Open request sent to the default application.")
        except (OSError, GLib.Error) as exc:
            status.set_text("Could not open the selected item: " + str(exc)[:160])

    def open_folder(_widget=None):
        current = state["snapshot"]
        if current is None or not current.exists:
            status.set_text("Desktop folder is unavailable.")
            return
        try:
            Gio.AppInfo.launch_default_for_uri(Path(current.folder).as_uri(), None)
        except (OSError, GLib.Error) as exc:
            status.set_text("Could not open Desktop folder: " + str(exc)[:160])

    def menu(event=None):
        popup = Gtk.Menu()
        for text, callback in (("Open selected", open_item),
                               ("Open Desktop folder", open_folder),
                               ("Refresh", refresh_files)):
            action = Gtk.MenuItem(label=text)
            action.connect("activate", callback)
            action.set_sensitive(text != "Open selected" or selected_row() is not None)
            popup.append(action)
        popup.show_all()
        if event is None:
            popup.popup_at_widget(icons, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)
        else:
            popup.popup_at_pointer(event)

    def button_press(_widget, event):
        if event.button != 3:
            return False
        path = icons.get_path_at_pos(int(event.x), int(event.y))
        if path is not None:
            icons.unselect_all()
            icons.select_path(path)
        menu(event)
        return True

    def background_press(_widget, event):
        if event.button != 3:
            return False
        icons.unselect_all()
        menu(event)
        return True

    def on_key(_widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            open_item()
            return True
        if event.keyval == Gdk.KEY_Menu or (event.keyval == Gdk.KEY_F10
                                             and event.state & Gdk.ModifierType.SHIFT_MASK):
            menu()
            return True
        return False

    def save_settings(_button):
        selected = chosen_appearance()
        try:
            plate.save_appearance(style, config_root=config_root,
                                  icon_size=selected.icon_size,
                                  placement=selected.placement,
                                  show_icons=selected.show_icons,
                                  show_hidden=selected.show_hidden)
            status.set_text("Saved layout for " + style + ". XFDesktop is unchanged.")
        except (OSError, ValueError) as exc:
            status.set_text("Could not save layout: " + str(exc)[:160])

    def close(_window):
        state["closed"] = True
        runner.close()

    icons.connect("item-activated", open_item)
    icons.connect("button-press-event", button_press)
    image.connect("button-press-event", background_press)
    icons.connect("key-press-event", on_key)
    size.connect("changed", lambda *_: render())
    placement.connect("changed", lambda *_: render())
    show_icons.connect("toggled", lambda *_: render())
    hidden.connect("toggled", lambda *_: render())
    save.connect("clicked", save_settings)
    refresh.connect("clicked", refresh_files)
    window.connect("destroy", close)
    window.show_all()
    refresh_files()
    return window


def run(style: str) -> int:
    """Explicit preview only. Never starts when a rice is applied or at login."""
    if not os.environ.get("DISPLAY"):
        print("ricePlate preview needs an X11 graphical session.", file=sys.stderr)
        return 1
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk

    ready, _args = Gtk.init_check([])
    if not ready:
        print("Cannot initialize GTK for ricePlate preview.", file=sys.stderr)
        return 1
    window = build_window(style)
    window.connect("destroy", lambda *_: Gtk.main_quit())
    Gtk.main()
    return 0
