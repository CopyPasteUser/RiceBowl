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
    def test_mac_to_aero_stops_plank_and_macbar(self, which, shell, stop, start):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ())
        self.assertEqual([c.args[0] for c in stop.call_args_list], ["plank", "macbar"])
        self.assertEqual(shell.call_args_list[-1], mock.call("aero", False))
        start.assert_not_called()

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
    def test_stop_failure_blocks_new_shell(self, shell, stop):
        self.assertEqual(s.sync_theme("RiceHub-Aero"), ("plank did not exit",))
        self.assertNotIn(mock.call("aero", False), shell.call_args_list)

if __name__ == "__main__":
    unittest.main()
