"""Frutiger tray controls: real providers, bounded presentation and stale safety."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from macrice.frutiger_flyouts import AquaFlyouts
from macrice.hardware_status import BluetoothDevice, BluetoothState, SoundOutput, WifiNetwork
from macrice.riceware.worker import Response


class FakeRunner:
    def __init__(self):
        self.requests = []

    def submit(self, key, action, callback):
        self.requests.append((key, action, callback))

    def complete(self, *, error=None):
        key, action, callback = self.requests.pop(0)
        callback(Response(key, 1, error=error,
                          value=None if error else action()))


def flyout(backend=None):
    instance = AquaFlyouts.__new__(AquaFlyouts)
    instance.Gtk = SimpleNamespace(Label=lambda **_kwargs: Mock())
    instance.controller = SimpleNamespace(hardware=backend or Mock())
    instance._busy = set()
    instance._confirming = set()
    instance._generations = {}
    instance.popovers = {"network": SimpleNamespace(get_visible=lambda: True)}
    instance.details = {"network": Mock()}
    instance.details["network"].get_children.return_value = ()
    instance.detail_status = {"network": Mock()}
    return instance


class AquaFlyoutTests(unittest.TestCase):
    def test_all_device_probes_use_injected_shared_facade(self):
        backend = Mock()
        backend.read_wifi_radio.return_value = True
        backend.read_wifi_networks.return_value = (WifiNetwork("Office", 72, "WPA2", True),)
        backend.read_bluetooth.return_value = BluetoothState(False, ())
        backend.read_sound_outputs.return_value = (SoundOutput("sink", "Speakers", True),)
        backend.read_power_profiles.return_value = ("balanced", ("balanced", "power-saver"))
        panel = flyout(backend)
        self.assertEqual(panel._read_details("network")[0], True)
        self.assertEqual(panel._read_details("bluetooth").powered, False)
        self.assertEqual(panel._read_details("audio")[0].name, "sink")
        self.assertEqual(panel._read_details("battery")[0], "balanced")
        for name in ("read_wifi_radio", "read_wifi_networks", "read_bluetooth",
                     "read_sound_outputs", "read_power_profiles"):
            getattr(backend, name).assert_called_once_with()

    def test_wifi_list_is_bounded_and_selects_exact_ssid(self):
        backend = Mock()
        panel = flyout(backend)
        panel._clear = Mock()
        panel._row = Mock()
        panel._change = Mock()
        networks = tuple(WifiNetwork("wifi-" + str(i), 60, "WPA2", i == 0)
                         for i in range(12))
        panel._render_details("network", (True, networks))
        self.assertEqual(panel._row.call_count, 6)  # Radio plus five networks.
        actions = [call.kwargs["action"] for call in panel._row.call_args_list[1:]]
        actions[1]()
        action = panel._change.call_args.args[1]
        action()
        backend.connect_wifi.assert_called_once_with("wifi-1")

    def test_bluetooth_links_are_available_only_for_paired_devices(self):
        backend = Mock()
        panel = flyout(backend)
        panel.details["bluetooth"] = Mock()
        panel._clear = Mock()
        panel._row = Mock()
        devices = (BluetoothDevice("AA:BB:CC:DD:EE:FF", "Headset", True, False),
                   BluetoothDevice("11:22:33:44:55:66", "Nearby", False, False))
        panel._render_details("bluetooth", BluetoothState(True, (), devices, "dbus"))
        self.assertEqual(panel._row.call_count, 3)
        self.assertEqual(panel._row.call_args_list[1].kwargs["button"], "Connect")
        self.assertNotIn("button", panel._row.call_args_list[2].kwargs)

    def test_radio_shutdown_needs_confirm_and_can_be_cancelled(self):
        panel = flyout()
        panel._row = Mock()
        panel._refresh_details = Mock()
        panel._change = Mock()
        action = Mock()
        panel._confirm_radio_off("network", action)
        self.assertEqual(panel._row.call_count, 2)
        self.assertEqual(panel._change.call_count, 0)
        panel._confirm_radio_off("network", action)
        self.assertEqual(panel._row.call_count, 2)
        panel._row.call_args_list[1].kwargs["action"]()
        panel._refresh_details.assert_called_once_with("network")
        panel._row.call_args_list[0].kwargs["action"]()
        panel._change.assert_called_once_with("network", action)

    def test_late_mutation_result_cannot_reopen_closed_popover(self):
        runner = FakeRunner()
        panel = flyout()
        panel.controller.submit = runner.submit
        panel._refresh_details = Mock()
        panel._change("network", lambda: True)
        self.assertEqual(runner.requests[0][0], "aqua-write-network")
        panel._discard("network")
        runner.complete()
        panel._refresh_details.assert_not_called()
        self.assertNotIn("network", panel._busy)

    def test_read_failure_is_explicit_and_does_not_enable_stale_controls(self):
        runner = FakeRunner()
        panel = flyout()
        panel.controller.submit = runner.submit
        panel._clear = Mock()
        panel._render_details = Mock()
        panel._refresh_details("network")
        self.assertEqual(runner.requests[0][0], "aqua-read-network")
        runner.complete(error="NetworkManager not available")
        panel._render_details.assert_not_called()
        self.assertIn("NetworkManager not available",
                      panel.detail_status["network"].set_text.call_args.args[0])
        self.assertNotIn("network", panel._busy)

    def test_hiding_popover_drops_late_wifi_scan_and_private_rows(self):
        runner = FakeRunner()
        panel = flyout()
        panel.controller.submit = runner.submit
        panel._read_details = Mock(return_value=(True, (WifiNetwork("Home", 88, "WPA2", True),)))
        panel._render_details = Mock()
        panel._refresh_details("network")
        panel._discard("network")
        runner.complete()
        panel._render_details.assert_not_called()
        panel.details["network"].get_children.assert_called()
        self.assertNotIn("network", panel._busy)


if __name__ == "__main__":
    unittest.main()
