"""Session switching regression tests (no actual desktop processes are touched)."""
import unittest
import os
import tempfile
import sys
import types
from pathlib import Path
from unittest import mock
from macrice import shell_session as s

class SessionTests(unittest.TestCase):
    def setUp(self):
        controls = mock.patch.object(s, "_activate_session_controls", return_value=[])
        self.controls = controls.start()
        self.addCleanup(controls.stop)
        ready = mock.patch.object(s, "_wait_for_shell_ready", return_value=True)
        self.ready = ready.start()
        self.addCleanup(ready.stop)

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_start", return_value=[])
    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    @mock.patch.object(s.shutil, "which", return_value="/usr/bin/example")
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    def test_mac_to_aero_stops_plank_and_macbar(self, stop_macbar, which, shell, stop, start):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ())
        self.assertEqual([c.args[0] for c in stop.call_args_list], ["plank"])
        stop_macbar.assert_called_once_with()
        self.assertEqual(shell.call_args_list[-1], mock.call("aero", False))
        start.assert_not_called()

    @mock.patch.object(s, "_macbar_bus_owned", return_value=False)
    @mock.patch.object(s, "_macbar_running", return_value=False)
    @mock.patch.object(s.subprocess, "run")
    def test_absent_macbar_does_not_block_windows(self, run, process, bus):
        self.assertEqual(s._stop_macbar(), [])
        run.assert_not_called()

    @mock.patch.object(s, "_processes", return_value=[])
    @mock.patch.object(s.os, "kill")
    def test_absent_plank_does_not_poll_or_send_signals(self, kill, processes):
        self.assertEqual(s._stop("plank"), [])
        processes.assert_called_once_with("plank")
        kill.assert_not_called()

    @mock.patch.object(s, "_macbar_bus_owned", side_effect=[True, False])
    @mock.patch.object(s, "_macbar_running", side_effect=[True, False])
    @mock.patch.object(s, "_macbar_owner_pid", return_value=371)
    @mock.patch.object(s, "_managed_macbar_pids", return_value=[])
    @mock.patch.object(s.os, "kill")
    @mock.patch.object(s.subprocess, "run")
    def test_macbar_bus_owner_is_stopped_by_verified_pid(self, run, kill, managed, owner, process, bus):
        self.assertEqual(s._stop_macbar(), [])
        kill.assert_called_once_with(371, s.signal.SIGTERM)
        run.assert_not_called()
        self.assertEqual(bus.call_count, 2)

    @mock.patch.object(s, "_macbar_bus_owned", return_value=None)
    @mock.patch.object(s, "_macbar_running", side_effect=[True, False])
    @mock.patch.object(s, "_macbar_owner_pid", return_value=None)
    @mock.patch.object(s, "_managed_macbar_pids", return_value=[372])
    @mock.patch.object(s.os, "kill")
    def test_managed_python_process_fallback_if_bus_unavailable(self, kill, managed, owner, process, bus):
        self.assertEqual(s._stop_macbar(), [])
        kill.assert_called_once_with(372, s.signal.SIGTERM)
        self.assertEqual(process.call_count, 2)

    @mock.patch.object(s, "_macbar_bus_owned", return_value=True)
    @mock.patch.object(s, "_macbar_running", return_value=True)
    @mock.patch.object(s, "_macbar_owner_pid", return_value=None)
    @mock.patch.object(s, "_managed_macbar_pids", return_value=[])
    @mock.patch.object(s.os, "kill")
    def test_unverified_macbar_process_is_never_signalled(self, kill, managed, owner, process, bus):
        self.assertIn("could not verify", s._stop_macbar()[0])
        kill.assert_not_called()

    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    @mock.patch.object(s, "_stop_macbar", return_value=["MacBar is still running"])
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    def test_macbar_failure_blocks_new_windows_shell(self, recover, stop_macbar, shell, stop):
        with mock.patch.dict("os.environ", {"DISPLAY": ":99"}):
            self.assertEqual(s.sync_theme("RiceHub-Aero"), ("MacBar is still running",))
        self.assertNotIn(mock.call("aero", False), shell.call_args_list)
        recover.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_start", return_value=[])
    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    @mock.patch.object(s.shutil, "which", return_value="/usr/bin/example")
    def test_aero_to_mac_starts_both(self, which, shell, stop, start):
        self.assertEqual(s.sync_theme("WhiteSur-Light"), ())
        self.assertEqual([c.args[0] for c in start.call_args_list], ["plank", "macbar"])
        stop.assert_not_called()

    def test_macbar_launcher_is_resolved_outside_gui_path(self):
        """XFCE-launched RiceHub may not have ~/.local/bin in PATH."""
        with tempfile.TemporaryDirectory() as temporary:
            local_bin = Path(temporary)
            launcher = local_bin / "macbar"
            launcher.write_text("#!/bin/sh\nexit 0\n")
            launcher.chmod(0o755)
            with mock.patch.dict(os.environ, {"DISPLAY": ":99"}), \
                 mock.patch.object(s, "bin_home", return_value=local_bin), \
                 mock.patch.object(s.shutil, "which", side_effect=lambda name:
                                   "/usr/bin/plank" if name == "plank" else None), \
                 mock.patch.object(s, "_shell", return_value=[]), \
                 mock.patch.object(s, "_start", return_value=[]) as start:
                self.assertEqual(s.sync_theme("WhiteSur-Dark"), ())
            self.assertEqual(start.call_args_list, [
                mock.call("plank", ["/usr/bin/plank"]),
                mock.call("macbar", [str(launcher)]),
            ])

    @mock.patch.dict("os.environ", {}, clear=True)
    @mock.patch.object(s, "_stop")
    def test_no_display_no_actions(self, stop):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ())
        stop.assert_not_called()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    def test_restoring_unmanaged_xfce_theme_recovers_panel_and_shortcuts(self, shell, recover):
        self.assertEqual(s.sync_theme("Mint-Y"), ())
        recover.assert_called_once_with()
        self.assertEqual([call.args[1] for call in shell.call_args_list],
                         [True] * len(s.SHELLS))
        self.controls.assert_not_called()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_recover_xfce_panel", return_value=["XFCE panel cannot start"])
    @mock.patch.object(s, "_shell", return_value=[])
    def test_restore_reports_stock_panel_recovery_failure(self, shell, recover):
        self.assertEqual(s.sync_theme("Mint-Y"), ("XFCE panel cannot start",))
        self.controls.assert_not_called()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_stop", return_value=["plank did not exit"])
    @mock.patch.object(s, "_shell", return_value=[])
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    def test_stop_failure_blocks_new_shell(self, recover, stop_macbar, shell, stop):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ("plank did not exit",))
        self.assertNotIn(mock.call("aero", False), shell.call_args_list)
        recover.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_shell", side_effect=lambda profile, quit:
                       ["shell quit failed"] if quit else [])
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    def test_restore_recovers_panel_even_when_old_shell_wont_quit(self, recover, shell):
        self.assertIn("shell quit failed", s.sync_theme("Mint-Y"))
        recover.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", side_effect=lambda profile, quit:
                       ["new shell could not launch"] if not quit else [])
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    def test_shell_spawn_failure_still_recovers_panel(self, recover, shell, stop, macbar):
        self.assertIn("new shell could not launch", s.sync_theme("RiceHub-Aero"))
        recover.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    def test_stock_panel_retirement_failure_closes_replacement(self, recover, shell, stop, macbar):
        self.controls.return_value = ["panel quit failed"]
        self.assertIn("panel quit failed", s.sync_theme("RiceHub-Aero"))
        self.assertIn(mock.call("aero", True), shell.call_args_list)
        recover.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_recover_xfce_panel", return_value=[])
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    def test_unready_shell_does_not_quit_xfce_panel(self, shell, stop, stop_macbar, fallback):
        self.ready.return_value = False
        result = s.sync_theme("RiceHub-Aero")
        self.assertTrue(any("not ready" in warning for warning in result))
        self.controls.assert_not_called()
        fallback.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    @mock.patch.object(s, "_stop", return_value=[])
    @mock.patch.object(s, "_shell", return_value=[])
    def test_shell_ready_before_original_panel_is_retired(self, shell, stop, stop_macbar):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ())
        self.ready.assert_called_once_with("aero")
        self.controls.assert_called_once_with("RiceHub-Aero")

    def test_all_shells_have_their_existing_dbus_application_id(self):
        self.assertEqual(s._shell_app_id("aero"), "io.github.copypasteuser.RiceHub.AeroShell")
        self.assertEqual(s._shell_app_id("ten"), "io.github.copypasteuser.RiceHub.TenShell")
        for profile in ("winxp", "winclassic", "chromeos", "frutiger"):
            self.assertEqual(s._shell_app_id(profile),
                             f"io.github.copypasteuser.RiceHub.{profile.title()}Shell")

    @mock.patch.object(s, "_shell_process_active", return_value=False)
    @mock.patch.object(s, "_shell_bus_owned", return_value=False)
    @mock.patch.object(s.subprocess, "run")
    def test_absent_shell_quit_does_not_spawn_python(self, run, bus, active):
        self.assertEqual(s._shell("frutiger", True), [])
        bus.assert_called_once_with("frutiger")
        active.assert_called_once_with("frutiger")
        run.assert_not_called()

    @mock.patch.object(s, "_shell_process_active", return_value=True)
    @mock.patch.object(s, "_shell_bus_owned", return_value=False)
    @mock.patch.object(s.subprocess, "run", return_value=mock.Mock(returncode=0))
    def test_starting_shell_is_still_asked_to_quit(self, run, bus, active):
        self.assertEqual(s._shell("winxp", True), [])
        run.assert_called_once()
        self.assertEqual(run.call_args.args[0][-2:], ["winxp-shell", "--quit"])

    @mock.patch.object(s, "_shell_process_active")
    @mock.patch.object(s, "_shell_bus_owned", return_value=None)
    @mock.patch.object(s.subprocess, "run", return_value=mock.Mock(returncode=0))
    def test_unavailable_bus_keeps_conservative_quit(self, run, bus, active):
        self.assertEqual(s._shell("chromeos", True), [])
        run.assert_called_once()
        active.assert_not_called()

    def test_inflight_shell_process_is_detected_before_dbus_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "23791"
            proc.mkdir()
            (proc / "cmdline").write_bytes(
                b"/usr/bin/python3\0/opt/ricebowl/launcher.py\0frutiger-shell\0")
            self.assertTrue(s._shell_process_active("frutiger", proc_root=Path(tmp)))
            self.assertFalse(s._shell_process_active("winxp", proc_root=Path(tmp)))

    def test_bus_owner_check_uses_exact_shell_application_name(self):
        connection = mock.Mock()
        connection.call_sync.return_value.unpack.return_value = (False,)
        gio = types.SimpleNamespace(BusType=types.SimpleNamespace(SESSION=0),
                                    DBusCallFlags=types.SimpleNamespace(NONE=0),
                                    bus_get_sync=mock.Mock(return_value=connection))
        gi = types.ModuleType("gi")
        gi.require_version = mock.Mock()
        gi.repository = types.ModuleType("gi.repository")
        gi.repository.Gio = gio
        gi.repository.GLib = types.SimpleNamespace(Variant=lambda sig, value: (sig, value),
                                                   VariantType=lambda signature: signature)
        with mock.patch.dict(sys.modules, {"gi": gi, "gi.repository": gi.repository}):
            self.assertIs(s._shell_bus_owned("chromeos"), False)
            self.assertEqual(connection.call_sync.call_args.args[:4],
                             ("org.freedesktop.DBus", "/org/freedesktop/DBus",
                              "org.freedesktop.DBus", "NameHasOwner"))
            self.assertEqual(connection.call_sync.call_args.args[4],
                             ("(s)", ("io.github.copypasteuser.RiceHub.ChromeosShell",)))
            self.assertEqual(connection.call_sync.call_args.args[7], 500)
            connection.call_sync.side_effect = OSError("bus disconnected")
            self.assertIsNone(s._shell_bus_owned("chromeos"))

    def test_readiness_requires_gtk_action_on_the_correct_dbus_path(self):
        connection = mock.Mock()
        connection.call_sync.return_value.unpack.return_value = (["toggle-menu", "ricebowl-ready"],)
        gio = types.SimpleNamespace(BusType=types.SimpleNamespace(SESSION=0),
                                    DBusCallFlags=types.SimpleNamespace(NONE=0),
                                    VariantType=lambda signature: signature,
                                    bus_get_sync=mock.Mock(return_value=connection))
        gi = types.ModuleType("gi")
        gi.require_version = mock.Mock()
        gi.repository = types.ModuleType("gi.repository")
        gi.repository.Gio = gio
        gi.repository.GLib = types.SimpleNamespace(VariantType=lambda signature: signature)
        with mock.patch.dict(sys.modules, {"gi": gi, "gi.repository": gi.repository}):
            self.assertTrue(s._shell_ready("winxp"))
            self.assertEqual(connection.call_sync.call_args.args[:4], (
                "io.github.copypasteuser.RiceHub.WinxpShell",
                "/io/github/copypasteuser/RiceHub/WinxpShell", "org.gtk.Actions", "List"))
            connection.call_sync.return_value.unpack.return_value = (["toggle-menu"],)
            self.assertFalse(s._shell_ready("winxp"))

    @mock.patch.object(s, "_start", return_value=[])
    @mock.patch.object(s.shutil, "which", return_value="/usr/bin/xfce4-panel")
    def test_failure_recovers_stock_panel_and_saved_shortcuts(self, which, start):
        with mock.patch("macrice.session_shortcuts.restore_bindings", return_value=()) as restore:
            self.assertEqual(s._recover_xfce_panel(), [])
        start.assert_called_once_with("xfce4-panel", ["/usr/bin/xfce4-panel"])
        restore.assert_called_once_with()

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    def test_all_six_rices_switch_sequentially_and_restore_stock_panel(self):
        """Model a live session, rather than testing six isolated launches."""
        active = set()
        panel = {"running": True}
        recovered = []

        def shell(profile, quit):
            if quit:
                active.discard(profile)
            else:
                active.add(profile)
            return []

        def handoff(theme):
            self.assertEqual(len(active), 1, theme)
            panel["running"] = False
            return []

        def recover():
            panel["running"] = True
            recovered.append(tuple(sorted(active)))
            return []

        sequences = (
            ("RiceHub-Luna", "winxp"),
            ("RiceHub-Aero", "aero"),
            ("RiceHub-Ten-Dark", "ten"),
            ("RiceHub-Chrome", "chromeos"),
            ("RiceHub-Classic", "winclassic"),
            ("RiceHub-Frutiger", "frutiger"),
            ("RiceHub-Luna", "winxp"),
        )
        with mock.patch.object(s, "_shell", side_effect=shell), \
             mock.patch.object(s, "_stop", return_value=[]), \
             mock.patch.object(s, "_stop_macbar", return_value=[]), \
             mock.patch.object(s, "_activate_session_controls", side_effect=handoff), \
             mock.patch.object(s, "_recover_xfce_panel", side_effect=recover):
            for theme, expected in sequences:
                self.assertEqual(s.sync_theme(theme), ())
                self.assertEqual(active, {expected})
                self.assertFalse(panel["running"])
            self.assertEqual(s.sync_theme("Mint-Y"), ())
        self.assertEqual(active, set())
        self.assertTrue(panel["running"])
        self.assertEqual(recovered, [()])

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    def test_failed_mid_sequence_handoff_terminates_failed_shell_and_recovers(self):
        active = set()
        panel = {"running": True}

        def shell(profile, quit):
            if quit:
                active.discard(profile)
            else:
                active.add(profile)
            return []

        def handoff(theme):
            if theme == "RiceHub-Chrome":
                return ["panel handoff failed"]
            panel["running"] = False
            return []

        def recover():
            panel["running"] = True
            return []

        with mock.patch.object(s, "_shell", side_effect=shell), \
             mock.patch.object(s, "_stop", return_value=[]), \
             mock.patch.object(s, "_stop_macbar", return_value=[]), \
             mock.patch.object(s, "_activate_session_controls", side_effect=handoff), \
             mock.patch.object(s, "_recover_xfce_panel", side_effect=recover):
            self.assertEqual(s.sync_theme("RiceHub-Frutiger"), ())
            self.assertEqual(active, {"frutiger"})
            self.assertFalse(panel["running"])
            self.assertIn("panel handoff failed", s.sync_theme("RiceHub-Chrome"))
            self.assertEqual(active, set())
            self.assertTrue(panel["running"])
            self.assertEqual(s.sync_theme("RiceHub-Aero"), ())
            self.assertEqual(active, {"aero"})


