"""XP icon visibility is persisted independently from Windows 7 and XFCE."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from macrice.luna_tray_preferences import preferences_path
from macrice.win7_tray_prefs import TrayPreferences, load, save
from macrice.aero_tray import select_tray_icons


class LunaTrayPreferencesTests(unittest.TestCase):
    def test_settings_files_are_rice_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}):
                xp_path = preferences_path()
                from macrice.win7_tray_prefs import preferences_path as win7_path

                self.assertEqual(xp_path, Path(directory) / "ricehub" / "winxp-tray.json")
                self.assertNotEqual(xp_path, win7_path())
                xp = TrayPreferences(2, {"org.example.Music": "hide"})
                windows7 = TrayPreferences(4, {"org.example.Music": "show"})
                save(xp, xp_path)
                save(windows7, win7_path())
                self.assertEqual(load(xp_path), xp)
                self.assertEqual(load(win7_path()), windows7)
                self.assertEqual(xp_path.stat().st_mode & 0o777, 0o600)
                self.assertEqual(win7_path().stat().st_mode & 0o777, 0o600)

    def test_no_config_file_is_written_on_read(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}):
                path = preferences_path()
                self.assertEqual(load(path), TrayPreferences())
                self.assertFalse(path.exists())

    def test_hidden_xp_icon_remains_accessible_through_overflow(self):
        icons = [("player", "Active"), ("network", "NeedsAttention"),
                 ("inactive", "Passive"), ("chat", "Active")]
        visible, overflow = select_tray_icons(
            icons, 2, {"player": "hide", "chat": "show"})
        self.assertEqual(visible, ("chat", "network"))
        self.assertEqual(overflow, ("player",))

    def test_invalid_or_symlink_config_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}):
                path = preferences_path()
                path.parent.mkdir()
                path.write_text("invalid user content", encoding="utf-8")
                with self.assertRaises(ValueError):
                    save(TrayPreferences(), path)
                self.assertEqual(path.read_text(encoding="utf-8"), "invalid user content")
                path.unlink()
                target = Path(directory) / "private"
                target.write_text("keep", encoding="utf-8")
                path.symlink_to(target)
                with self.assertRaises(ValueError):
                    load(path)
                with self.assertRaises(ValueError):
                    save(TrayPreferences(), path)
                self.assertEqual(target.read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
