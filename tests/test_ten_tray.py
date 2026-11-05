"""Windows 10 flyout boundaries and reused Linux backend contracts."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from macrice.luna_tray import LunaTray
from macrice.ten_tray import TEN_SETTINGS_LINKS, TEN_TRAY_ICONS, TenTray


class Windows10TrayTests(unittest.TestCase):
    def test_four_native_tray_panels_have_linux_icons(self):
        self.assertEqual(set(TEN_TRAY_ICONS),
                         {"Volume", "Power", "Bluetooth devices", "Date and time"})
        self.assertTrue(all(name for name in TEN_TRAY_ICONS.values()))
        self.assertTrue(issubclass(TenTray, LunaTray))

    def test_deep_links_route_to_real_ten_settings_pages(self):
        self.assertEqual(TEN_SETTINGS_LINKS,
                         {"Sound settings…": "sound", "Power options…": "system",
                          "Date and time settings…": "time"})

    def test_network_is_not_registered_twice(self):
        tray = TenTray.__new__(TenTray)
        with self.assertRaisesRegex(ValueError, "separate NetworkManager"):
            tray.install("network", object())

    def test_toggle_ignores_unknown_tray_without_touching_hardware(self):
        tray = TenTray.__new__(TenTray)
        tray.popovers = {"audio": Mock()}
        tray.shell = Mock()
        tray.toggle("network")
        tray.shell.assert_not_called()


if __name__ == "__main__":
    unittest.main()
