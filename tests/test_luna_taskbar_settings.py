"""XP-only taskbar/Start preferences and safe persistence."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from macrice.luna_taskbar_settings import (
    DEFAULT_OPTIONS, LunaSettingsError, center_on_workarea,
    load_options, save_options, validate_options,
)


class LunaTaskbarSettingsTests(unittest.TestCase):
    def test_dialog_centers_above_taskbar_on_any_monitor(self):
        from types import SimpleNamespace

        for width, height in ((800, 600), (1024, 768), (1600, 900)):
            rect = SimpleNamespace(x=300, y=150, width=width, height=height)
            x, y = center_on_workarea(rect, 408, 366)
            self.assertGreaterEqual(x, rect.x)
            self.assertGreaterEqual(y, rect.y)
            self.assertLessEqual(x + 408, rect.x + width)
            self.assertLessEqual(y + 366, rect.y + height - 40)

    def test_missing_preferences_use_separate_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            default = load_options(Path(directory) / "missing.json")
        self.assertEqual(default, DEFAULT_OPTIONS)
        default["show_clock"] = False
        self.assertTrue(DEFAULT_OPTIONS["show_clock"])

    def test_persists_all_controls_with_private_atomic_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ricehub" / "winxp-taskbar.json"
            options = save_options({"show_clock": False, "show_quick_launch": False,
                                    "group_similar_windows": False,
                                    "recent_program_count": 11}, path)
            self.assertEqual(load_options(path), options)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(tuple(path.parent.glob("*.tmp")), ())
            self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)

    def test_unknown_keys_are_dropped_and_old_values_get_defaults(self):
        self.assertEqual(validate_options({"future": "ignored"}), DEFAULT_OPTIONS)

    def test_rejects_bad_types_ranges_and_malformed_or_huge_json(self):
        for overrides in ({"show_clock": 1}, {"show_quick_launch": "yes"},
                          {"group_similar_windows": 0},
                          {"recent_program_count": True},
                          {"recent_program_count": 2},
                          {"recent_program_count": 13}):
            with self.subTest(overrides=overrides), self.assertRaises(LunaSettingsError):
                save_options(overrides, Path(tempfile.gettempdir()) / "unused.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            for payload in ("{oops", json.dumps(["not", "a", "dict"]),
                            " " * 8200):
                path.write_text(payload)
                with self.assertRaises(LunaSettingsError):
                    load_options(path)

    def test_rejects_symlinked_files_and_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            victim = root / "protected"
            victim.write_text("do not change")
            link = root / "xp.json"
            link.symlink_to(victim)
            with self.assertRaises(LunaSettingsError):
                load_options(link)
            with self.assertRaises(LunaSettingsError):
                save_options(DEFAULT_OPTIONS, link)
            self.assertEqual(victim.read_text(), "do not change")
            alias = root / "alias"
            alias.symlink_to(root)
            with self.assertRaises(LunaSettingsError):
                save_options(DEFAULT_OPTIONS, alias / "settings.json")


if __name__ == "__main__":
    unittest.main()
