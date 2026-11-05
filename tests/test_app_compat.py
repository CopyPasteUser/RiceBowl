"""App compatibility diagnostics must be truthful and non-invasive."""

import json
import subprocess
import unittest
from unittest.mock import patch

from macrice.app_compat import format_report, inspect_window, parse_properties
from macrice.cli import main, parser


SAMPLE = (
    'WM_CLASS = "Mail", "thunderbird"\n'
    '_GTK_FRAME_EXTENTS = 4, 4, 28, 4\n'
    '_MOTIF_WM_HINTS:  not found.\n'
    '_NET_WM_WINDOW_TYPE = _NET_WM_WINDOW_TYPE_NORMAL\n'
    'WM_NAME = "SECRET PRIVATE EMAIL SUBJECT"\n'
)


class AppCompatTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

    def run_command(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if command[0] == "xprop":
            return subprocess.CompletedProcess(command, 0, SAMPLE, "")
        return subprocess.CompletedProcess(command, 0, "Chicago\n", "")

    def inspect(self, **kwargs):
        return inspect_window(environment={"DISPLAY": ":99", "XDG_SESSION_TYPE": "x11"},
                              which=lambda _: "/usr/bin/available", run=self.run_command, **kwargs)

    def test_inspection_never_requests_titles_or_changes_appearance(self):
        report = self.inspect()
        self.assertEqual(report["application"], "thunderbird")
        self.assertEqual(report["window"]["wm_class"], ["Mail", "thunderbird"])
        self.assertEqual(report["active_gtk_theme"], "Chicago")
        self.assertTrue(report["window"]["gtk_frame_extents_hint"])
        self.assertFalse(report["window"]["motif_hints_present"])
        self.assertNotIn("SECRET", json.dumps(report))
        self.assertNotIn("WM_NAME", self.calls[0][0])
        self.assertEqual(self.calls[0][0][:2], ["xprop", "-notype"])
        self.assertTrue(all(call[0][0] in ("xprop", "xfconf-query") for call in self.calls))
        self.assertTrue(all(call[1]["check"] is False for call in self.calls))
        self.assertEqual(self.calls[0][1]["timeout"], 25)

    def test_explicit_window_id_is_validated_and_bounded(self):
        report = self.inspect(window_id="0xAB123")
        self.assertEqual(report["application"], "thunderbird")
        self.assertIn("0xAB123", self.calls[0][0])
        self.assertEqual(self.calls[0][1]["timeout"], 3)
        with self.assertRaisesRegex(ValueError, "hexadecimal"):
            self.inspect(window_id=";rm -rf something")
        self.assertEqual(len(self.calls), 3)

    def test_photocraft_settings_and_custom_ui_boundary(self):
        parsed = parse_properties('WM_CLASS = "photocraft", "PhotoCraft"\n')
        self.assertEqual(parsed["wm_class"], ["photocraft", "PhotoCraft"])
        self.assertFalse(parsed["gtk_frame_extents_hint"])
        def custom(command, **kwargs):
            if command[0] == "xprop":
                return subprocess.CompletedProcess(command, 0,
                                                   'WM_CLASS = "photocraft", "PhotoCraft"\n', "")
            return subprocess.CompletedProcess(command, 1, "", "not configured")
        report = inspect_window(environment={"DISPLAY": ":1"},
                                which=lambda _: "present", run=custom)
        self.assertIn("System Title Bar", report["next_step"])
        self.assertIn("self-drawn", report["next_step"])
        self.assertIsNone(report["active_gtk_theme"])
        self.assertIn("PhotoCraft", format_report(report))

    def test_untrusted_properties_and_theme_names_are_redacted(self):
        parsed = parse_properties('WM_CLASS = "person@example.com", "Mail"\n'
                                  'WM_NAME = "private text"\n')
        self.assertEqual(parsed["wm_class"], ["<redacted>", "Mail"])
        self.assertNotIn("private text", str(parsed))
        def untrusted(command, **kwargs):
            if command[0] == "xprop":
                return subprocess.CompletedProcess(command, 0,
                                                   'WM_CLASS = "ok", "tool"\n', "")
            return subprocess.CompletedProcess(command, 0, "secret@example.com\n", "")
        report = inspect_window(environment={"DISPLAY": ":1"},
                                which=lambda _: "present", run=untrusted)
        self.assertEqual(report["active_gtk_theme"], "<redacted>")

    def test_missing_session_and_tools_do_not_query_x11(self):
        with self.assertRaisesRegex(ValueError, "Wayland"):
            inspect_window(environment={"DISPLAY": ":1", "XDG_SESSION_TYPE": "wayland"},
                           run=self.run_command)
        with self.assertRaisesRegex(ValueError, "DISPLAY"):
            inspect_window(environment={}, run=self.run_command)
        with self.assertRaisesRegex(ValueError, "x11-utils"):
            inspect_window(environment={"DISPLAY": ":1"}, which=lambda _: None,
                           run=self.run_command)
        self.assertEqual(self.calls, [])

    def test_timeouts_failure_and_size_limits(self):
        def timeout(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        with self.assertRaisesRegex(ValueError, "timed out"):
            inspect_window(environment={"DISPLAY": ":1"}, which=lambda _: "present", run=timeout)

        def rejected(command, **kwargs):
            return subprocess.CompletedProcess(command, 1, "", "private stderr")
        with self.assertRaisesRegex(ValueError, "selection cancelled"):
            inspect_window(environment={"DISPLAY": ":1"}, which=lambda _: "present", run=rejected)

        def oversized(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, "X" * 8193, "")
        with self.assertRaisesRegex(ValueError, "size limit"):
            inspect_window(environment={"DISPLAY": ":1"}, which=lambda _: "present", run=oversized)

    def test_cli_requires_target_and_exposes_json_without_ui(self):
        with self.assertRaises(SystemExit):
            parser().parse_args(["app-compat"])
        args = parser().parse_args(["app-compat", "--select", "--json"])
        self.assertTrue(args.select)
        self.assertTrue(args.json)
        with patch("macrice.app_compat.inspect_window", return_value={"window": {"wm_class": []}}):
            with patch("builtins.print") as output:
                self.assertEqual(main(["app-compat", "--window-id", "0x10", "--json"]), 0)
        self.assertEqual(json.loads(output.call_args.args[0]), {"window": {"wm_class": []}})


if __name__ == "__main__":
    unittest.main()
