"""On-demand GTK3 desktop preview using widgets, without cairo bindings."""

from __future__ import annotations

import os
import threading


PREVIEW_STYLE = b"""
.rice-topbar { background: rgba(17, 22, 34, .92); padding: 7px 12px; }
.rice-topbar label { color: #f5f7fb; font-size: 12px; }
.rice-dock { background: rgba(24, 31, 48, .79); border-radius: 17px; padding: 10px; }
.rice-dock-icon { background: #a6c6ec; color: #152133; border-radius: 10px;
  font-size: 18px; font-weight: bold; min-width: 45px; min-height: 43px; }
.rice-panel { background: rgba(18, 24, 37, .94); color: #f5f7fb;
  border-radius: 14px; padding: 15px; }
.rice-panel label { color: #f5f7fb; }
.rice-panel-title { font-size: 16px; font-weight: bold; }
.rice-search { background: rgba(55, 66, 86, .91); color: #b2bacb;
  padding: 11px; border-radius: 10px; }
.rice-row { background: rgba(40, 51, 69, .78); padding: 7px 10px;
  border-radius: 9px; }
.rice-app-icon { background: #647b9e; color: white; border-radius: 6px;
  min-width: 29px; min-height: 29px; }
.rice-small { color: #b5c0d2; font-size: 11px; }
"""


