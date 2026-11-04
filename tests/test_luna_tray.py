"""XP notification-area backend tests; no desktop or device required."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from macrice.hardware_status import (
    _nmcli_fields, connect_wifi, disconnect_wifi, read_bluetooth, read_brightness,
    read_power_profiles, read_sound_outputs, read_wifi_networks, read_wifi_radio,
    set_bluetooth_power, set_brightness, set_power_profile, set_sound_output,
    set_wifi_radio,
)


class WifiTrayTests(unittest.TestCase):
    def test_nmcli_escape_handling(self):
        self.assertEqual(_nmcli_fields(r"*:Cafe\: Study:74:WPA2"),
                         ("*", "Cafe: Study", "74", "WPA2"))
        self.assertEqual(_nmcli_fields(r" :Office\\Guest:42:WPA3"),
                         (" ", r"Office\Guest", "42", "WPA3"))

    @patch("macrice.hardware_status._run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/nmcli")
    def test_networks_sorted_and_deduplicated(self, _which, run):
        run.return_value = ("*:Main:55:WPA2\n:Guest:90:--\n:Main:70:WPA2\n"
                            ":Hidden::WPA2\n:Bad:bogus:--")
        networks = read_wifi_networks()
        self.assertEqual([n.ssid for n in networks], ["Main", "Guest"])
        self.assertTrue(networks[0].connected)
        self.assertEqual(networks[0].signal, 55)
        self.assertEqual(run.call_args.kwargs, {"timeout": 1.8})

    @patch("macrice.hardware_status._run", return_value="enabled")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/nmcli")
    def test_radio_probes_actual_backend(self, _which, run):
        self.assertTrue(read_wifi_radio())
        run.assert_called_once_with(["nmcli", "radio", "wifi"])

    @patch("macrice.hardware_status.shutil.which", return_value=None)
    def test_missing_network_manager_is_explicit(self, _which):
        self.assertIsNone(read_wifi_radio())
        self.assertEqual(read_wifi_networks(), ())
        with self.assertRaises(RuntimeError):
            set_wifi_radio(False)

    @patch("macrice.hardware_status.read_wifi_radio", return_value=True)
    @patch("macrice.hardware_status.subprocess.run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/nmcli")
    def test_wifi_change_verified(self, _which, run, _read):
        run.return_value.returncode = 0
        self.assertTrue(set_wifi_radio(True))
        self.assertEqual(run.call_args.args[0], ["nmcli", "radio", "wifi", "on"])
        with self.assertRaises(RuntimeError):
            set_wifi_radio(False)

    @patch("macrice.hardware_status.read_wifi_networks")
    @patch("macrice.hardware_status.subprocess.run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/nmcli")
    def test_connect_wifi_passes_ssid_as_data_and_verifies(self, _which, run, networks):
        from macrice.hardware_status import WifiNetwork

        run.return_value.returncode = 0
        networks.return_value = (WifiNetwork("Cafe: Wi-Fi", 79, "WPA2", True),)
        self.assertTrue(connect_wifi("Cafe: Wi-Fi"))
        self.assertEqual(run.call_args.args[0][-1], "Cafe: Wi-Fi")
        with self.assertRaises(ValueError):
            connect_wifi("\x00")

    @patch("macrice.hardware_status.read_wifi_networks", return_value=())
    @patch("macrice.hardware_status.subprocess.run")
    @patch("macrice.hardware_status._run", return_value="wlp1s0:wifi:connected\neth0:ethernet:connected")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/nmcli")
    def test_disconnect_targets_wifi_not_wired(self, _which, _read, run, _networks):
        run.return_value.returncode = 0
        self.assertTrue(disconnect_wifi())
        self.assertEqual(run.call_args.args[0], ["nmcli", "device", "disconnect", "wlp1s0"])


class BrightnessTrayTests(unittest.TestCase):
    def test_backlight_uses_actual_maximum(self):
        with tempfile.TemporaryDirectory() as tmp:
            led = Path(tmp) / "intel_backlight"
            led.mkdir()
            (led / "max_brightness").write_text("12000")
            (led / "brightness").write_text("9000")
            self.assertEqual(read_brightness(Path(tmp)), 75)

    @patch("macrice.hardware_status.shutil.which", return_value=None)
    def test_brightness_write_without_backend(self, _which):
        with self.assertRaises(RuntimeError):
            set_brightness(50)

    @patch("macrice.hardware_status.read_brightness", return_value=61)
    @patch("macrice.hardware_status.subprocess.run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/brightnessctl")
    def test_brightness_read_back(self, _which, run, _read):
        run.return_value.returncode = 0
        self.assertEqual(set_brightness(60), 61)
        self.assertEqual(run.call_args.args[0], ["brightnessctl", "set", "60%"])
        with self.assertRaises(ValueError):
            set_brightness(0)


class ExtraDeviceTests(unittest.TestCase):
    @patch("macrice.hardware_status._run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/pactl")
    def test_audio_outputs_match_real_default(self, _which, run):
        run.side_effect = ["0\talsa_output.analog-stereo\tmodule\n"
                           "1\talsa_output.hdmi-stereo\tmodule", "alsa_output.hdmi-stereo"]
        outputs = read_sound_outputs()
        self.assertEqual(len(outputs), 2)
        self.assertFalse(outputs[0].active)
        self.assertTrue(outputs[1].active)

    @patch("macrice.hardware_status.read_sound_outputs")
    @patch("macrice.hardware_status.subprocess.run")
    def test_sound_selection_is_verified(self, run, outputs):
        from macrice.hardware_status import SoundOutput

        entry = SoundOutput("alsa_output.test", "test", False)
        outputs.side_effect = [(entry,), (SoundOutput(entry.name, "test", True),)]
        run.return_value.returncode = 0
        self.assertTrue(set_sound_output(entry.name).active)
        self.assertEqual(run.call_args.args[0], ["pactl", "set-default-sink", entry.name])

    @patch("macrice.hardware_status._run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/powerprofilesctl")
    def test_power_profile_discovery(self, _which, run):
        run.side_effect = ["balanced", "* performance:\n  balanced:\n  power-saver:\n"]
        self.assertEqual(read_power_profiles(),
                         ("balanced", ("power-saver", "balanced", "performance")))

    @patch("macrice.hardware_status.read_power_profiles")
    @patch("macrice.hardware_status.subprocess.run")
    def test_power_profile_commit_verified(self, run, profiles):
        profiles.side_effect = [("balanced", ("balanced", "power-saver")),
                                ("power-saver", ("balanced", "power-saver"))]
        run.return_value.returncode = 0
        self.assertEqual(set_power_profile("power-saver"), "power-saver")

    @patch("macrice.hardware_status._run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/bluetoothctl")
    def test_bluetooth_power_and_connected_devices(self, _which, run):
        run.side_effect = ["Controller XX\nPowered: yes", "Device 00:11:22:33:44:55 Headphones"]
        state = read_bluetooth()
        self.assertTrue(state.powered)
        self.assertEqual(state.connected, ("Headphones",))

    @patch("macrice.hardware_status.read_bluetooth")
    @patch("macrice.hardware_status.subprocess.run")
    @patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/bluetoothctl")
    def test_bluetooth_write_verified(self, _which, run, read):
        from macrice.hardware_status import BluetoothState

        run.return_value.returncode = 0
        read.return_value = BluetoothState(True, ())
        self.assertTrue(set_bluetooth_power(True).powered)
        with self.assertRaises(RuntimeError):
            set_bluetooth_power(False)


if __name__ == "__main__":
    unittest.main()