class PanelAndShortcutTests(unittest.TestCase):
    def test_taskbar_start_preserves_private_diagnostic_log(self):
        with tempfile.TemporaryDirectory() as temporary, \
             mock.patch.dict(os.environ, {"XDG_STATE_HOME": temporary}), \
             mock.patch.object(s.subprocess, "Popen") as process:
            self.assertEqual(s._shell("aero", False), [])
            log = Path(temporary) / "ricehub/aero-shell.log"
            self.assertTrue(log.exists())
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
        process.assert_called_once()
        self.assertEqual(process.call_args.kwargs["stderr"], s.subprocess.STDOUT)
        self.assertNotEqual(process.call_args.kwargs["stdout"], s.subprocess.DEVNULL)

    @mock.patch.object(s, "_processes", side_effect=[[1492], []])
    @mock.patch.object(s.shutil, "which", return_value="/usr/bin/xfce4-panel")
    @mock.patch.object(s.subprocess, "run", return_value=mock.Mock(returncode=0))
    def test_stock_xfce_panel_is_quit_gracefully(self, run, which, processes):
        self.assertEqual(s._stop_xfce_panel(), [])
        run.assert_called_once_with(["/usr/bin/xfce4-panel", "--quit"],
                                    capture_output=True, text=True, timeout=4, check=False)

    @mock.patch.object(s, "_stop_xfce_panel", return_value=[])
    def test_shortcuts_are_installed_before_panel_shutdown(self, panel):
        with mock.patch("macrice.session_shortcuts.install_bindings", return_value=()) as shortcuts:
            self.assertEqual(s._activate_session_controls("WhiteSur-Dark"), [])
        shortcuts.assert_called_once_with("WhiteSur-Dark")
        panel.assert_called_once_with()

    @mock.patch.object(s, "_stop_xfce_panel")
    def test_shortcut_failure_keeps_original_panel_running(self, panel):
        with mock.patch("macrice.session_shortcuts.install_bindings", side_effect=RuntimeError("write rejected")):
            errors = s._activate_session_controls("WhiteSur-Dark")
        self.assertIn("write rejected", errors[0])
        panel.assert_not_called()

if __name__ == "__main__":
    unittest.main()
