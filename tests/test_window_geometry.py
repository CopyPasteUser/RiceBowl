"""Cross-rice geometry persistence, recovery and debounced GTK lifecycle."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from macrice import window_geometry as geometry


class WindowGeometryTests(unittest.TestCase):
    def test_secure_file_roundtrip_and_unknown_payloads(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "window.json"
            role = "ricebowl-aqua-settings"
            self.assertIsNone(geometry.load(role, path=path))
            value = geometry.WindowGeometry(-450, 50, 750, 600)
            geometry.save(role, value, path=path)
            self.assertEqual(geometry.load(role, path=path), value)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            payload = path.read_bytes()
            with self.assertRaises(ValueError):
                geometry.save(role, geometry.WindowGeometry(10, 10, 5, 5), path=path)
            self.assertEqual(path.read_bytes(), payload)
            path.write_text('{"version":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                geometry.save(role, value, path=path)
            self.assertEqual(json.loads(path.read_text())["version"], 2)

    def test_symlink_and_untrusted_roles_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "target.json"
            target.write_text("never change", encoding="utf-8")
            link = Path(root) / "link.json"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                geometry.load("ricebowl-aqua-settings", path=link)
            with self.assertRaises(ValueError):
                geometry.save("ricebowl-aqua-settings",
                              geometry.WindowGeometry(1, 1, 400, 350), path=link)
            self.assertEqual(target.read_text(), "never change")
        for role in ("../../etc/passwd", "", "ricebowl-ä"): 
            with self.assertRaises(ValueError):
                geometry.geometry_path(role)

    def test_offscreen_saved_window_is_recovered_on_primary_display(self):
        monitor = SimpleNamespace(x=0, y=0, width=1366, height=768)
        self.assertEqual(
            geometry.visible_geometry(geometry.WindowGeometry(4000, 200, 880, 900), (monitor,)),
            geometry.WindowGeometry(243, 0, 880, 768))
        monitor_left = SimpleNamespace(x=-1920, y=0, width=1920, height=1080)
        saved = geometry.WindowGeometry(-1600, 40, 700, 500)
        self.assertEqual(geometry.visible_geometry(saved, (monitor_left, monitor)), saved)

    def test_restore_track_waits_for_nonmaximized_configuration_and_flushes_on_hide(self):
        window = mock.Mock()
        window.get_screen.return_value = SimpleNamespace(
            get_n_monitors=lambda: 1,
            get_monitor_geometry=lambda _i: SimpleNamespace(x=0, y=0, width=1280, height=800))
        window.get_visible.return_value = True
        window.get_window.return_value.get_state.return_value = 0
        window.get_position.return_value = (24, 33)
        window.get_size.return_value = (620, 470)
        Gdk = SimpleNamespace(WindowState=SimpleNamespace(MAXIMIZED=2))
        GLib = mock.Mock()
        GLib.timeout_add.return_value = 23
        saved = geometry.WindowGeometry(33, 44, 630, 500)
        with mock.patch.object(geometry, "load", return_value=saved), \
                mock.patch.object(geometry, "save") as write:
            self.assertTrue(geometry.restore_and_track(window, "ricebowl-aqua-settings", Gdk, GLib))
            window.set_default_size.assert_called_once_with(630, 500)
            window.move.assert_called_once_with(33, 44)
            hooks = {call.args[0]: call.args[1] for call in window.connect.call_args_list}
            hooks["configure-event"](window, None)
            GLib.timeout_add.assert_called_once()
            window.get_window.return_value.get_state.return_value = 2
            hooks["configure-event"](window, None)
            hooks["unmap-event"](window, None)
            write.assert_called_once_with("ricebowl-aqua-settings",
                                          geometry.WindowGeometry(24, 33, 620, 470))
            GLib.source_remove.assert_called_once_with(23)


if __name__ == "__main__":
    unittest.main()
