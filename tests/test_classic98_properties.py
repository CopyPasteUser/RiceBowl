"""Regression checks for Windows 98 Taskbar Properties without a GTK display."""
from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from macrice.classic98_properties import (
    DEFAULTS, apply_settings, load_settings, save_settings, settings_path,
)


class ClassicTaskbarSettingsTests(unittest.TestCase):
    def test_defaults_for_missing_or_corrupt_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            self.assertEqual(load_settings(path), DEFAULTS)
            path.write_text("{not json")
            self.assertEqual(load_settings(path), DEFAULTS)
            path.write_text("[]" )
            self.assertEqual(load_settings(path), DEFAULTS)
            path.write_bytes(b"x" * 4097)
            self.assertEqual(load_settings(path), DEFAULTS)

    def test_partial_values_are_strict_booleans(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"show_clock": False,
                                        "show_quick_launch": "no",
                                        "unrelated": "ignore"}))
            self.assertEqual(load_settings(path),
                             {"show_clock": False, "show_quick_launch": True})

    def test_atomic_roundtrip_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config" / "settings.json"
            candidate = {"show_clock": False, "show_quick_launch": False}
            save_settings(candidate, path)
            self.assertEqual(load_settings(path), candidate)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(list(path.parent.glob(".classic98-taskbar-*")), [])
            candidate["show_clock"] = True
            save_settings(candidate, path)
            self.assertEqual(load_settings(path), candidate)

    def test_bad_input_does_not_change_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_settings(dict(DEFAULTS), path)
            old = path.read_bytes()
            for bad in ({"show_clock": 1, "show_quick_launch": False},
                        {"show_clock": True},
                        {"show_clock": True, "show_quick_launch": True,
                         "rogue": False}):
                with self.assertRaises(ValueError):
                    save_settings(bad, path)
                self.assertEqual(path.read_bytes(), old)

    def test_symlink_is_never_overwritten_or_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            victim = root / "victim"
            victim.write_text("untouched")
            target = root / "settings"
            target.symlink_to(victim)
            self.assertEqual(load_settings(target), DEFAULTS)
            with self.assertRaises(ValueError):
                save_settings(dict(DEFAULTS), target)
            self.assertEqual(victim.read_text(), "untouched")

    def test_xdg_location(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}):
                self.assertEqual(settings_path(),
                                 Path(directory) / "ricebowl" / "classic98-taskbar.json")

    def test_apply_only_touches_classic_widgets(self):
        shell = MagicMock()
        apply_settings(shell, {"show_clock": False, "show_quick_launch": True})
        shell.classic98_clock_button.set_visible.assert_called_once_with(False)
        shell.classic98_quick_launch.set_visible.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
