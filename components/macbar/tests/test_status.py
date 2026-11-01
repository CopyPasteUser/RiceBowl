from __future__ import annotations

import tempfile
import unittest
import datetime as dt
from pathlib import Path
from sys import path

path.insert(0, str(Path(__file__).resolve().parents[1]))

from status import Battery, Volume, clock_text, network_status, parse_pactl, parse_wpctl, read_battery  # noqa: E402


class StatusTests(unittest.TestCase):
    def test_wpctl(self) -> None:
        self.assertEqual(parse_wpctl("Volume: 0.35 [MUTED]"), Volume(35, True))
        self.assertEqual(parse_wpctl("Volume: 1.23"), Volume(123, False))
        self.assertIsNone(parse_wpctl("Backend unavailable"))

    def test_pactl(self) -> None:
        self.assertEqual(parse_pactl("front-left: 65536 / 100% / 0.00 dB"), Volume(100, False))

    def test_battery(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "AC").mkdir()
            (root / "AC/type").write_text("Mains\n")
            battery = root / "BAT0"
            battery.mkdir()
            (battery / "type").write_text("Battery\n")
            (battery / "capacity").write_text("87\n")
            (battery / "status").write_text("Charging\n")
            self.assertEqual(read_battery(root), Battery(87, "Charging"))

    def test_missing_battery(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(read_battery(Path(folder)))

    def test_network_connection_type_not_just_global_state(self) -> None:
        self.assertEqual(network_status(70, "802-11-wireless"),
                         ("network-wireless-symbolic", "Wi-Fi connected"))
        self.assertEqual(network_status(70, "802-3-ethernet"),
                         ("network-wired-symbolic", "Ethernet connected"))
        self.assertEqual(network_status(50, "802-11-wireless"),
                         ("network-wireless-symbolic", "Wi-Fi connected (limited)"))
        self.assertEqual(network_status(20, "802-11-wireless"),
                         ("network-offline-symbolic", "Network disconnected"))

    def test_wifi_remains_visible_with_vpn_primary(self) -> None:
        self.assertEqual(network_status(70, "vpn", ("vpn", "802-11-wireless")),
                         ("network-wireless-symbolic", "Wi-Fi connected"))
        self.assertEqual(network_status(70, "vpn", ("802-3-ethernet",)),
                         ("network-wired-symbolic", "Ethernet connected"))

    def test_clock_adapts_to_available_width(self) -> None:
        now = dt.datetime(2026, 11, 1, 17, 42)
        self.assertEqual(clock_text(now, 320), "17:42")
        self.assertEqual(clock_text(now, 600), "Sun  17:42")
        self.assertEqual(clock_text(now, 1440), "Sun 01 Nov  17:42")


if __name__ == "__main__":
    unittest.main()
