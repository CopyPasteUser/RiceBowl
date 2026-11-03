"""Aero geometry and overflow regressions; independent of GTK hardware."""
import unittest

from macrice.aero_layout import PANEL_HEIGHT, actual_popup_y, bottom_strut, menu_geometry, task_capacity, select_windows


class AeroLayoutTests(unittest.TestCase):
    def test_menu_is_bounded_to_monitor_with_nonzero_origin(self):
        for x, y, w, h in [(0, 0, 1920, 1080), (1920, 0, 1366, 768), (-1280, 50, 1280, 720),
                            (0, 0, 480, 360), (0, 0, 320, 240)]:
            a, b, c, d = menu_geometry(x, y, w, h)
            self.assertGreaterEqual(a, x)
            self.assertGreaterEqual(b, y)
            self.assertLessEqual(a + c, x + w)
            self.assertLessEqual(b + d, y + h - PANEL_HEIGHT)

    def test_xp_menu_is_reanchored_for_gtk_natural_height(self):
        # The 0.9.0 menu grew beyond its requested 560 px and overlapped the panel.
        for top, monitor_height, allocated_height in ((0, 900, 587), (75, 900, 587), (-20, 768, 608)):
            y = actual_popup_y(top, monitor_height, allocated_height)
            self.assertEqual(y + allocated_height, top + monitor_height - PANEL_HEIGHT - 8)

    def test_capacities_do_not_overflow_at_narrow_widths(self):
        self.assertEqual(task_capacity(320, 3), 0)
        self.assertGreater(task_capacity(1920, 3), task_capacity(800, 3))
        self.assertLessEqual(task_capacity(3840, 3), 9)

    def test_active_window_is_kept_visible_and_overflow_is_complete(self):
        windows = tuple(range(12))
        visible, hidden = select_windows(windows, 10, 3)
        self.assertEqual(visible, (0, 1, 10))
        self.assertEqual(len(visible) + len(hidden), 12)
        self.assertEqual(len(set(visible + hidden)), 12)

    def test_ewmh_bottom_workarea_only_when_monitor_touches_root_bottom(self):
        short, partial = bottom_strut(0, 0, 1920, 1080, 1080)
        self.assertEqual(short, (0, 0, 0, PANEL_HEIGHT))
        self.assertEqual(len(partial), 12)
        self.assertEqual(partial[-2:], (0, 1919))
        none, none_partial = bottom_strut(1920, 0, 1280, 720, 1080)
        self.assertEqual(none, (0, 0, 0, 0))
        self.assertEqual(none_partial, (0,) * 12)

    def test_zero_capacity_shows_all_in_overflow(self):
        windows = (1, 2, 3)
        self.assertEqual(select_windows(windows, 2, 0), ((), windows))
