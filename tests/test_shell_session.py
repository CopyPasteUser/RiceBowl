"""Session switching regression tests (no actual desktop processes are touched)."""
import unittest
from unittest import mock
from macrice import shell_session as s

class SessionTests(unittest.TestCase):
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
    @mock.patch.object(s, "_macbar_running", return_value=False)
    @mock.patch.object(s.subprocess, "run", return_value=mock.Mock(returncode=0))
    @mock.patch.object(s.shutil, "which", return_value="/usr/bin/gapplication")
    def test_running_python_macbar_is_quit_over_bus(self, which, run, process, bus):
        self.assertEqual(s._stop_macbar(), [])
        run.assert_called_once_with(
            ["gapplication", "quit", s.MACBAR_APP_ID],
            capture_output=True, text=True, timeout=4, check=False)
        self.assertEqual(bus.call_count, 2)

    @mock.patch.object(s, "_macbar_bus_owned", return_value=None)
    @mock.patch.object(s, "_macbar_running", side_effect=[True, False])
    @mock.patch.object(s.subprocess, "run", return_value=mock.Mock(returncode=0))
    @mock.patch.object(s.shutil, "which", return_value="/usr/bin/gapplication")
    def test_python_process_fallback_if_bus_unavailable(self, which, run, process, bus):
        self.assertEqual(s._stop_macbar(), [])
        self.assertEqual(process.call_count, 2)

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

if __name__ == "__main__":
    unittest.main()
