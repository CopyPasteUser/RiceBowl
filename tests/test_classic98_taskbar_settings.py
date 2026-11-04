"""Regression coverage for private, persistent Win98 taskbar preferences."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from macrice.classic98_taskbar_settings import (
    DEFAULT_OPTIONS, TaskbarSettingsError, load_options, save_options,
)


class Classic98TaskbarOptionsTests(unittest.TestCase):
    def test_missing_settings_use_independent_defaults(self):
        with tempfile.TemporaryDirectory() as dirname:
            original = load_options(Path(dirname) / "missing.json")
            self.assertEqual(original, DEFAULT_OPTIONS)
            original["show_clock"] = False
            self.assertTrue(DEFAULT_OPTIONS["show_clock"])

    def test_save_and_reload_private_atomic_preferences(self):
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "ricebowl" / "classic98-taskbar.json"
            saved = save_options({"show_clock": False, "show_quick_launch": True}, path)
            self.assertFalse(saved["show_clock"])
            self.assertEqual(load_options(path), saved)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
            self.assertEqual(tuple(path.parent.glob("*.tmp")), ())

    def test_invalid_config_never_silently_overrides_default(self):
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "broken.json"
            path.write_text(json.dumps({"show_clock": "false"}))
            with self.assertRaises(TaskbarSettingsError):
                load_options(path)
            with self.assertRaises(TaskbarSettingsError):
                save_options({"show_clock": 0}, path)

    def test_oversized_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "large.json"
            path.write_text("x" * 8193)
            with self.assertRaises(TaskbarSettingsError):
                load_options(path)


if __name__ == "__main__":
    unittest.main()
