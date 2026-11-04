"""Hermetic Aqua World Riceware migration and lifecycle regressions."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from macrice.frutiger_riceware import FrutigerController
from macrice.frutiger_notifications import AquaNotifications, notification_preview
from macrice.frutiger_native_controls import build_native_controls
from macrice.riceware import spice
from macrice.riceware.native_hardware import RicewareHardware
from macrice.riceware.worker import Response


class FakeRunner:
    def __init__(self):
        self.requests = []
        self.closed = False

    def submit(self, key, operation, callback):
        self.requests.append((key, operation, callback))

    def deliver(self, *, error=None):
        key, operation, callback = self.requests.pop(0)
        callback(Response(key, 1, error=error,
                          value=None if error else operation()))

    def close(self):
        self.closed = True


class FrutigerRicewareTests(unittest.TestCase):
    def setUp(self):
        self.runner = FakeRunner()
        self.controller = FrutigerController(object(), runner=self.runner)

    def tearDown(self):
        self.controller.close()

    def test_status_and_audio_use_verified_spice(self):
        values = []
        device = object()
        with patch("macrice.frutiger_riceware.spice.read",
                   return_value=spice.Result("desktop_status", "ok", device)):
            self.controller.refresh_status(values.append)
            self.assertEqual(self.runner.requests[0][0], "frutiger-desktop-status")
            self.runner.deliver()
        self.assertEqual(values, [device])

        with patch("macrice.frutiger_riceware.spice.change",
                   return_value=spice.Result("audio_volume", "error",
                                             reason="Unverified volume")):
            self.controller.change_audio("audio_volume", 41,
                                         lambda state, error: values.append((state, error)))
            self.runner.deliver()
        self.assertEqual(values[-1], (None, "Unverified volume"))

    def test_unavailable_hardware_is_not_optimistically_enabled(self):
        backend = RicewareHardware()
        with patch("macrice.riceware.native_hardware.spice.read",
                   return_value=spice.Result("wifi", "unavailable")):
            self.assertIsNone(backend.read_wifi_radio())
        with patch("macrice.riceware.native_hardware.spice.change",
                   return_value=spice.Result("wifi", "error", reason="Denied")):
            with self.assertRaisesRegex(RuntimeError, "Denied"):
                backend.set_wifi_radio(False)

    def test_close_suppresses_in_flight_callbacks(self):
        values = []
        self.controller.refresh_status(values.append)
        self.controller.close()
        with patch("macrice.frutiger_riceware.spice.read",
                   return_value=spice.Result("desktop_status", "ok", object())):
            self.runner.deliver()
        self.assertEqual(values, [])
        self.assertTrue(self.runner.closed)

    def test_native_builder_injects_shared_backend_and_runner(self):
        fake_panel = Mock()
        backend = object()
        with patch("macrice.frutiger_native_controls.NativeAquaControls",
                   return_value=fake_panel) as construct:
            result = build_native_controls(None, None, None, None, "connections",
                                           "Network connections", is_current=lambda: True,
                                           backend=backend, runner=self.runner)
        self.assertIs(result, fake_panel)
        self.assertIs(construct.call_args.kwargs["backend"], backend)
        self.assertIs(construct.call_args.kwargs["runner"], self.runner)
        fake_panel.wifi.assert_called_once_with()


class AquaNotificationTests(unittest.TestCase):
    def test_preview_is_bounded_and_only_contains_text(self):
        entries = tuple(SimpleNamespace(application="App", summary="Subject " + str(i),
                                        is_read=bool(i % 2)) for i in range(32))
        result = notification_preview(entries)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0], ("App", "Subject 0", False))
        self.assertEqual(notification_preview(entries, limit=2)[-1][1], "Subject 1")

    def test_unavailable_notification_backend_does_not_enable_actions(self):
        display = AquaNotifications.__new__(AquaNotifications)
        display.controller = SimpleNamespace(submit=Mock())
        display._serial = 0
        display._busy = False
        display._syncing = False
        display._quiet = None
        display._history_available = False
        display.status = Mock()
        display.dnd = Mock()
        display.mark_read = Mock()
        display.entries = Mock()
        display.entries.get_children.return_value = ()
        display.popover = Mock()
        display.popover.get_visible.return_value = True
        display.Gtk = SimpleNamespace(Label=Mock(return_value=Mock()))
        runner = FakeRunner()
        display.controller.submit = runner.submit
        pop_status = SimpleNamespace(history_available=False, unread=None, quiet=None,
                                     reason="History disabled")
        with patch("macrice.frutiger_notifications.pop.status",
                   return_value=pop_status), patch(
                       "macrice.frutiger_notifications.pop.history") as history:
            display.refresh()
            runner.deliver()
            history.assert_not_called()
        self.assertIsNone(display._quiet)
        self.assertIs(pop_status.history_available, False)
        display.mark_read.set_sensitive.assert_called_with(False)
        display.dnd.set_sensitive.assert_called_with(False)

    def test_dnd_write_requires_real_backend_and_discards_stale_close(self):
        display = AquaNotifications.__new__(AquaNotifications)
        runner = FakeRunner()
        display.controller = SimpleNamespace(submit=runner.submit)
        display._serial = 0
        display._busy = False
        display._syncing = False
        display._quiet = False
        display._history_available = True
        display.dnd = Mock()
        display.mark_read = Mock()
        display.entries = Mock()
        display.entries.get_children.return_value = ()
        display.popover = Mock()
        display.popover.get_visible.return_value = True
        display.refresh = Mock()
        display._change_quiet(SimpleNamespace(get_active=lambda: True), None)
        with patch("macrice.frutiger_notifications.pop.set_quiet_mode", return_value=True) as write:
            # The callback is scheduled by the same bounded device worker.
            runner.deliver()
            write.assert_called_once_with(True)
        display.refresh.assert_called_once_with(feedback="Do Not Disturb updated")
        display._closed()
        self.assertIsNone(display._quiet)
        self.assertFalse(display._history_available)

        display._quiet = False
        display._change_quiet(SimpleNamespace(get_active=lambda: True), None)
        display._closed()
        with patch("macrice.frutiger_notifications.pop.set_quiet_mode", return_value=True):
            runner.deliver()
        # Closing the popover invalidates an in-flight action's UI callback.
        display.refresh.assert_called_once_with(feedback="Do Not Disturb updated")


if __name__ == "__main__":
    unittest.main()
