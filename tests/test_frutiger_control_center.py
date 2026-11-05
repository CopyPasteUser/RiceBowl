"""Aqua Control Center contracts that do not require a running GTK desktop."""

from __future__ import annotations

import unittest
from pathlib import Path

from macrice.frutiger_control_center import (AQUA_CATEGORIES, available_tool,
                                             search_aqua, DETAIL_PROBES)
from macrice.frutiger_device_details import (split_nmcli_fields, wifi_networks,
                                             bluetooth_adapter, audio_outputs,
                                             connected_displays, probe)
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

    def test_live_detail_probes_cover_real_device_pages(self):
        for key in (("connections", "Network connections"),
                    ("connections", "Bluetooth devices"),
                    ("sound", "Input & output devices"),
                    ("display", "Display configuration"),
                    ("system", "System information")):
            self.assertIn(key, DETAIL_PROBES)
        self.assertIn("Unsupported", probe("not-an-adapter").error)

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
                         b".aqua-control-launch:hover", b"popover.aqua-flyout",
                         b".aqua-flyout-mute:checked", b".aqua-control-probe-error"):
            self.assertIn(selector, css)
        for profile in ("winxp", "aero", "winclassic", "chromeos", "windows10"):
            if profile in CSS:
                self.assertNotIn(b".aqua-control-category", CSS[profile])

    def test_frutiger_tray_and_launcher_share_one_control_center(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertIn('from .frutiger_control_center import build', source)
        self.assertIn('self._show_aqua_control(page)', source)
        self.assertIn('self._show_aqua_control())', source)
        self.assertIn('self.aqua_control_show_category(category)', source)
        self.assertIn('self._aqua_flyouts.show(name)', source)
        flyouts = (ROOT / 'macrice/frutiger_flyouts.py').read_text(encoding='utf-8')
        for marker in ('"network": "connections"', '"audio": "sound"',
                       '"battery": "power"', 'shell._queue_volume_change',
                       'shell._toggle_output_mute', 'create_tray_window(button, Gtk'):
            self.assertIn(marker, flyouts)

    def test_places_reads_live_gio_mounts_and_uses_real_trash(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        launcher = source[source.index("def _create_frutiger_menu(self):"):
                          source.index("def _create_ten_menu(self):")]
        for expression in ('Gio.VolumeMonitor.get()', 'monitor.get_mounts()',
                           'mount.is_shadowed()', 'mount.get_default_location().get_uri()',
                           '"mount-added", "mount-removed", "mount-changed"',
                           'self._open_uri("trash:///")', 'DIRECTORY_DESKTOP'):
            self.assertIn(expression, launcher)

    def test_launcher_search_covers_apps_real_places_and_aqua_settings(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        results = source[source.index("def _populate_frutiger(self, query):"):
                         source.index("def _populate_win7(self, query):")]
        for marker in ('frutiger_apps(self.apps, self._pinned_ids, query)',
                       'from .frutiger_control_center import search_aqua',
                       'GLib.UserDirectory.DIRECTORY_DOWNLOAD',
                       'self._open_luna_user_folder(folder)',
                       'self._open_uri("trash:///")',
                       'self._show_aqua_control(page, item)',
                       'No matching apps, places or settings'):
            self.assertIn(marker, results)
        self.assertIn('shell.aqua_control_show_task = show_named_task',
                      (ROOT / 'macrice/frutiger_control_center.py').read_text(encoding='utf-8'))

    def test_nmcli_escaped_colons_and_sorted_real_networks(self):
        self.assertEqual(split_nmcli_fields(r"yes:Cafe\:2.4G:90:WPA2"),
                         ("yes", "Cafe:2.4G", "90", "WPA2"))
        self.assertEqual(split_nmcli_fields(r"no:Wifi\\Guest:40:"),
                         ("no", "Wifi\\Guest", "40", ""))
        result = wifi_networks(run=lambda args: (
            "no:Other:25:WPA3\nyes:Cafe\\:2.4G:91:WPA2\n"
            "no:Other:60:WPA3\ninvalid\n", None))
        self.assertEqual(result.lines, (
            "Connected · Cafe:2.4G · 91% · WPA2", "Other · 60% · WPA3"))
        self.assertIn("unavailable", wifi_networks(
            run=lambda args: (None, "unavailable")).error)

    def test_read_only_bluetooth_audio_and_display_probes(self):
        self.assertEqual(bluetooth_adapter(run=lambda args: (
            "Controller 11:22:33\n\tName: Desk Bluetooth\n\tPowered: yes\n", None)).lines,
            ("Adapter: Desk Bluetooth", "Power: On"))
        self.assertIn("No Bluetooth", bluetooth_adapter(
            run=lambda args: ("No default controller available", None)).error)
        self.assertEqual(audio_outputs(run=lambda args: (
            "0\talsa_output.usb\tmodule\ts16le\tRUNNING\n", None)).lines,
            ("alsa_output.usb · RUNNING",))
        self.assertEqual(connected_displays(run=lambda args: (
            "Screen 0\nHDMI-1 connected primary 1920x1080+0+0\n"
            "DP-1 disconnected\neDP-1 connected 1366x768+0+0\n", None)).lines,
            ("HDMI-1 · 1920x1080", "eDP-1 · 1366x768"))


if __name__ == "__main__":
    unittest.main()