def open_preview(parent=None):
    """Open the full desktop illustration and a confirmed apply/restore flow."""
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

    from .installer import project_root
    from .rice import STYLES, apply, restore

    provider = Gtk.CssProvider()
    provider.load_from_data(PREVIEW_STYLE)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )
    source = project_root() / "assets/wallpapers"
    images = {
        key: GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(source / style.wallpaper), 960, 540, False,
        ) for key, style in STYLES.items()
    }

    def styled(widget, css):
        widget.get_style_context().add_class(css)
        return widget

    def label(value, css=None):
        widget = Gtk.Label(label=value, xalign=0)
        return styled(widget, css) if css else widget

    def panel(name, rows, width):
        box = styled(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "rice-panel")
        box.set_size_request(width, -1)
        box.pack_start(label(name, "rice-panel-title"), False, False, 0)
        for title, is_search in rows:
            if is_search:
                box.pack_start(label(title, "rice-search"), False, False, 0)
                continue
            row = styled(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10), "rice-row")
            icon = styled(Gtk.Label(label=title[0]), "rice-app-icon")
            row.pack_start(icon, False, False, 0)
            row.pack_start(label(title), True, True, 0)
            box.pack_start(row, False, False, 0)
        return box

    class RicePreview(Gtk.Window):
        def __init__(self):
            super().__init__(title="MacRice · Complete Desktop", transient_for=parent)
            self.set_name("macrice-window")
            self.set_default_size(995, 680)
            self.set_resizable(True)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_border_width(15)
            self._style = "night"
            self._mode = "Overview"
            self._busy = False

            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.add(outer)
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            outer.pack_start(header, False, False, 0)
            header.pack_start(label("Complete desktop preview", "section-title"), True, True, 0)

            styles = Gtk.ComboBoxText()
            for key, style in STYLES.items():
                styles.append(key, style.name)
            styles.set_active_id(self._style)
            styles.connect("changed", self._change_style)
            styles.set_tooltip_text("Preview one of the two original wallpapers and matching Rice presets")
            header.pack_start(styles, False, False, 0)

            modes = Gtk.ComboBoxText()
            for mode in ("Overview", "Desktop", "Apps", "Control Center"):
                modes.append_text(mode)
            modes.set_active(0)
            modes.connect("changed", self._change_mode)
            header.pack_start(modes, False, False, 0)

            # A real wallpaper behind illustrative native GTK panels: no browser,
            # Cairo foreign bindings, rendering timer or hidden background daemon.
            canvas = Gtk.Overlay()
            outer.pack_start(canvas, True, True, 0)
            self.wallpaper = Gtk.Image.new_from_pixbuf(images[self._style])
            canvas.add(self.wallpaper)

            topbar = styled(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=17), "rice-topbar")
            topbar.set_halign(Gtk.Align.FILL)
            topbar.set_valign(Gtk.Align.START)
            for name in ("◉", "Applications", "Files", "View"):
                topbar.pack_start(label(name), False, False, 0)
            topbar.pack_end(label("12:42"), False, False, 0)
            topbar.pack_end(label("Network   ·   Audio"), False, False, 0)
            canvas.add_overlay(topbar)

            dock = styled(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9), "rice-dock")
            dock.set_halign(Gtk.Align.CENTER)
            dock.set_valign(Gtk.Align.END)
            dock.set_margin_bottom(14)
            for initial in ("F", "W", ">_", "M", "S", "+"):
                dock.pack_start(styled(Gtk.Label(label=initial), "rice-dock-icon"), False, False, 0)
            canvas.add_overlay(dock)

            self.menu = panel("Applications", [("Search apps", True)] + [
                (name, False) for name in ("Files", "Browser", "Terminal", "Settings", "Editor", "Music")
            ], 285)
            self.menu.set_halign(Gtk.Align.START)
            self.menu.set_valign(Gtk.Align.START)
            self.menu.set_margin_start(27)
            self.menu.set_margin_top(53)
            canvas.add_overlay(self.menu)

            self.control = panel("Control Center", [
                ("Wi-Fi", False), ("Bluetooth", False), ("Volume", False),
                ("Brightness", False), ("Quick Actions", False),
            ], 275)
            self.control.set_halign(Gtk.Align.END)
            self.control.set_valign(Gtk.Align.START)
            self.control.set_margin_end(27)
            self.control.set_margin_top(53)
            canvas.add_overlay(self.control)

            explanation = label(
                "Illustrative preview — your actual app icons, screens and live desktop may differ.",
                "muted",
            )
            explanation.set_line_wrap(True)
            outer.pack_start(explanation, False, False, 0)

            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            outer.pack_start(actions, False, False, 0)
            self.apply_button = Gtk.Button(label="Apply complete Rice")
            self.apply_button.get_style_context().add_class("suggested-action")
            self.apply_button.connect("clicked", lambda _button: self._confirm(True))
            actions.pack_start(self.apply_button, False, False, 0)
            self.restore_button = Gtk.Button(label="Restore previous desktop")
            self.restore_button.connect("clicked", lambda _button: self._confirm(False))
            actions.pack_start(self.restore_button, False, False, 0)
            self.feedback = label("Nothing changes until you confirm Apply.", "muted")
            self.feedback.set_line_wrap(True)
            outer.pack_start(self.feedback, False, False, 0)

        def _change_style(self, combo):
            self._style = combo.get_active_id() or "night"
            self.wallpaper.set_from_pixbuf(images[self._style])

        def _change_mode(self, combo):
            self._mode = combo.get_active_text() or "Overview"
            self._update_panels()

        def _update_panels(self):
            self.menu.set_visible(self._mode in ("Overview", "Apps"))
            self.control.set_visible(self._mode in ("Overview", "Control Center"))

        def _confirm(self, applying):
            if self._busy:
                return
            detail = (
                "This updates GTK, window borders, icons, cursor, fonts, Plank and XFCE wallpaper. "
                "Missing themes stop the process before any change. Previous values are backed up."
                if applying else
                "Restore previous XFCE, Plank and app theme values. If you changed them since applying, "
                "MacRice will stop rather than overwrite your newer choices."
            )
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text="Apply this complete XFCE Rice?" if applying else "Restore the previous desktop?",
            )
            dialog.format_secondary_text(detail)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Apply" if applying else "Restore", Gtk.ResponseType.OK)
            accepted = dialog.run() == Gtk.ResponseType.OK
            dialog.destroy()
            if not accepted:
                return
            self._busy = True
            self.apply_button.set_sensitive(False)
            self.restore_button.set_sensitive(False)
            self.feedback.set_text("Working… saving original settings before changes.")
            selected_style = self._style

            def worker():
                try:
                    backup = apply(selected_style) if applying else restore()
                    result = ("Rice applied. Backup: " if applying else "Desktop restored. Backup: ") + str(backup)
                except Exception as exc:
                    result = "No changes completed: " + str(exc)
                GLib.idle_add(self._finished, result)

            threading.Thread(target=worker, daemon=True).start()

        def _finished(self, result):
            self.feedback.set_text(result)
            self._busy = False
            self.apply_button.set_sensitive(True)
            self.restore_button.set_sensitive(True)
            return False

    window = RicePreview()
    if parent is None:
        window.connect("destroy", Gtk.main_quit)
    window.show_all()
    window._update_panels()
    if parent is None:
        Gtk.main()
    return window


def run() -> int:
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("Rice preview needs a GTK desktop session.", file=__import__("sys").stderr)
        return 1
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, Gtk
        from .gui import STYLE

        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        open_preview()
    except (ImportError, ValueError, OSError) as exc:
        print(f"Could not display Rice preview: {exc}", file=__import__("sys").stderr)
        return 1
    return 0
