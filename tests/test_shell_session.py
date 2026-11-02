"""Session switching regression tests (no actual desktop processes are touched)."""
import unittest
import os
import tempfile
from pathlib import Path
from unittest import mock
from macrice import shell_session as s

class SessionTests(unittest.TestCase):
    def setUp(self):
        controls = mock.patch.object(s, "_activate_session_controls", return_value=[])
        self.controls = controls.start()
        self.addCleanup(controls.stop)

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
    def test_macbar_failure_blocks_new_windows_shell(self, stop_macbar, shell, stop):
        with mock.patch.dict("os.environ", {"DISPLAY": ":99"}):
            self.assertEqual(s.sync_theme("RiceHub-Aero"), ("MacBar is still running",))
        self.assertNotIn(mock.call("aero", False), shell.call_args_list)

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
    @mock.patch.object(s, "_stop", return_value=["plank did not exit"])
    @mock.patch.object(s, "_shell", return_value=[])
    @mock.patch.object(s, "_stop_macbar", return_value=[])
    def test_stop_failure_blocks_new_shell(self, stop_macbar, shell, stop):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ("plank did not exit",))
        self.assertNotIn(mock.call("aero", False), shell.call_args_list)


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
            self.assertEqual(s._activate_session_controls(), [])
        shortcuts.assert_called_once_with()
        panel.assert_called_once_with()

    @mock.patch.object(s, "_stop_xfce_panel")
    def test_shortcut_failure_keeps_original_panel_running(self, panel):
        with mock.patch("macrice.session_shortcuts.install_bindings", side_effect=RuntimeError("write rejected")):
            errors = s._activate_session_controls()
        self.assertIn("write rejected", errors[0])
        panel.assert_not_called()

if __name__ == "__main__":
    unittest.main()
