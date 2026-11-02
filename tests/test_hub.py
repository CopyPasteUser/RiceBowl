"""RiceHub catalog, recovery model, and GTK style smoke tests."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.cli import main
from macrice.hub import CSS, HUB_VERSION, run
from macrice.hub_catalog import (
    AVAILABLE_STYLE_KEYS, FAMILIES, FAMILY_BY_KEY, recent_backups, search_families,
)
from macrice.rice import STYLES


class HubCatalogTests(unittest.TestCase):
    def test_macos_and_verified_aero_families_are_enabled(self):
        self.assertEqual([family.key for family in FAMILIES if family.available], ["macos", "windows10", "windows7"])
        self.assertEqual(AVAILABLE_STYLE_KEYS, set(STYLES))
        self.assertEqual(FAMILY_BY_KEY["macos"].styles, ("night", "day", "aqua"))
        # Every style used while constructing HubWindow must exist in the engine.
        for family in FAMILIES:
            for style in family.styles:
                self.assertIn(style, STYLES, f"{family.key}: {style} would crash startup")
        for family in FAMILIES:
            self.assertIs(FAMILY_BY_KEY[family.key], family)
            self.assertEqual(bool(family.styles), family.available)
        self.assertTrue(FAMILY_BY_KEY["windows7"].prototype)
        self.assertTrue(FAMILY_BY_KEY["windows10"].prototype)
        self.assertTrue(FAMILY_BY_KEY["windows10"].available)
        self.assertEqual({family.key for family in FAMILIES if family.prototype and not family.available},
                         {"winxp", "winclassic", "chromeos", "frutiger"})

    def test_search_availability_and_case_insensitive_queries(self):
        self.assertEqual([item.key for item in search_families("windows", "soon")],
                         ["winxp", "winclassic"])
        self.assertNotIn("windows11", FAMILY_BY_KEY)
        self.assertEqual({family.key for family in FAMILIES},
                         {"macos", "windows10", "windows7", "winxp", "winclassic", "chromeos", "frutiger"})
        self.assertEqual([item.key for item in search_families("AURORA", "available")], ["macos"])
        self.assertEqual([item.key for item in search_families("windows", "available")], ["windows10", "windows7"])
        self.assertEqual(search_families("not a real rice"), ())
        with self.assertRaises(ValueError):
            search_families("", "no-such-filter")

    def test_backup_listing_uses_valid_manifests_and_excludes_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "macrice-state/backups/rice"
            root.mkdir(parents=True)
            good = root / "20261102T105520123456Z"
            good.mkdir()
            (good / "manifest.json").write_text(json.dumps({"style": "night", "schema": 2}))
            restored = root / "20261102T105620123456Z"
            restored.mkdir()
            (restored / "manifest.json").write_text(json.dumps({"style": "day"}))
            (restored / "restored").write_text("already restored")
            unknown = root / "20261102T105720123456Z"
            unknown.mkdir()
            (unknown / "manifest.json").write_text(json.dumps({"style": "retired-style"}))
            invalid = root / "20261102T105820123456Z"
            invalid.mkdir()
            (invalid / "manifest.json").write_text("invalid json")
            records = recent_backups(base)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].style, "night")
            self.assertEqual(records[0].created, "2026-11-02 10:55")
            self.assertEqual(recent_backups(base, limit=0), [])

    def test_missing_state_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(recent_backups(root), [])
            self.assertEqual(list(root.iterdir()), [])


class HubStylingTests(unittest.TestCase):
    def test_existing_cli_launches_the_new_hub(self):
        with mock.patch("macrice.hub.run", return_value=0) as fake:
            self.assertEqual(main(["hub"]), 0)
            fake.assert_called_once_with()

    def test_styling_is_native_and_does_not_require_web_stack(self):
        self.assertEqual(HUB_VERSION, "0.5.0rc2")
        self.assertIn(b"hub-card", CSS)
        self.assertNotIn(b"javascript", CSS.lower())
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("PyGObject unavailable on this test runner")
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)

    def test_headless_launch_fails_cleanly(self):
        with mock.patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
            self.assertEqual(run(), 1)


if __name__ == "__main__":
    unittest.main()
