"""Run with dbus-run-session + Xvfb in CI to exercise real GTK widgets."""

import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest import mock


class FrutigerCalendarGtkTests(unittest.TestCase):
    def test_local_calendar_opens_with_today_and_can_reset_selection(self):
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        from macrice.frutiger_calendar import AquaCalendar

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("Native GTK display unavailable; Xvfb CI supplies one")
        window = Gtk.Window()
        anchor = Gtk.Button(label="Clock")
        window.add(anchor)
        window.show_all()
        try:
            popup = AquaCalendar(anchor, Gtk)
            popup.show()
            year, month, day = popup.calendar.get_date()
            now = datetime.now().astimezone()
            self.assertEqual((year, month + 1, day), (now.year, now.month, now.day))
            popup.calendar.select_day(1)
            popup.reset_today()
            self.assertEqual(popup.calendar.get_date(), (now.year, now.month - 1, now.day))
            self.assertTrue(popup.popover.get_visible())
        finally:
            window.destroy()

    def test_wpa_flyout_uses_a_masked_entry_cleared_before_dispatch(self):
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
        from macrice.frutiger_flyouts import AquaFlyouts

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("Native GTK display unavailable; Xvfb CI supplies one")
        window = Gtk.Window()
        anchor = Gtk.Button(label="Network")
        window.add(anchor)
        runner = mock.Mock()
        shell = SimpleNamespace(
            frutiger_controller=runner, aqua_bluetooth_button=anchor,
            _status_widgets={"network": (anchor, None, None)},
            _class=lambda widget, css: widget,
            _icon=lambda name, size: Gtk.Image.new_from_icon_name(name, size),
        )
        window.show_all()
        try:
            flyout = AquaFlyouts(shell, Gtk)
            popup = flyout._build("network")
            flyout.popovers["network"] = popup
            popup.show_all()
            popup.popup()
            flyout._password_prompt("Aqua Network")
            details = flyout.details["network"]
            entries = [item for item in details.get_children() if isinstance(item, Gtk.Entry)]
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertFalse(entry.get_visibility())
            entry.set_text("supersafepassphrase")
            connect = next(button for row in details.get_children()
                           if isinstance(row, Gtk.Box)
                           for button in row.get_children()
                           if isinstance(button, Gtk.Button) and button.get_label() == "Connect")
            connect.clicked()
            self.assertEqual(entry.get_text(), "")
            runner.submit.assert_called_once()
            self.assertEqual(runner.submit.call_args.args[0], "aqua-write-network")
        finally:
            window.destroy()

    def test_connected_locations_popup_constructs_real_scrolled_gtk_controls(self):
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gio", "2.0")
        from gi.repository import Gtk, Gio
        from macrice.frutiger_drives import AquaDrives

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("Native GTK display unavailable; Xvfb CI supplies one")
        window = Gtk.Window()
        anchor = Gtk.Button(label="Drives")
        window.add(anchor)
        window.show_all()
        shell = SimpleNamespace(aqua_drives_button=anchor, bar=window, _open_uri=mock.Mock())
        popup = None
        try:
            popup = AquaDrives(shell, Gtk, Gio)
            popup.show()
            self.assertTrue(popup.popover.get_visible())
            self.assertTrue(popup.handlers)
            popup.popover.popdown()
            popup._on_closed()  # Also safe if the signal already disconnected.
            self.assertFalse(popup.handlers)
        finally:
            if popup is not None:
                popup.close()
            window.destroy()


if __name__ == "__main__":
    unittest.main()
