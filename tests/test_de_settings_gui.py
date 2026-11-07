"""Actual GTK constructor/navigation smoke for the on-demand RiceSpice GUI."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.de import settings


class SettingsGuiTests(unittest.TestCase):
    def test_all_sections_render_without_hardware_services_or_side_effects(self):
        try:
            Gtk, Gdk, GLib = settings._gtk_modules()
        except (ImportError, ValueError):
            self.skipTest("GTK introspection typelib is not installed")
        if not Gtk.init_check([])[0]:
            self.skipTest("GTK display is unavailable")
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.dict("os.environ", {"XDG_CONFIG_HOME": directory}), \
                mock.patch("macrice.de.settings_backend.wifi_state", return_value=True), \
                mock.patch("macrice.de.settings_backend.bluetooth_snapshot", return_value={
                    "powered": True, "adapter": "/org/bluez/hci0", "devices": [],
                }), \
                mock.patch("macrice.de.audio_devices.inspect", return_value={
                    "outputs": [{"name": "output.1", "description": "USB speakers", "default": True}],
                    "inputs": [{"name": "input.1", "description": "USB mic", "default": True}],
                }), \
                mock.patch("macrice.de.settings_backend.external_tool", return_value=None):
            Path(directory).chmod(0o700)
            window = settings.RiceSpiceWindow(Gtk, Gdk, GLib)
            self.assertTrue(window.window.get_visible())
            self.assertEqual(len(window.nav_buttons), 9)
            for name, _title, _description in settings.SECTIONS:
                window.show_page(name)
                self.assertEqual(window.page, name)
                self.assertTrue(window.nav_buttons[name].get_active())
            GLib.timeout_add(160, lambda: (window.window.destroy(), False)[1])
            Gtk.main()
            self.assertTrue(window.closed)


if __name__ == "__main__":
    unittest.main()
