"""Windows 7 consumes Riceware without losing its independent Aero renderer."""

import unittest
from unittest.mock import Mock, patch

from macrice.riceware import plate, spice
from macrice.win7_tray import Win7Tray
from tests.test_luna_riceware import tray


class Win7RicewareTests(unittest.TestCase):
    def test_aero_tray_keeps_distinct_renderer_and_shared_worker(self):
        aero = tray(Win7Tray)
        self.assertIsInstance(aero, Win7Tray)
        self.assertEqual(Win7Tray._audio.__qualname__, "Win7Tray._audio")
        self.assertEqual(Win7Tray.change_audio.__qualname__, "LunaTray.change_audio")
        done = Mock()
        with patch.object(spice, "change", return_value=spice.Result(
                "audio_volume", "ok", value="real sound state")) as write:
            aero.change_audio("audio_volume", 37, done)
        write.assert_called_once_with("audio_volume", 37)
        done.assert_called_once_with("real sound state", None)

    def test_aero_device_controls_reject_unverified_changes(self):
        aero = tray(Win7Tray)
        with patch.object(spice, "read", return_value=spice.Result("wifi", "ok", True)), \
             patch.object(spice, "change", return_value=spice.Result(
                 "wifi", "error", reason="Radio still enabled")) as write:
            aero._toggle_wifi(None)
        write.assert_called_once_with("wifi", False)
        self.assertIn("Radio still enabled", aero._network_error)
        aero.refresh_network.assert_called_once_with()

        with patch.object(spice, "change", return_value=spice.Result(
                "bluetooth_disconnect", "error", reason="Device still connected")) as write:
            aero._set_bluetooth_device(None, "AA:BB:CC:DD:EE:FF", False)
        write.assert_called_once_with("bluetooth_disconnect", "AA:BB:CC:DD:EE:FF")
        self.assertIn("Device still connected", aero._bluetooth_error)

    def test_aero_status_and_shutdown_use_bounded_runner(self):
        aero = tray(Win7Tray)
        done = Mock()
        with patch.object(spice, "read", return_value=spice.Result(
                "desktop_status", "ok", value="status")) as read:
            aero.refresh_status(done)
        read.assert_called_once_with("desktop_status")
        done.assert_called_once_with("status")
        aero.close()
        self.assertTrue(aero._requests.closed)

    def test_aero_desktop_shortcuts_use_riceplate_with_existing_safety(self):
        with patch.object(plate.win7_desktop, "manage", return_value=((), ("user edited",))) as manage:
            result = plate.manage_shortcuts("win7", "remove")
        manage.assert_called_once_with("remove", folder=None, catalog=None)
        self.assertEqual(result, ((), ("user edited",)))


if __name__ == "__main__":
    unittest.main()
