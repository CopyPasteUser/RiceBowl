"""riceCheck must stay truthful, silent and strictly read-only."""

import tempfile
import json
import unittest
from pathlib import Path

from macrice.doctor import diagnose, summary
from macrice.installer import MANAGED_MARKER


class RiceCheckTests(unittest.TestCase):
    def test_healthy_xfce_session_without_extra_services(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "macrice").mkdir()
            (root / "macrice" / MANAGED_MARKER).write_text("managed")
            (root / "ricebowl").touch()
            (root / "ricehub-toggle").touch()
            names = {"xfconf-query", "xfce4-panel", "xfwm4", "nmcli", "pactl"}
            checks = diagnose(environment={"DISPLAY": ":0", "XDG_SESSION_TYPE": "x11",
                                           "XDG_CURRENT_DESKTOP": "XFCE"},
                              which=lambda program: "/usr/bin/" + program if program in names else None,
                              data_root=root, bin_root=root, gi_available=True)
            self.assertEqual(summary(checks), (11, 0, 4))
            self.assertEqual(next(c for c in checks if c.key == "bluetooth").status, "info")

    def test_missing_display_and_dependencies_have_repair_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            checks = diagnose(environment={"XDG_SESSION_TYPE": "wayland"}, which=lambda _: None,
                              data_root=Path(directory), bin_root=Path(directory), gi_available=False)
            self.assertEqual(next(c for c in checks if c.key == "x11").status, "warning")
            self.assertEqual(next(c for c in checks if c.key == "gtk").status, "warning")
            self.assertTrue(all(c.advice for c in checks if c.status != "ok"))

    def test_no_subprocess_or_private_network_details(self):
        with tempfile.TemporaryDirectory() as directory:
            checks = diagnose(environment={"DISPLAY": ":99", "DESKTOP_SESSION": "xfce"},
                              which=lambda _: None, data_root=Path(directory),
                              bin_root=Path(directory), gi_available=False)
            self.assertNotIn("SSID", " ".join(str(c) for c in checks))
            self.assertEqual(len(checks), len({c.key for c in checks}))

    def test_shortcut_backup_checked_without_exposing_previous_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "macrice-state/session-shortcuts.json"
            state.parent.mkdir()
            secret_command = "some-personal-launcher --my-local-path"
            state.write_text(json.dumps({"version": 1,
                "original": {"Super_L": secret_command, "Control_R": "old"},
                "managed": {"Super_L": "new", "Control_R": "new"}}))
            state.chmod(0o600)
            checks = diagnose(environment={}, which=lambda _: None,
                              data_root=root, bin_root=root, gi_available=False)
            self.assertEqual(next(c for c in checks if c.key == "shortcuts").status, "ok")
            self.assertNotIn(secret_command, str(checks))
            state.chmod(0o644)
            checks = diagnose(environment={}, which=lambda _: None,
                              data_root=root, bin_root=root, gi_available=False)
            self.assertEqual(next(c for c in checks if c.key == "shortcuts").status, "warning")
