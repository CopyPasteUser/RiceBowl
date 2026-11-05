"""Aqua display inventory reads real RandR data without changing screens."""

import subprocess
import unittest
from unittest import mock

from macrice import display_layout


XRANDR = """Screen 0: minimum 8 x 8, current 3840 x 1080, maximum 32767 x 32767
eDP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis)
   1920x1080     60.01*+  59.93
   1680x1050     59.88
   1366x768      60.00
HDMI-1 connected 1920x1080+1920+0 (normal left inverted right x axis y axis)
   1920x1080     60.00*+  50.00
   1280x720      60.00
DP-1 disconnected (normal left inverted right x axis y axis)
"""


class DisplayLayoutTests(unittest.TestCase):
    def test_read_all_connected_outputs_without_disconnected_noise(self):
        outputs = display_layout.parse_randr(XRANDR)
        self.assertEqual([item.name for item in outputs], ["eDP-1", "HDMI-1"])
        self.assertTrue(outputs[0].primary)
        self.assertEqual(outputs[1].position, (1920, 0))
        self.assertEqual(outputs[1].current_mode, "1920x1080")
        self.assertEqual(outputs[0].modes, ("1920x1080", "1680x1050", "1366x768"))

    def test_handles_unusual_offsets_and_missing_active_geometry(self):
        outputs = display_layout.parse_randr(
            "DP-2 connected 1440x900+-1440+0 (normal left inverted right)\n"
            "   1440x900 60.00*\n"
            "USB-1 connected (normal left inverted right)\n"
            "   800x600 60.00+\n")
        self.assertEqual(outputs[0].position, (-1440, 0))
        self.assertIsNone(outputs[1].current_mode)
        self.assertEqual(outputs[1].modes, ("800x600",))

    def test_missing_x11_is_explicit_and_never_invokes_xrandr(self):
        with mock.patch.dict(display_layout.os.environ, {"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"}), \
                mock.patch.object(display_layout.subprocess, "run") as run:
            with self.assertRaisesRegex(RuntimeError, "Wayland"):
                display_layout.read_monitor_layout()
        run.assert_not_called()

    def test_read_uses_only_query_and_reports_failure_without_side_effects(self):
        with mock.patch.dict(display_layout.os.environ, {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}), \
                mock.patch.object(display_layout.shutil, "which", return_value="/usr/bin/xrandr"), \
                mock.patch.object(display_layout.subprocess, "run", return_value=
                                  subprocess.CompletedProcess([], 0, stdout=XRANDR)) as run:
            self.assertEqual(len(display_layout.read_monitor_layout()), 2)
        run.assert_called_once_with(("xrandr", "--query"), capture_output=True,
                                    text=True, timeout=4, check=False)
        with mock.patch.dict(display_layout.os.environ, {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}), \
                mock.patch.object(display_layout.shutil, "which", return_value="/usr/bin/xrandr"), \
                mock.patch.object(display_layout.subprocess, "run", return_value=
                                  subprocess.CompletedProcess([], 1, stdout="")):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                display_layout.read_monitor_layout()


if __name__ == "__main__":
    unittest.main()
