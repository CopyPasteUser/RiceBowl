"""Native ricePlate preview checks; run under dbus-run-session / Xvfb in CI."""

import os
import tempfile
import time
import unittest
from pathlib import Path


@unittest.skipUnless(os.environ.get("DISPLAY"), "Needs an X11 desktop")
class RicePlatePreviewGuiTests(unittest.TestCase):
    def test_preview_is_a_normal_window_with_real_icon_rows_and_saved_layout(self):
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk

        ready, _ = Gtk.init_check([])
        if not ready:
            self.skipTest("GTK display unavailable")
        from macrice.riceware import plate
        from macrice.riceware.plate_preview import build_window

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            desktop = root / "Desktop"
            desktop.mkdir()
            (desktop / "Visible.txt").write_text("hello", encoding="utf-8")
            (desktop / ".Hidden.txt").write_text("private", encoding="utf-8")
            window = build_window("winxp", folder=desktop, config_root=root / "config")
            try:
                self.assertIsInstance(window, Gtk.Window)
                self.assertEqual(window.get_name(), "riceplate-preview")

                def walk(widget):
                    yield widget
                    if isinstance(widget, Gtk.Container):
                        for child in widget.get_children():
                            yield from walk(child)

                widget_list = tuple(walk(window))
                icon_views = [widget for widget in widget_list if isinstance(widget, Gtk.IconView)]
                self.assertEqual(len(icon_views), 1)
                icon_view = icon_views[0]
                deadline = time.monotonic() + 3
                while len(icon_view.get_model()) != 1 and time.monotonic() < deadline:
                    while GLib.MainContext.default().pending():
                        GLib.MainContext.default().iteration(False)
                    time.sleep(0.01)
                self.assertEqual(len(icon_view.get_model()), 1)
                self.assertEqual(icon_view.get_model()[0][1], "Visible.txt")

                # Gio directory events must refresh without pressing the button
                # or running a periodic polling timer.
                created = desktop / "Just-added.txt"
                created.write_text("new", encoding="utf-8")
                deadline = time.monotonic() + 5
                while len(icon_view.get_model()) != 2 and time.monotonic() < deadline:
                    while GLib.MainContext.default().pending():
                        GLib.MainContext.default().iteration(False)
                    time.sleep(0.01)
                self.assertEqual(len(icon_view.get_model()), 2)
                created.unlink()
                deadline = time.monotonic() + 5
                while len(icon_view.get_model()) != 1 and time.monotonic() < deadline:
                    while GLib.MainContext.default().pending():
                        GLib.MainContext.default().iteration(False)
                    time.sleep(0.01)
                self.assertEqual(len(icon_view.get_model()), 1)

                choices = [widget for widget in widget_list if isinstance(widget, Gtk.ComboBoxText)]
                self.assertEqual(len(choices), 2)
                choices[0].set_active_id("64")
                buttons = [widget for widget in widget_list if isinstance(widget, Gtk.Button)]
                saved = next(widget for widget in buttons if widget.get_label() == "Save for this rice")
                saved.clicked()
                self.assertEqual(plate.appearance("winxp", config_root=root / "config").icon_size, 64)
            finally:
                window.destroy()


if __name__ == "__main__":
    unittest.main()
