"""RiceHub catalog, recovery model, and GTK style smoke tests."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.cli import main
from macrice.hub import CSS, _activate_hub_window, run
from macrice.hub_art import FAMILY_ICONS, PREVIEW_FILES
from macrice.hub_catalog import (
    AVAILABLE_STYLE_KEYS, FAMILIES, FAMILY_BY_KEY, recent_backups, search_families,
)
from macrice.rice import STYLES


class HubCatalogTests(unittest.TestCase):
    def test_macos_and_verified_aero_families_are_enabled(self):
        self.assertEqual([family.key for family in FAMILIES if family.available],
                         ["macos", "windows10", "windows7", "winxp", "winclassic", "chromeos", "frutiger"])
        self.assertEqual(AVAILABLE_STYLE_KEYS, set(STYLES))
        self.assertEqual(FAMILY_BY_KEY["macos"].styles, ("night", "day", "aqua"))
        # Every style used while constructing HubWindow must exist in the engine.
        for family in FAMILIES:
            for style in family.styles:
                self.assertIn(style, STYLES, f"{family.key}: {style} would crash startup")
        for family in FAMILIES:
            self.assertIs(FAMILY_BY_KEY[family.key], family)
            self.assertEqual(bool(family.styles), family.available)
        self.assertTrue(all(family.available for family in FAMILIES))
        self.assertEqual(set(PREVIEW_FILES), {family.key for family in FAMILIES if family.key != "macos"})
        self.assertEqual(set(FAMILY_ICONS), {family.key for family in FAMILIES})
        self.assertFalse(any(hasattr(family, "prototype") for family in FAMILIES))

    def test_search_availability_and_case_insensitive_queries(self):
        self.assertEqual([item.key for item in search_families("windows", "soon")], [])
        self.assertNotIn("windows11", FAMILY_BY_KEY)
        self.assertEqual({family.key for family in FAMILIES},
                         {"macos", "windows10", "windows7", "winxp", "winclassic", "chromeos", "frutiger"})
        self.assertEqual([item.key for item in search_families("AURORA", "available")], ["macos"])
        self.assertEqual([item.key for item in search_families("windows", "available")],
                         ["windows10", "windows7", "winxp", "winclassic"])
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
        self.assertIn(b"hub-card", CSS)
        self.assertIn(b"hub-preview-frame", CSS)
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


class HubActivationTests(unittest.TestCase):
    def test_failed_constructor_destroys_invisible_gtk_window_and_quits(self):
        application = mock.Mock()
        invisible = mock.Mock()
        application.get_windows.return_value = [invisible]
        active = []

        def create(_application):
            raise ValueError("style missing after Gtk.ApplicationWindow was registered")

        with mock.patch("traceback.print_exc") as trace:
            self.assertFalse(_activate_hub_window(application, active, create))
        trace.assert_called_once_with()
        invisible.destroy.assert_called_once_with()
        application.quit.assert_called_once_with()
        self.assertEqual(active, [])

    def test_activation_creates_or_presents_one_window(self):
        application = mock.Mock()
        window = mock.Mock()
        window._selected = "macos"
        active = []
        factory = mock.Mock(return_value=window)

        self.assertTrue(_activate_hub_window(application, active, factory))
        self.assertEqual(active, [window])
        window.show_all.assert_called_once_with()
        window._select_family.assert_called_once_with("macos")
        factory.assert_called_once_with(application)
        self.assertTrue(_activate_hub_window(application, active, factory))
        window.present.assert_called_once_with()
        factory.assert_called_once()


if __name__ == "__main__":
    unittest.main()
