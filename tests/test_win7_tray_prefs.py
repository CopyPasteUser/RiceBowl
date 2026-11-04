"""Persistent Win7 SNI choices do not depend on a running desktop session."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from macrice.aero_tray import select_tray_icons
from macrice.win7_tray_prefs import (
    MAX_FILE_BYTES, TrayPreferences, load, save, stable_icon_id, validate,
)


class Win7TrayPreferencesTests(unittest.TestCase):
    def test_attention_and_explicit_choices(self):
        icons = [("music", "Active"), ("warning", "NeedsAttention"),
                 ("chat", "Active"), ("sleep", "Passive")]
        self.assertEqual(select_tray_icons(icons, 2, {"music": "hide", "chat": "show"}),
                         (("chat", "warning"), ("music",)))
        self.assertEqual(select_tray_icons(icons, 1, {"warning": "hide"}),
                         (("music",), ("warning", "chat")))
        self.assertEqual(select_tray_icons(icons, 0, {"chat": "show"}),
                         ((), ("music", "warning", "chat")))

    def test_defaults_are_read_only_and_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "tray.json"
            self.assertEqual(load(path), TrayPreferences())
            self.assertFalse(path.exists())
            prefs = TrayPreferences(4, {"org.example.Music": "show", "chat": "hide"})
            save(prefs, path)
            self.assertEqual(load(path), prefs)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text())["version"], 1)
            self.assertFalse(any(path.parent.glob(".win7-tray-*")))

    def test_reject_invalid_and_preserve_original_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tray.json"
            path.write_bytes(b"malformed user content")
            with self.assertRaises(ValueError):
                save(TrayPreferences(), path)
            self.assertEqual(path.read_bytes(), b"malformed user content")
            path.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
            with self.assertRaises(ValueError):
                load(path)

    def test_symlink_and_unsupported_format_are_not_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "other.json"
            target.write_text("sensitive", encoding="utf-8")
            link = root / "tray.json"
            link.symlink_to(target)
            with self.assertRaises(ValueError):
                load(link)
            with self.assertRaises(ValueError):
                save(TrayPreferences(), link)
            self.assertEqual(target.read_text(), "sensitive")
            link.unlink()
            link.write_text('{"version": 2, "visible_limit": 3, "icons": {}}')
            with self.assertRaises(ValueError):
                load(link)

    def test_validation_limits_and_stable_protocol_ids(self):
        self.assertEqual(stable_icon_id("org.example.MyApp"), "org.example.MyApp")
        for value in (":1.22", "../secret", "", "bad name", "x" * 97, 32):
            self.assertIsNone(stable_icon_id(value))
        for count in (-1, 9, True, "3"):
            with self.assertRaises(ValueError):
                validate(TrayPreferences(count, {}))
        for mode in ("bad", False, None):
            with self.assertRaises(ValueError):
                validate(TrayPreferences(3, {"app": mode}))
        with self.assertRaises(ValueError):
            validate(TrayPreferences(3, {str(i): "auto" for i in range(65)}))


if __name__ == "__main__":
    unittest.main()
