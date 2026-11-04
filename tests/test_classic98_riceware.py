"""Hermetic Windows 98 adapter, safety and desktop-view regression checks."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from macrice.classic98_desktop import MAX_DESKTOP_ITEMS, display_items
from macrice.classic98_riceware import Classic98Controller
from macrice.classic98_tray import MAX_DEVICES, MAX_NETWORKS, network_caption
from macrice.classic98_control_panel import APPLETS
from macrice.hardware_status import WifiNetwork
from macrice.riceware import plate, spice
from macrice.riceware.worker import Response


class FakeRunner:
    def __init__(self):
        self.requests = []
        self.closed = False

    def submit(self, key, operation, callback):
        self.requests.append((key, operation, callback))

    def deliver(self, *, error=None):
        key, operation, callback = self.requests.pop(0)
        callback(Response(key, 1, error=error, value=operation() if not error else None))

    def close(self):
        self.closed = True


class ClassicRicewareTests(unittest.TestCase):
    def setUp(self):
        self.runner = FakeRunner()
        self.adapter = Classic98Controller(object(), runner=self.runner)

    def tearDown(self):
        self.adapter.close()

    def test_status_probe_uses_ricespice_and_one_bounded_request(self):
        reported = []
        status = object()
        with patch("macrice.classic98_riceware.spice.read",
                   return_value=spice.Result("desktop_status", "ok", status)) as read:
            self.adapter.refresh_status(reported.append)
            self.assertEqual(self.runner.requests[0][0], "classic98-desktop-status")
            self.runner.deliver()
            read.assert_called_once_with("desktop_status")
        self.assertEqual(reported, [status])

    def test_unavailable_status_is_not_fabricated(self):
        reported = []
        with patch("macrice.classic98_riceware.spice.read",
                   return_value=spice.Result("desktop_status", "unavailable")):
            self.adapter.refresh_status(reported.append)
            self.runner.deliver()
        self.assertEqual(reported, [None])

    def test_mutation_requires_verified_readback(self):
        reported = []
        expected = object()
        with patch("macrice.classic98_riceware.spice.change",
                   return_value=spice.Result("audio_volume", "ok", expected)) as write:
            self.adapter.change_audio("audio_volume", 42,
                                      lambda value, error: reported.append((value, error)))
            self.runner.deliver()
            write.assert_called_once_with("audio_volume", 42)
        self.assertEqual(reported, [(expected, None)])

    def test_mutation_error_surfaces_without_fake_success(self):
        reported = []
        with patch("macrice.classic98_riceware.spice.change",
                   return_value=spice.Result("audio_mute", "error", reason="Not verified")):
            self.adapter.change_audio("audio_mute", True,
                                      lambda value, error: reported.append((value, error)))
            self.runner.deliver()
        self.assertEqual(reported, [(None, "Not verified")])

    def test_worker_error_and_close_suppress_late_ui_callbacks(self):
        values = []
        self.adapter.submit("network-scan", lambda: 5, values.append)
        self.runner.deliver(error="NetworkManager failed")
        self.assertEqual((values[0].status, values[0].reason),
                         ("error", "NetworkManager failed"))
        self.adapter.submit("network-scan", lambda: 6, values.append)
        self.adapter.close()
        self.runner.deliver()
        self.assertEqual(len(values), 1)
        self.assertTrue(self.runner.closed)
        self.adapter.submit("nothing", lambda: 7, values.append)
        self.assertFalse(self.runner.requests)

    def test_classic_tray_network_details_do_not_infer_a_connection(self):
        item = WifiNetwork("SSID", 66, "WPA2", False)
        self.assertEqual(network_caption(item), "66% · Secured")
        self.assertIn("Connected", network_caption(WifiNetwork("SSID", 80, "--", True)))
        self.assertLessEqual(MAX_NETWORKS, 12)
        self.assertLessEqual(MAX_DEVICES, 12)

    def test_classic_control_panel_has_native_device_applets(self):
        applets = {applet.name for applet in APPLETS}
        self.assertTrue({"Network", "Bluetooth", "Sounds", "Multimedia",
                         "Power Management", "Desktop Icons"} <= applets)

    def test_desktop_rows_are_bounded_and_represent_metadata_honestly(self):
        items = tuple(plate.DesktopItem(f"file-{n}", f"/tmp/file-{n}", "file")
                      for n in range(MAX_DESKTOP_ITEMS + 10))
        snapshot = plate.DesktopSnapshot("/tmp", True, items, True)
        self.assertEqual(len(display_items(snapshot)), MAX_DESKTOP_ITEMS)
        hidden = plate.DesktopSnapshot("/tmp", True, (
            plate.DesktopItem(".secret", "/tmp/.secret", "file"),
            plate.DesktopItem("app.desktop", "/tmp/app.desktop", "launcher",
                              "App", None, True),
        ))
        self.assertEqual(display_items(hidden), (
            (".secret", "file", "Dotfile", "/tmp/.secret"),
            ("App", "launcher", "Hidden entry", "/tmp/app.desktop")))


if __name__ == "__main__":
    unittest.main()
