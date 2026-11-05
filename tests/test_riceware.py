"""Contract checks for all four opt-in riceware foundations; no live devices."""

import contextlib
import io
import json
import stat
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
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
        with patch.dict(spice.READERS, {"wifi_networks": lambda: ()}), \
             patch.object(hardware_status, "read_wifi_radio", return_value=None):
            self.assertEqual(spice.read("wifi_networks").status, "unavailable")
        with patch.dict(spice.READERS, {"power_profiles": lambda: object()}):
            self.assertEqual(spice.read("power_profiles").status, "error")

    def test_mutation_reads_real_result_and_surfaces_errors(self):
        writer = Mock(return_value=True)
        with patch.dict(spice.WRITERS, {"wifi": (writer, "wifi")}), \
             patch.dict(spice.READERS, {"wifi": lambda: False}):
            state = spice.change("wifi", True)
        self.assertEqual(state.status, "error")
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

    def test_changed_audio_and_bluetooth_state_must_be_verified(self):
        with patch.dict(spice.WRITERS, {"audio_volume": (Mock(return_value=True), "audio")}), \
             patch.dict(spice.READERS, {"audio": lambda: hardware_status.SoundState(50, False)}):
            self.assertEqual(spice.change("audio_volume", 50).status, "ok")
            self.assertEqual(spice.change("audio_volume", 80).status, "error")
        bluetooth = hardware_status.BluetoothState(False, ())
        with patch.dict(spice.WRITERS, {
                "bluetooth_power": (Mock(return_value=bluetooth), "bluetooth")}), \
             patch.dict(spice.READERS, {"bluetooth": lambda: bluetooth}):
            self.assertEqual(spice.change("bluetooth_power", False).status, "ok")
            self.assertEqual(spice.change("bluetooth_power", True).status, "error")

    def test_concurrent_writes_to_same_device_are_serialized(self):
        entered, release, second_started = (threading.Event() for _ in range(3))
        state = [0]

        def writer(value):
            if value == 30:
                entered.set()
                self.assertTrue(release.wait(2))
            state[0] = value

        def second():
            second_started.set()
            return spice.change("audio_volume", 40)

        with patch.dict(spice.WRITERS, {"audio_volume": (writer, "audio")}), \
             patch.dict(spice.READERS, {"audio": lambda: hardware_status.SoundState(state[0], False)}):
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(spice.change, "audio_volume", 30)
                self.assertTrue(entered.wait(1))
                latter = pool.submit(second)
                self.assertTrue(second_started.wait(1))
                self.assertFalse(latter.done())
                release.set()
                self.assertEqual(first.result(timeout=2).status, "ok")
                self.assertEqual(latter.result(timeout=2).status, "ok")


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
        self.assertEqual(run.call_args.args[0], [
            "/usr/bin/notify-send", "--app-name=RiceBowl", "--", "-looks-like-option", "Hello"])
        self.assertEqual(run.call_args.kwargs["timeout"], 4)
        with self.assertRaises(ValueError):
            pop.send("x" * 161)

    def test_missing_host_is_not_silently_faked(self):
        with patch.object(pop.shutil, "which", return_value=None):
            with self.assertRaises(pop.NotificationUnavailable):
                pop.send("Test")

    def test_status_degrades_without_history_and_rejects_bad_identifiers(self):
        with patch.object(pop.xfce, "read_dnd", return_value=None), \
             patch.object(pop.xfce, "has_unread", side_effect=pop.NotificationUnavailable("No log")):
            state = pop.status()
        self.assertFalse(state.history_available)
        self.assertIsNone(state.unread)
        with self.assertRaises(ValueError):
            pop.dismiss("bad\nidentifier")
        with self.assertRaises(ValueError):
            pop.mark_read(tuple(str(i) for i in range(pop.xfce.MAX_ITEMS + 1)))


