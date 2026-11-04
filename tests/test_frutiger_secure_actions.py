"""Credential and pairing actions must be verified and never expose secrets."""

import subprocess
import unittest
from unittest import mock

from macrice import hardware_status as hw
from macrice.riceware import spice


class SecureDeviceTests(unittest.TestCase):
    def test_wifi_secret_goes_only_to_stdin(self):
        password = "correct-horse-do-not-log"
        network = hw.WifiNetwork("MyNetwork", 88, "WPA2", True)
        with mock.patch.object(hw.shutil, "which", return_value="/usr/bin/nmcli"), \
                mock.patch.object(hw.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run, \
                mock.patch.object(hw, "read_wifi_networks", return_value=(network,)):
            self.assertTrue(hw.connect_wifi_secured("MyNetwork", password))
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["nmcli", "--ask"])
        self.assertNotIn(password, " ".join(command))
        self.assertEqual(run.call_args.kwargs["input"], password + "\n")
        self.assertTrue(run.call_args.kwargs["capture_output"])

    def test_wifi_error_does_not_return_secret_or_subprocess_output(self):
        password = "another-very-secret-value"
        failed = subprocess.CompletedProcess([], 10, stdout=password, stderr="bad " + password)
        with mock.patch.object(hw.shutil, "which", return_value="/usr/bin/nmcli"), \
                mock.patch.object(hw.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(RuntimeError, "authentication failed") as context:
                hw.connect_wifi_secured("Home", password)
        self.assertNotIn(password, str(context.exception))

    def test_wifi_credentials_are_validated_in_riceware_before_device_action(self):
        for invalid in (("MyNetwork", "short"), ("MyNetwork", "bad\npassw"),
                        ("network", "secretpassword", "extra"), ("network", None)):
            result = spice.change("wifi_connect_secure", invalid)
            self.assertEqual(result.status, "error")
            self.assertNotIn("secretpassword", result.reason or "")

    def test_bluetooth_pairing_requires_known_device_and_verifies_pair_state(self):
        address = "AA:BB:CC:DD:EE:FF"
        before = hw.BluetoothState(True, (), (hw.BluetoothDevice(address, "Headset", False, False),))
        after = hw.BluetoothState(True, (), (hw.BluetoothDevice(address, "Headset", True, False),))
        with mock.patch.object(hw, "read_bluetooth", side_effect=[before, after]), \
                mock.patch.object(hw.shutil, "which", return_value="/usr/bin/bluetoothctl"), \
                mock.patch.object(hw.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(hw.pair_bluetooth_device(address), after)
        self.assertEqual(run.call_args.args[0], ["bluetoothctl", "pair", address])

    def test_bluetooth_pairing_rejects_unknown_device_before_mutation(self):
        with mock.patch.object(hw, "read_bluetooth", return_value=hw.BluetoothState(True, (), ())):
            with self.assertRaisesRegex(ValueError, "Discover"):
                hw.pair_bluetooth_device("AA:BB:CC:DD:EE:FF")
