"""Contract checks for all four opt-in riceware foundations; no live devices."""

import contextlib
import io
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from macrice import cli, hardware_status
from macrice.luna_desktop import _desktop_entry
from macrice.riceware import plate, pop, spice, wine


class SpiceTests(unittest.TestCase):
    def test_unknown_capability_and_explicit_unavailable(self):
        with self.assertRaises(ValueError):
            spice.read("shell_command")
        with patch.dict(spice.READERS, {"wifi": lambda: None}):
            self.assertEqual(spice.read("wifi").status, "unavailable")
        with patch.dict(spice.READERS, {"audio": lambda: hardware_status.SoundState(None, None)}):
            self.assertEqual(spice.read("audio").status, "unavailable")

    def test_mutation_reads_real_result_and_surfaces_errors(self):
        writer = Mock(return_value=True)
        with patch.dict(spice.WRITERS, {"wifi": (writer, "wifi")}), \
             patch.dict(spice.READERS, {"wifi": lambda: False}):
            state = spice.change("wifi", True)
        self.assertEqual(state.value, False)  # Never replace readback with requested value.
        writer.assert_called_once_with(True)
        with patch.dict(spice.WRITERS, {"wifi": (Mock(side_effect=RuntimeError("denied")), "wifi")}):
            failure = spice.change("wifi", True)
        self.assertEqual(failure.status, "error")
        self.assertIn("denied", failure.reason)

    def test_wifi_disconnect_has_no_arbitrary_value(self):
        with self.assertRaises(ValueError):
            spice.change("unknown", "rm")
        with patch.dict(spice.WRITERS, {"wifi_disconnect": (Mock(), "wifi_networks")}):
            self.assertEqual(spice.change("wifi_disconnect", "bad").status, "error")
        with patch.dict(spice.WRITERS, {"wifi_connect": (Mock(return_value=False), "wifi_networks")}):
            self.assertEqual(spice.change("wifi_connect", "ssid").status, "error")


class PopTests(unittest.TestCase):
    def test_native_log_is_reused(self):
        with patch.object(pop.xfce, "list_notifications", return_value=("real-entry",)):
            self.assertEqual(pop.history(), ("real-entry",))
        with patch.object(pop.xfce, "set_dnd", return_value=True) as setter:
            self.assertTrue(pop.set_quiet_mode(True))
            setter.assert_called_once_with(True)

    def test_send_is_explicit_bounded_and_argument_safe(self):
        with patch.object(pop.shutil, "which", return_value="/usr/bin/notify-send"), \
             patch.object(pop.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            pop.send("-looks-like-option", "Hello")
        self.assertEqual(run.call_args.args[0],
                         ["/usr/bin/notify-send", "--app-name=RiceBowl", "--", "-looks-like-option", "Hello"])
        self.assertEqual(run.call_args.kwargs["timeout"], 4)
        with self.assertRaises(ValueError):
            pop.send("x" * 161)

    def test_missing_host_is_not_silently_faked(self):
        with patch.object(pop.shutil, "which", return_value=None):
            with self.assertRaises(pop.NotificationUnavailable):
                pop.send("Test")


class PlateTests(unittest.TestCase):
    def test_read_only_snapshot_never_follows_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "a.desktop").write_text("shortcut", encoding="utf-8")
            (folder / "b").mkdir()
            (folder / "c").symlink_to(folder / "a.desktop")
            view = plate.snapshot(folder)
            self.assertEqual([item.kind for item in view.items], ["launcher", "directory", "link"])
            self.assertTrue((folder / "a.desktop").exists())
            with self.assertRaises(ValueError):
                plate.snapshot(folder / "c")
            with self.assertRaises(ValueError):
                plate.snapshot(folder, limit=1.5)

    def test_shortcuts_preserve_user_modifications(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            catalog = {"ricebowl-xp-trash.desktop": _desktop_entry("Trash", "user-trash", "trash:///")}
            self.assertEqual(plate.manage_shortcuts("xp", "install", folder=folder,
                                                    catalog=catalog)[0], tuple(catalog))
            target = folder / next(iter(catalog))
            target.write_text("user modified", encoding="utf-8")
            self.assertEqual(plate.manage_shortcuts("xp", "remove", folder=folder,
                                                    catalog=catalog)[0], ())
            self.assertEqual(target.read_text(), "user modified")
            with self.assertRaises(ValueError):
                plate.manage_shortcuts("chromeos", "install", folder=folder)


class WineTests(unittest.TestCase):
    def test_names_and_prefix_store_cannot_escape(self):
        for name in ("../escape", "UPPER", "", "name.with.dot", "a" * 49):
            with self.assertRaises(ValueError):
                wine._name(name)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            folder.symlink_to(tmp)
            with self.assertRaises(RuntimeError):
                wine.list_prefixes(store=folder)

    def test_initialize_and_launch_only_managed_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                 patch.object(wine.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
                created = wine.create_prefix("game_1", store=folder)
            self.assertTrue(created.ready)
            self.assertTrue((folder / "game_1" / wine.MARKER).is_file())
            self.assertFalse((folder / "game_1" / wine.MARKER).stat().st_mode & stat.S_IRWXO)
            self.assertEqual(run.call_args.kwargs["env"]["WINEPREFIX"], str(folder / "game_1"))
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wine"), \
                 patch.object(wine.subprocess, "Popen", return_value=Mock(pid=12345)) as launch:
                self.assertEqual(wine.launch("game_1", "setup.exe", ("/silent",), store=folder), 12345)
            self.assertEqual(launch.call_args.args[0], ["/usr/bin/wine", "setup.exe", "/silent"])
            self.assertTrue(launch.call_args.kwargs["start_new_session"])
            self.assertEqual([p.name for p in wine.list_prefixes(store=folder)], ["game_1"])

    def test_failed_creation_preserves_diagnostics_but_cannot_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wineboot"), \
                 patch.object(wine.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)):
                with self.assertRaises(RuntimeError):
                    wine.create_prefix("broken", store=folder)
            self.assertTrue((folder / "broken" / ".ricewine-init.log").exists())
            self.assertFalse(wine.list_prefixes(store=folder)[0].ready)
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wine"):
                with self.assertRaises(RuntimeError):
                    wine.launch("broken", "setup.exe", store=folder)

    def test_never_runs_wine_as_root(self):
        with patch.object(wine.os, "geteuid", return_value=0):
            with self.assertRaises(RuntimeError):
                wine.create_prefix("game")
            with self.assertRaises(RuntimeError):
                wine.launch("game", "app.exe")


class CliTests(unittest.TestCase):
    def test_spice_cli_reports_structured_capability(self):
        output = io.StringIO()
        with patch.dict(spice.READERS, {"wifi": lambda: False}), \
             contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(["riceware", "spice", "get", "wifi"]), 0)
        self.assertEqual(json.loads(output.getvalue())["value"], False)

    def test_wine_status_without_wine_is_non_mutating(self):
        output = io.StringIO()
        with patch.object(wine, "wine_version", return_value=None), \
             patch.object(wine, "list_prefixes", return_value=()), \
             contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(["riceware", "wine", "status"]), 0)
        self.assertIsNone(json.loads(output.getvalue())["wine_version"])


if __name__ == "__main__":
    unittest.main()