class PlateTests(unittest.TestCase):
    def test_riceplate_stylesheet_is_valid_gtk_css_without_display(self):
        from macrice.riceware.plate_preview import canvas_stylesheet

        try:
            import gi
        except ImportError:
            self.skipTest("GTK introspection unavailable")
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        provider = Gtk.CssProvider()
        provider.load_from_data(canvas_stylesheet("#194da1", "#ffffff", "#316ac5", 5))

    def test_each_rice_has_a_distinct_desktop_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(plate.appearance("winclassic", config_root=root).family, "win98")
            self.assertEqual(plate.appearance("winclassic", config_root=root).icon_size, 32)
            self.assertEqual(plate.appearance("night", config_root=root).placement, "right")
            self.assertFalse(plate.appearance("chromeos", config_root=root).show_icons)
            self.assertTrue(plate.appearance("winxp", config_root=root).show_icons)
            with self.assertRaises(ValueError):
                plate.appearance("unrecognized", config_root=root)

    def test_desktop_preferences_are_explicit_per_style_and_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            previous = plate.appearance("winxp", config_root=root)
            self.assertEqual(previous.icon_size, 48)
            saved = plate.save_appearance("winxp", config_root=root,
                                          icon_size=64, show_hidden=True,
                                          placement="right", show_icons=True)
            self.assertEqual(saved.icon_size, 64)
            self.assertEqual(saved.placement, "right")
            self.assertTrue(saved.show_hidden)
            self.assertEqual(plate.appearance("winxp", config_root=root), saved)
            self.assertEqual(plate.appearance("frutiger", config_root=root).placement, "left")
            target = root / "ricebowl/plate.json"
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            raw = target.read_bytes()
            with self.assertRaises(ValueError):
                plate.save_appearance("winxp", config_root=root, icon_size=999)
            with self.assertRaises(ValueError):
                plate.save_appearance("winxp", config_root=root, show_hidden="no")
            self.assertEqual(target.read_bytes(), raw)

    def test_desktop_preferences_refuse_symlinked_locations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "personal.json"
            target.write_text('{"important":true}', encoding="utf-8")
            folder = root / "ricebowl"
            folder.mkdir()
            (folder / "plate.json").symlink_to(target)
            with self.assertRaises(ValueError):
                plate.appearance("winxp", config_root=root)
            with self.assertRaises(ValueError):
                plate.save_appearance("winxp", config_root=root, icon_size=64)
            self.assertEqual(target.read_text(), '{"important":true}')

    def test_riceplate_preview_filters_hidden_rows_without_mutations(self):
        from macrice.riceware.plate_preview import visible_items

        view = plate.DesktopSnapshot("/tmp/Desktop", True, (
            plate.DesktopItem("notes.txt", "/tmp/Desktop/notes.txt", "file"),
            plate.DesktopItem(".private", "/tmp/Desktop/.private", "file"),
            plate.DesktopItem("hidden.desktop", "/tmp/Desktop/hidden.desktop", "launcher",
                              hidden=True),
        ))
        with tempfile.TemporaryDirectory() as tmp:
            prefs = plate.appearance("winxp", config_root=Path(tmp))
        self.assertEqual([row.filename for row in visible_items(view, prefs)], ["notes.txt"])
        self.assertEqual(len(visible_items(view, plate.DesktopAppearance(
            "winxp", "winxp", 48, "left", True, True))), 3)
        self.assertEqual(visible_items(view, plate.DesktopAppearance(
            "chromeos", "chromeos", 48, "left", False, True)), ())

    def test_plate_preview_cli_is_opt_in_and_does_not_apply_a_rice(self):
        with patch("macrice.riceware.plate_preview.run", return_value=0) as preview:
            self.assertEqual(cli.main(["riceware", "plate", "preview", "--style", "frutiger"]), 0)
        preview.assert_called_once_with("frutiger")

    def test_read_only_snapshot_never_follows_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "a.desktop").write_text("shortcut", encoding="utf-8")
            (folder / "b").mkdir()
            (folder / "c").symlink_to(folder / "a.desktop")
            view = plate.snapshot(folder)
            self.assertEqual([item.kind for item in view.items], ["launcher", "directory", "link"])
            self.assertFalse(view.truncated)
            self.assertTrue(plate.snapshot(folder, limit=2).truncated)
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

            def boot(_args, **kwargs):
                (Path(kwargs["env"]["WINEPREFIX"]) / "system.reg").write_text("registry")
                return Mock(wait=Mock(return_value=0), pid=4321)

            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", side_effect=lambda name: "/usr/bin/" + name), \
                 patch.object(wine.subprocess, "Popen", side_effect=boot) as run:
                created = wine.create_prefix("game_1", store=folder)
            self.assertTrue(created.ready)
            self.assertTrue((folder / "game_1" / wine.MARKER).is_file())
            self.assertFalse((folder / "game_1" / wine.MARKER).stat().st_mode & stat.S_IRWXO)
            self.assertEqual(run.call_args.kwargs["env"]["WINEPREFIX"], str(folder / "game_1"))
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wine"), \
                 patch.object(wine.subprocess, "Popen", return_value=Mock(
                     pid=12345, wait=Mock(side_effect=subprocess.TimeoutExpired(
                         "wine", 0.15)))) as launch:
                self.assertEqual(wine.launch("game_1", "setup.exe", ("/silent",), store=folder), 12345)
            self.assertEqual(launch.call_args.args[0], ["/usr/bin/wine", "setup.exe", "/silent"])
            self.assertTrue(launch.call_args.kwargs["start_new_session"])
            self.assertEqual([p.name for p in wine.list_prefixes(store=folder)], ["game_1"])
            self.assertEqual(wine.read_init_log("game_1", store=folder), "")
            (folder / "game_1" / wine.INIT_LOG).write_bytes(b"warning\x1b[31m\n")
            self.assertEqual(wine.read_init_log("game_1", store=folder), "warning[31m\n")

    def test_failed_creation_preserves_diagnostics_but_cannot_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wineboot"), \
                 patch.object(wine.subprocess, "Popen", return_value=Mock(wait=Mock(return_value=1))):
                with self.assertRaises(RuntimeError):
                    wine.create_prefix("broken", store=folder)
            self.assertTrue((folder / "broken" / ".ricewine-init.log").exists())
            self.assertFalse(wine.list_prefixes(store=folder)[0].ready)
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wine"):
                with self.assertRaises(RuntimeError):
                    wine.launch("broken", "setup.exe", store=folder)

            def complete(_args, **kwargs):
                (Path(kwargs["env"]["WINEPREFIX"]) / "system.reg").write_text("registry")
                return Mock(wait=Mock(return_value=0))

            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wineboot"), \
                 patch.object(wine.subprocess, "Popen", side_effect=complete):
                self.assertTrue(wine.resume_prefix("broken", store=folder).ready)
                with self.assertRaises(RuntimeError):
                    wine.resume_prefix("broken", store=folder)

    def test_successful_exit_without_registry_is_not_a_ready_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wineboot"), \
                 patch.object(wine.subprocess, "Popen", return_value=Mock(wait=Mock(return_value=0))):
                with self.assertRaisesRegex(RuntimeError, "no registry"):
                    wine.create_prefix("empty", store=Path(tmp) / "prefixes")

    def test_timeout_kills_only_own_initialization_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Mock(pid=4242, wait=Mock(side_effect=[
                subprocess.TimeoutExpired("wineboot", 5), 0]))
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wineboot"), \
                 patch.object(wine.subprocess, "Popen", return_value=process), \
                 patch.object(wine.os, "killpg") as killed:
                with self.assertRaisesRegex(RuntimeError, "timed out"):
                    wine.create_prefix("slow", store=Path(tmp) / "prefixes", timeout=5)
            killed.assert_called_once_with(4242, wine.signal.SIGKILL)

    def test_cancelled_init_stops_only_its_child_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            process = Mock(pid=4545, wait=Mock(side_effect=[KeyboardInterrupt(), 0]))
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wineboot"), \
                 patch.object(wine.subprocess, "Popen", return_value=process), \
                 patch.object(wine.os, "killpg") as killed:
                with self.assertRaisesRegex(RuntimeError, "cancelled"):
                    wine.create_prefix("stopped", store=Path(tmp) / "prefixes")
            killed.assert_called_once_with(4545, wine.signal.SIGKILL)

    def test_invalid_timeout_does_not_create_partial_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            with self.assertRaises(ValueError):
                wine.create_prefix("broken", store=folder, timeout=-1)
            self.assertFalse(folder.exists())

    def test_bad_prefix_permissions_do_not_hide_other_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            folder.mkdir(mode=0o700)
            bad = folder / "exposed"
            bad.mkdir(mode=0o755)
            (folder / "safe").mkdir(mode=0o700)
            states = {item.name: item for item in wine.list_prefixes(store=folder)}
            self.assertIn("exposed", states)
            self.assertIsNotNone(states["exposed"].issue)
            self.assertIsNone(states["safe"].issue)

    def test_immediate_wine_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "prefixes"
            folder.mkdir(mode=0o700)
            prefix = folder / "game"
            prefix.mkdir(mode=0o700)
            (prefix / wine.MARKER).write_text("managed")
            (prefix / "system.reg").write_text("registry")
            with patch.object(wine.os, "geteuid", return_value=1000), \
                 patch.object(wine.shutil, "which", return_value="/usr/bin/wine"), \
                 patch.object(wine.subprocess, "Popen", return_value=Mock(wait=Mock(return_value=1))):
                with self.assertRaisesRegex(RuntimeError, "status 1"):
                    wine.launch("game", "broken.exe", store=folder)

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

    def test_notification_history_clear_requires_confirmation(self):
        with patch.object(pop, "clear_history") as clear, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["riceware", "pop", "clear"]), 1)
            clear.assert_not_called()
            self.assertEqual(cli.main(["riceware", "pop", "clear", "--yes"]), 0)
            clear.assert_called_once()
            self.assertEqual(cli.main(["riceware", "pop", "clear", "unexpected", "--yes"]), 1)
            clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
