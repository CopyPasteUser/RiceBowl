"""Capture actual rendered MacMenu windows in an active GTK/Xfce session.

Example: /usr/bin/python3 capture_screenshot.py --theme dark
"""

import argparse
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from macmenu.ui import PALETTES, LauncherWindow


class CaptureApplication(Gtk.Application):
    def __init__(self, theme: str, output: Path, settings: bool = False, settings_page: str = "appearance"):
        super().__init__(application_id="io.github.xfce.MacMenuCapture")
        self.theme = theme
        self.output = output
        self.settings = settings
        self.settings_page = settings_page
        self.window = None
        self._expanded = False

    def do_activate(self):
        self.window = LauncherWindow(self)
        self.window.settings["theme"] = self.theme
        self.window.apply_theme()
        self.window.render()
        self.window.show_launcher()
        if self.settings:
            GLib.idle_add(self.window.open_preferences)
        GLib.timeout_add(600, self.capture)

    def capture(self) -> bool:
        target = self.window
        if self.settings:
            dialogs = [
                widget for widget in Gtk.Window.list_toplevels()
                if isinstance(widget, Gtk.Dialog)
                and widget.get_title() == "MacMenu Preferences"
            ]
            if not dialogs:
                return True
            target = dialogs[0]
            if not self._expanded:
                # Capture the native dialog at a readable size; on shorter
                # screens users can still scroll its content normally.
                target.resize(510, 532)
                for switcher in target.get_children():
                    self.activate_settings_page(switcher)
                self._expanded = True
                return True
        window = target.get_window()
        if window is None:
            return True
        width, height = target.get_size()
        image = Gdk.pixbuf_get_from_window(window, 0, 0, width, height)
        if image is None:
            raise RuntimeError("Could not capture the GTK window")
        self.output.parent.mkdir(parents=True, exist_ok=True)
        image.savev(str(self.output), "png", [], [])
        print(f"Screenshot saved: {self.output}")
        if self.settings:
            target.response(Gtk.ResponseType.CLOSE)
        self.window.destroy()
        self.quit()
        return False

    def activate_settings_page(self, widget: Gtk.Widget) -> bool:
        if isinstance(widget, Gtk.Stack) and widget.get_child_by_name(self.settings_page):
            widget.set_visible_child_name(self.settings_page)
            return True
        if isinstance(widget, Gtk.Container):
            return any(self.activate_settings_page(child) for child in widget.get_children())
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--theme", choices=tuple(PALETTES), default="dark")
    parser.add_argument("--settings", action="store_true", help="Capture preferences instead of launcher")
    parser.add_argument("--settings-page", choices=("appearance", "privacy"), default="appearance")
    parser.add_argument("--output", type=Path, default=Path("screenshots/macmenu-midnight.png"))
    args = parser.parse_args()
    return CaptureApplication(args.theme, args.output, args.settings, args.settings_page).run([])


if __name__ == "__main__":
    raise SystemExit(main())
