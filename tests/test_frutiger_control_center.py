"""Aqua Control Center contracts that do not require a running GTK desktop."""

from __future__ import annotations

import unittest
from pathlib import Path

from macrice.frutiger_control_center import (AQUA_CATEGORIES, available_tool,
                                             search_aqua)
from macrice.heritage_shell import CSS


ROOT = Path(__file__).resolve().parents[1]


class AquaControlCenterTests(unittest.TestCase):
    def test_unique_categories_and_real_three_level_navigation(self):
        identifiers = [category[0] for category in AQUA_CATEGORIES]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for required in ("connections", "sound", "display", "personalize", "power",
                         "devices", "applications", "system", "accessibility"):
            self.assertIn(required, identifiers)
        for category in AQUA_CATEGORIES:
            self.assertGreaterEqual(len(category[4]), 2)
            for task in category[4]:
                self.assertEqual(len(task), 4)
                self.assertTrue(task[0] and task[3])
        source = (ROOT / "macrice/frutiger_control_center.py").read_text(encoding="utf-8")
        for contract in ('navigate("home")', 'navigate("category", category)',
                         'navigate("detail", category, task)', 'navigate("search")',
                         'back.connect("clicked", go_back)',
                         'set_sensitive(False)', 'set_placeholder_text'):
            self.assertIn(contract, source)

    def test_search_is_finite_case_insensitive_and_matches_descriptions(self):
        self.assertEqual(search_aqua(""), ())
        self.assertIn("Bluetooth devices", [task[0] for _, task in search_aqua("BLUETOOTH")])
        self.assertIn("Display configuration", [task[0] for _, task in search_aqua("resolution")])
        self.assertIn("Default applications", [task[0] for _, task in search_aqua("BROWSER")])
        self.assertEqual(search_aqua("no setting could match this string"), ())

    def test_external_commands_are_strictly_allowlisted_and_installed(self):
        self.assertEqual(available_tool(("nm-connection-editor",), lambda cmd: "/bin/tool"),
                         "nm-connection-editor")
        self.assertIsNone(available_tool(("untrusted-tool",), lambda cmd: "/bin/tool"))
        self.assertIsNone(available_tool(("nm-connection-editor",), lambda cmd: None))
        for category in AQUA_CATEGORIES:
            for task in category[4]:
                for command in task[2]:
                    self.assertTrue(available_tool((command,), lambda cmd: "/bin/tool"),
                                    command)

    def test_aqua_css_is_isolated_and_covers_deep_controls(self):
        css = CSS["frutiger"]
        for selector in (b".aqua-control-category", b".aqua-control-task",
                         b".aqua-control-detail-title", b".aqua-control-search:focus",
                         b".aqua-control-unavailable", b".aqua-control-live",
                         b".aqua-control-launch:hover"):
            self.assertIn(selector, css)
        for profile in ("winxp", "aero", "winclassic", "chromeos", "windows10"):
            if profile in CSS:
                self.assertNotIn(b".aqua-control-category", CSS[profile])

    def test_frutiger_tray_and_launcher_share_one_control_center(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertIn('from .frutiger_control_center import build', source)
        self.assertIn('self._show_aqua_control(page)', source)
        self.assertIn('self._show_aqua_control())', source)
        self.assertIn('"audio": "sound", "network": "connections"', source)
        self.assertIn('"battery": "power"', source)
        self.assertIn('self.aqua_control_show_category(category)', source)

    def test_places_reads_live_gio_mounts_and_uses_real_trash(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        launcher = source[source.index("def _create_frutiger_menu(self):"):
                          source.index("def _create_ten_menu(self):")]
        for expression in ('Gio.VolumeMonitor.get()', 'monitor.get_mounts()',
                           'mount.is_shadowed()', 'mount.get_default_location().get_uri()',
                           '"mount-added", "mount-removed", "mount-changed"',
                           'self._open_uri("trash:///")', 'DIRECTORY_DESKTOP'):
            self.assertIn(expression, launcher)


if __name__ == "__main__":
    unittest.main()
