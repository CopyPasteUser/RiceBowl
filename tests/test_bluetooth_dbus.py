"""Tests for BlueZ D-Bus parsing without a daemon or Bluetooth adapter."""

import unittest
from unittest.mock import patch

from macrice import bluetooth_dbus


class BluetoothDbusTests(unittest.TestCase):
    @patch("macrice.bluetooth_dbus._connection")
    def test_object_manager_uses_real_glib_variant_type(self, connection):
        from gi.repository import Gio

        bus = connection.return_value[1]
        connection.return_value = (Gio, bus)
        bus.call_sync.return_value.unpack.return_value = ({},)
        self.assertEqual(bluetooth_dbus._objects(), {})
        self.assertEqual(bus.call_sync.call_args.args[3], "GetManagedObjects")

    @patch("macrice.bluetooth_dbus._objects")
    def test_dbus_objects_are_scoped_to_selected_adapter(self, objects):
        objects.return_value = {
            "/org/bluez/hci0": {"org.bluez.Adapter1": {"Powered": True}},
            "/org/bluez/hci1": {"org.bluez.Adapter1": {"Powered": False}},
            "/org/bluez/hci0/dev_AA": {"org.bluez.Device1": {
                "Address": "AA:BB:CC:DD:EE:FF", "Alias": "Keyboard", "Paired": True,
                "Connected": False}},
            "/org/bluez/hci1/dev_FF": {"org.bluez.Device1": {
                "Address": "FF:EE:DD:CC:BB:AA", "Alias": "Other", "Paired": True,
                "Connected": True}},
        }
        self.assertEqual(bluetooth_dbus.snapshot(), (
            True, "/org/bluez/hci0", (("AA:BB:CC:DD:EE:FF", "Keyboard", True, False),)))

    @patch("macrice.bluetooth_dbus._objects", return_value={})
    def test_no_adapter_is_not_powered_off(self, _objects):
        with self.assertRaisesRegex(RuntimeError, "No BlueZ adapter"):
            bluetooth_dbus.snapshot()

    @patch("macrice.bluetooth_dbus._connection")
    @patch("macrice.bluetooth_dbus._objects")
    def test_device_method_targets_only_live_paired_path(self, objects, connection):
        from gi.repository import Gio

        bus = connection.return_value[1]
        connection.return_value = (Gio, bus)
        objects.return_value = {
            "/org/bluez/hci0/dev_AA": {"org.bluez.Device1": {
                "Address": "AA:BB:CC:DD:EE:FF", "Paired": True}},
        }
        bluetooth_dbus.set_connection("AA:BB:CC:DD:EE:FF", True)
        self.assertEqual(bus.call_sync.call_args.args[1:4],
                         ("/org/bluez/hci0/dev_AA", "org.bluez.Device1", "Connect"))
        objects.return_value["/org/bluez/hci0/dev_AA"]["org.bluez.Device1"]["Paired"] = False
        with self.assertRaisesRegex(ValueError, "Pair"):
            bluetooth_dbus.set_connection("AA:BB:CC:DD:EE:FF", True)


if __name__ == "__main__":
    unittest.main()
