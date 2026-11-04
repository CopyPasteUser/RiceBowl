"""ChromeOS Riceware migration tests without devices or a GTK display."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from macrice.chrome_riceware import ChromeController, ChromeHardware, READS, WRITES
from macrice.chrome_settings import NATIVE_DETAILS
from macrice.hardware_status import BluetoothState, SoundState
from macrice.frutiger_native_controls import NativeAquaControls
from macrice.riceware import spice
from macrice.riceware.worker import Response


ROOT = Path(__file__).resolve().parents[1]


class FakeRunner:
    def __init__(self):
        self.requests = []
        self.closed = False

    def submit(self, key, operation, callback):
        self.requests.append((key, operation, callback))

    def deliver(self, error=None):
        key, operation, callback = self.requests.pop(0)
        callback(Response(key, 1, error=error, value=None if error else operation()))

    def close(self):
        self.closed = True


class ChromeHardwareTests(unittest.TestCase):
    def setUp(self):
        self.backend = ChromeHardware()

    def test_capability_mapping_is_allowlisted_and_does_not_probe_on_import(self):
        self.assertGreaterEqual(len(READS), 8)
        self.assertGreaterEqual(len(WRITES), 10)
        with self.assertRaises(AttributeError):
            self.backend.run_shell_command

    def test_unknown_or_absent_device_is_not_presented_as_working(self):
        with patch("macrice.chrome_riceware.spice.read",
                   return_value=spice.Result("bluetooth", "unavailable")):
            self.assertEqual(self.backend.read_bluetooth(), BluetoothState(None, ()))
        with patch("macrice.chrome_riceware.spice.read",
                   return_value=spice.Result("audio", "unavailable")):
            self.assertEqual(self.backend.read_sound(), SoundState(None, None))
        with patch("macrice.chrome_riceware.spice.read",
                   return_value=spice.Result("battery", "unavailable")):
            self.assertIsNone(self.backend.read_battery())

    def test_read_errors_raise_and_success_uses_real_value(self):
        with patch("macrice.chrome_riceware.spice.read",
                   return_value=spice.Result("wifi", "error", reason="NetworkManager denied")):
            with self.assertRaisesRegex(RuntimeError, "denied"):
                self.backend.read_wifi_radio()
        with patch("macrice.chrome_riceware.spice.read",
                   return_value=spice.Result("wifi", "ok", True)) as read:
            self.assertIs(self.backend.read_wifi_radio(), True)
            read.assert_called_once_with("wifi")

    def test_write_requires_spice_verification(self):
        with patch("macrice.chrome_riceware.spice.change",
                   return_value=spice.Result("wifi", "error", reason="Unverified")) as change:
            with self.assertRaisesRegex(RuntimeError, "Unverified"):
                self.backend.set_wifi_radio(True)
            change.assert_called_once_with("wifi", True)
        state = SoundState(64, False)
        with patch("macrice.chrome_riceware.spice.change",
                   return_value=spice.Result("audio_volume", "ok", state)):
            self.assertEqual(self.backend.set_sound_volume(64), state)

    def test_bluetooth_connection_input_and_verified_write(self):
        with self.assertRaises(ValueError):
            self.backend.set_bluetooth_connection("00:11:22:33:44:55", "yes")
        with patch("macrice.chrome_riceware.spice.change",
                   return_value=spice.Result("bluetooth_connect", "ok", object())) as change:
            self.backend.set_bluetooth_connection("00:11:22:33:44:55", True)
            change.assert_called_once_with("bluetooth_connect", "00:11:22:33:44:55")


class ChromeControllerTests(unittest.TestCase):
    def setUp(self):
        self.runner = FakeRunner()
        self.controller = ChromeController(object(), runner=self.runner)

    def tearDown(self):
        self.controller.close()

    def test_desktop_status_and_audio_are_verified(self):
        values = []
        device = object()
        with patch("macrice.chrome_riceware.spice.read",
                   return_value=spice.Result("desktop_status", "ok", device)):
            self.controller.refresh_status(values.append)
            self.assertEqual(self.runner.requests[0][0], "chrome-desktop-status")
            self.runner.deliver()
        self.assertEqual(values, [device])
        with patch("macrice.chrome_riceware.spice.change",
                   return_value=spice.Result("audio_mute", "error", reason="Readback mismatch")):
            self.controller.change_audio("audio_mute", True,
                                         lambda value, error: values.append((value, error)))
            self.runner.deliver()
        self.assertEqual(values[-1], (None, "Readback mismatch"))

    def test_worker_error_and_close_suppress_stale_ui(self):
        values = []
        self.controller.submit("sample", lambda: 1, values.append)
        self.runner.deliver(error="Backend crashed")
        self.assertEqual(values[0].error, "Backend crashed")
        self.controller.submit("sample", lambda: 2, values.append)
        self.controller.close()
        self.runner.deliver()
        self.assertEqual(len(values), 1)
        self.assertTrue(self.runner.closed)

    def test_native_settings_are_independent_of_linux_tool_availability(self):
        self.assertEqual(NATIVE_DETAILS["Connections"], ("wifi",))
        self.assertEqual(NATIVE_DETAILS["Sound"], ("output_sound", "audio_devices"))
        self.assertEqual(NATIVE_DETAILS["Power"], ("battery", "power"))
        self.assertNotIn("VPN", NATIVE_DETAILS)  # Advanced XFCE utility required.
        settings = (ROOT / "macrice/chrome_settings.py").read_text()
        quick = (ROOT / "macrice/chrome_quick_settings.py").read_text()
        notifications = (ROOT / "macrice/chrome_notifications.py").read_text()
        self.assertIn("backend=self.shell.chrome_controller.hardware", settings)
        self.assertIn("backend=shell.chrome_controller.hardware", quick)
        self.assertIn("pop.history()", notifications)
        self.assertNotIn("threading.Thread", notifications)

    def test_hidden_device_page_drops_stale_response_without_resetting_new_busy_state(self):
        runner = FakeRunner()
        panel = NativeAquaControls.__new__(NativeAquaControls)
        panel._generation = 0
        panel._disposed = False
        panel._busy = False
        panel._debounce = 0
        panel._interactive = []
        panel.runner = runner
        panel.GLib = SimpleNamespace(source_remove=lambda _source: None)
        panel.is_current = lambda: True
        values = []
        panel._reader = lambda: 30
        panel._renderer = values.append
        panel._status = lambda _message, **_kwargs: None

        panel.refresh()
        self.assertTrue(panel._busy)
        panel.suspend()
        panel._reader = lambda: 42
        panel.refresh()
        runner.deliver()  # Old page read returns; must not clear new busy flag.
        self.assertTrue(panel._busy)
        self.assertEqual(values, [])
        runner.deliver()
        self.assertEqual(values, [42])
        self.assertFalse(panel._busy)

        panel.refresh()
        panel.dispose()
        runner.deliver()
        self.assertEqual(values, [42])


if __name__ == "__main__":
    unittest.main()
