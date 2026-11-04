"""XP-specific Riceware migration tests; no GTK session or real devices."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from macrice.luna_tray import LunaTray
from macrice.riceware import spice
from macrice.riceware.worker import Response


class InlineRunner:
    """Execute a real adapter operation but schedule the UI callback inline."""

    def __init__(self):
        self.operations = []
        self.closed = False

    def submit(self, key, operation, callback):
        self.operations.append(key)
        callback(Response(key, len(self.operations), value=operation()))

    def close(self):
        self.closed = True


class FakeButton:
    def __init__(self):
        self.sensitive = None
        self.label = None

    def set_sensitive(self, value):
        self.sensitive = value

    def set_label(self, value):
        self.label = value


class FakeLabel:
    def __init__(self):
        self.text = None

    def set_text(self, value):
        self.text = value


class FakeBox:
    def __init__(self):
        self.children = []

    def get_children(self):
        return self.children.copy()

    def remove(self, child):
        self.children.remove(child)

    def pack_start(self, child, *_args):
        self.children.append(child)

    def show_all(self):
        pass


def tray(tray_type=LunaTray):
    instance = object.__new__(tray_type)
    instance._requests = InlineRunner()
    instance._network_busy = False
    instance._network_error = None
    instance._power_profile_busy = False
    instance._profile_error = None
    instance._bluetooth_busy = False
    instance._bluetooth_error = None
    instance._brightness_writing = False
    instance._brightness_queued = None
    instance._brightness_source = 0
    instance.network_label = FakeLabel()
    instance.wifi_toggle = FakeButton()
    instance.wifi_disconnect = FakeButton()
    instance.network_list = FakeBox()
    instance.profile_label = FakeLabel()
    instance.bluetooth_switch = FakeButton()
    instance.bluetooth_label = FakeLabel()
    instance.brightness_label = FakeLabel()
    instance.audio_label = FakeLabel()
    instance._label = lambda value, *_args: FakeLabel()
    instance.refresh_network = Mock()
    instance.refresh_bluetooth = Mock()
    instance.refresh_profiles = Mock()
    instance.refresh_brightness = Mock()
    instance.refresh_outputs = Mock()
    return instance


class LunaRicewareTests(unittest.TestCase):
    def test_xp_taskbar_status_uses_the_same_worker_and_result_contract(self):
        xp = tray()
        done = Mock()
        with patch.object(spice, "read", return_value=spice.Result(
                "desktop_status", "ok", "live")) as read:
            xp.refresh_status(done)
        read.assert_called_once_with("desktop_status")
        done.assert_called_once_with("live")
        with patch.object(spice, "read", return_value=spice.Result(
                "desktop_status", "error", reason="backend down")):
            xp.refresh_status(done)
        done.assert_called_with(None)

    def test_xp_audio_writes_are_delegated_and_verified(self):
        xp = tray()
        done = Mock()
        with patch.object(spice, "change", return_value=spice.Result(
                "audio_volume", "ok", value="confirmed")) as change:
            xp.change_audio("audio_volume", 42, done)
        change.assert_called_once_with("audio_volume", 42)
        done.assert_called_once_with("confirmed", None)
        with patch.object(spice, "change", return_value=spice.Result(
                "audio_mute", "error", reason="readback mismatch")):
            xp.change_audio("audio_mute", True, done)
        done.assert_called_with(None, "readback mismatch")

    def test_wifi_refresh_uses_real_riceware_rescan(self):
        xp = tray()
        xp.refresh_network = LunaTray.refresh_network.__get__(xp, LunaTray)
        with patch.object(spice, "read", return_value=spice.Result("wifi", "ok", True)) as read, \
             patch.object(spice, "scan_wifi", return_value=spice.Result(
                 "wifi_networks", "ok", ())) as scan:
            xp.refresh_network(rescan=True)
        read.assert_called_once_with("wifi")
        scan.assert_called_once_with(rescan=True)
        self.assertEqual(xp.network_label.text, "Wi-Fi is on")
        self.assertFalse(xp._network_busy)

    def test_wifi_backend_exception_does_not_leave_busy_spinner(self):
        xp = tray()
        xp.refresh_network = LunaTray.refresh_network.__get__(xp, LunaTray)

        class ErrorRunner:
            def submit(self, key, _operation, callback):
                callback(Response(key, 1, error="session bus disconnected"))

        xp._requests = ErrorRunner()
        xp.refresh_network()
        self.assertFalse(xp._network_busy)
        self.assertEqual(xp.network_label.text, "session bus disconnected")
        self.assertFalse(xp.wifi_toggle.sensitive)

    def test_wifi_toggle_never_reports_success_on_readback_mismatch(self):
        xp = tray()
        with patch.object(spice, "read", return_value=spice.Result("wifi", "ok", True)), \
             patch.object(spice, "change", return_value=spice.Result(
                 "wifi", "error", reason="radio still on")) as change:
            xp._toggle_wifi(None)
        change.assert_called_once_with("wifi", False)
        self.assertIn("radio still on", xp._network_error)
        xp.refresh_network.assert_called_once_with()
        self.assertFalse(xp._network_busy)

    def test_wifi_missing_backend_does_not_write(self):
        xp = tray()
        with patch.object(spice, "read", return_value=spice.Result(
                "wifi", "unavailable", reason="No NetworkManager")), \
             patch.object(spice, "change") as change:
            xp._toggle_wifi(None)
        change.assert_not_called()
        self.assertIn("No NetworkManager", xp._network_error)

    def test_wifi_join_and_disconnect_use_single_api(self):
        xp = tray()
        with patch.object(spice, "change", return_value=spice.Result(
                "wifi_connect", "error", reason="Credentials required")) as change:
            xp._join_wifi("My Home")
        change.assert_called_once_with("wifi_connect", "My Home")
        self.assertIn("Credentials required", xp._network_error)
        self.assertIn("Connections", xp._network_error)
        with patch.object(spice, "change", return_value=spice.Result(
                "wifi_disconnect", "ok", ())) as change:
            xp._disconnect_wifi(None)
        change.assert_called_once_with("wifi_disconnect")
        self.assertIsNone(xp._network_error)

    def test_bluetooth_backend_selection_and_verified_write(self):
        xp = tray()
        state = Mock(powered=False)
        with patch.object(spice, "read", return_value=spice.Result(
                "bluetooth", "ok", state)), \
             patch.object(spice, "change", return_value=spice.Result(
                 "bluetooth_power", "ok", state)) as change:
            xp._toggle_bluetooth(None)
        change.assert_called_once_with("bluetooth_power", True)
        self.assertIsNone(xp._bluetooth_error)
        xp.refresh_bluetooth.assert_called_once_with()

        with patch.object(spice, "change", return_value=spice.Result(
                "bluetooth_connect", "error", reason="Not paired")) as change:
            xp._set_bluetooth_device(None, "AA:BB:CC:DD:EE:FF", True)
        change.assert_called_once_with("bluetooth_connect", "AA:BB:CC:DD:EE:FF")
        self.assertIn("Not paired", xp._bluetooth_error)

    def test_power_profile_and_brightness_use_verified_readback(self):
        xp = tray()
        with patch.object(spice, "change", return_value=spice.Result(
                "power_profile", "error", reason="Denied")) as change:
            xp._switch_profile("balanced")
        change.assert_called_once_with("power_profile", "balanced")
        self.assertIn("Denied", xp._profile_error)
        xp.refresh_profiles.assert_called_once_with()

        xp._brightness_queued = 64
        with patch.object(spice, "change", return_value=spice.Result(
                "brightness", "ok", 62)) as change:
            self.assertFalse(xp._commit_brightness())
        change.assert_called_once_with("brightness", 64)
        self.assertEqual(xp.brightness_label.text, "Brightness: 62%")
        self.assertFalse(xp._brightness_writing)
        xp.refresh_brightness.assert_called_once_with()

    def test_shutdown_closes_worker_and_discards_pending_brightness_timeout(self):
        xp = tray()
        xp._brightness_source = 91
        xp.GLib = Mock()
        xp.close()
        xp.GLib.source_remove.assert_called_once_with(91)
        self.assertTrue(xp._requests.closed)


if __name__ == "__main__":
    unittest.main()
