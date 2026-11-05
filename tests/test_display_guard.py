"""No real monitors are touched: the detached rollback contract is simulated."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice import display_guard, display_layout


OUTPUT = display_layout.DisplayOutput("eDP-1", "1920x1080", (0, 0), True,
                                     ("1920x1080", "1600x900", "1366x768"))


class GuardTests(unittest.TestCase):
    def _request(self, root: Path, *, name="eDP-1", mode="1600x900", x=10, y=0):
        change = display_guard.DisplayChange("a" * 32, root)
        display_guard._write_new(display_guard._request_path(change), {
            "name": name, "mode": mode, "x": x, "y": y,
            "old_mode": "1920x1080", "old_x": 0, "old_y": 0})
        return change

    def test_validation_refuses_disconnected_outputs_unlisted_modes_and_bad_coordinates(self):
        for name, mode, x, y in (("other", "1600x900", 0, 0),
                                  ("eDP-1", "800x600", 0, 0),
                                  ("eDP-1", "1600x900", 40000, 0),
                                  ("eDP-1", "1600x900", True, 0)):
            with self.subTest(name=name, mode=mode, x=x):
                with self.assertRaises(ValueError):
                    display_guard._validated_output(name, mode, x, y, (OUTPUT,))

    def test_request_spawns_independent_guard_and_requires_confirmation(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(display_guard.display_layout, "read_monitor_layout",
                                  return_value=(OUTPUT,)), \
                mock.patch.object(display_guard, "runtime_root", return_value=Path(root)), \
                mock.patch.object(display_guard.subprocess, "Popen") as spawn:
            change = display_guard.begin_change("eDP-1", "1600x900", -120, 15)
            self.assertTrue(display_guard._request_path(change).is_file())
            self.assertTrue(spawn.call_args.kwargs["start_new_session"])
            self.assertTrue(spawn.call_args.kwargs["close_fds"])
            self.assertEqual(spawn.call_args.args[0][1], str(Path(display_guard.__file__).resolve()))
            with self.assertRaisesRegex(RuntimeError, "not waiting"):
                display_guard.keep_change(change)
            display_guard._write_state(change, "pending", "Confirm")
            display_guard.keep_change(change)
            self.assertTrue(display_guard._keep_path(change).is_file())
            with self.assertRaises(FileExistsError):
                display_guard.keep_change(change)

    def test_unconfirmed_monitor_change_reverts_old_mode_and_position(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(display_guard.display_layout, "read_monitor_layout",
                                  return_value=(OUTPUT,)), \
                mock.patch.object(display_guard, "_run_xrandr") as run, \
                mock.patch.object(display_guard, "_check_current", return_value=True), \
                mock.patch.object(display_guard.time, "monotonic", side_effect=[0.0, 99.0]):
            change = self._request(Path(root))
            self.assertEqual(display_guard.run_worker(change), 1)
            self.assertEqual(run.call_args_list, [
                mock.call("eDP-1", "1600x900", 10, 0),
                mock.call("eDP-1", "1920x1080", 0, 0)])
            self.assertEqual(display_guard.read_status(change)[0], "reverted")
            self.assertFalse(display_guard._request_path(change).exists())

    def test_confirmed_monitor_change_keeps_mode_without_rollback(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(display_guard.display_layout, "read_monitor_layout",
                                  return_value=(OUTPUT,)), \
                mock.patch.object(display_guard, "_run_xrandr") as run, \
                mock.patch.object(display_guard, "_check_current", return_value=True):
            change = self._request(Path(root))
            original = display_guard._write_state

            def approve_after_pending(item, state, detail=""):
                original(item, state, detail)
                if state == "pending":
                    display_guard._write_new(display_guard._keep_path(item), {"keep": True})

            with mock.patch.object(display_guard, "_write_state", side_effect=approve_after_pending):
                self.assertEqual(display_guard.run_worker(change), 0)
            run.assert_called_once_with("eDP-1", "1600x900", 10, 0)
            self.assertEqual(display_guard.read_status(change)[0], "kept")

    def test_failed_apply_attempts_rollback_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(display_guard.display_layout, "read_monitor_layout",
                                  return_value=(OUTPUT,)), \
                mock.patch.object(display_guard, "_run_xrandr",
                                  side_effect=[RuntimeError("apply failed"), None]) as run, \
                mock.patch.object(display_guard, "_check_current", return_value=True):
            change = self._request(Path(root))
            self.assertEqual(display_guard.run_worker(change), 1)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(display_guard.read_status(change)[0], "reverted")

    def test_rollback_failure_is_reported_not_claimed_successful(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(display_guard.display_layout, "read_monitor_layout",
                                  return_value=(OUTPUT,)), \
                mock.patch.object(display_guard, "_run_xrandr",
                                  side_effect=[None, RuntimeError("X11 refused")]), \
                mock.patch.object(display_guard, "_check_current", return_value=True), \
                mock.patch.object(display_guard.time, "monotonic", side_effect=[0.0, 99.0]):
            change = self._request(Path(root))
            self.assertEqual(display_guard.run_worker(change), 1)
            self.assertEqual(display_guard.read_status(change), ("revert-failed", "X11 refused"))

    def test_confirmation_arriving_after_deadline_does_not_skip_rollback(self):
        with tempfile.TemporaryDirectory() as root, \
                mock.patch.object(display_guard.display_layout, "read_monitor_layout",
                                  return_value=(OUTPUT,)), \
                mock.patch.object(display_guard, "_run_xrandr") as run, \
                mock.patch.object(display_guard, "_check_current", return_value=True), \
                mock.patch.object(display_guard.time, "monotonic", side_effect=[0.0, 99.0]):
            change = self._request(Path(root))
            original = display_guard._write_state

            def late_confirm(item, state, detail=""):
                original(item, state, detail)
                if state == "pending":
                    display_guard._write_new(display_guard._keep_path(item), {"keep": True})

            with mock.patch.object(display_guard, "_write_state", side_effect=late_confirm):
                self.assertEqual(display_guard.run_worker(change), 1)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(display_guard.read_status(change)[0], "reverted")


if __name__ == "__main__":
    unittest.main()
