"""Wnck's optional event-driven task list, tested without an X server."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

from macrice.aero_windows import (WindowSnapshot, WindowSnapController, WindowTracker,
                                 closest_workarea, half_screen_geometry, is_task_window,
                                 toggle_window, toggle_window_id, window_layout)


class FakeWindow:
    next_handler = 0
    next_xid = 100

    def __init__(self, title, kind="normal", skipped=False):
        self.title, self.kind, self.skipped = title, kind, skipped
        self.signals = {}
        self.disconnected = []
        self.minimized = False
        self.maximized = False
        self.fullscreen = False
        self.attention = False
        self.geometry = (150, 160, 640, 460)
        self.calls = []
        self.disposed = False
        self.large_icon = object()  # GdkPixbuf stand-in, never a WnckWindow
        FakeWindow.next_xid += 1
        self.xid = FakeWindow.next_xid

    def get_xid(self):
        return self.xid

    def get_mini_icon(self):
        return None

    def get_icon(self):
        return self.large_icon

    def get_class_group(self):
        return SimpleNamespace(get_id=lambda: getattr(self, "wmclass", ""))

    def get_window_type(self):
        return self.kind

    def is_skip_tasklist(self):
        return self.skipped

    def get_name(self):
        return self.title

    def is_minimized(self):
        return self.minimized

    def is_maximized(self):
        return self.maximized

    def is_fullscreen(self):
        return self.fullscreen

    def needs_attention(self):
        return self.attention

    def get_geometry(self):
        return self.geometry

    def set_geometry(self, gravity, mask, x, y, width, height):
        self.geometry = x, y, width, height
        self.calls.append(("set_geometry", gravity, mask, self.geometry))

    def maximize(self):
        self.maximized = True
        self.calls.append(("maximize",))

    def unmaximize(self):
        self.maximized = False
        self.calls.append(("unmaximize",))

    def minimize(self):
        self.calls.append(("minimize",))

    def unminimize(self, time):
        self.calls.append(("unminimize", time))

    def activate(self, time):
        self.calls.append(("activate", time))

    def connect(self, name, callback):
        FakeWindow.next_handler += 1
        handle = FakeWindow.next_handler
        self.signals[name] = (handle, callback)
        return handle

    def disconnect(self, handle):
        if self.disposed:
            raise RuntimeError("Signal disconnected after native window was disposed")
        self.disconnected.append(handle)

    def emit(self, name):
        self.signals[name][1](self)


class FakeScreen:
    def __init__(self, windows):
        self.windows = windows
        self.active = windows[0] if windows else None
        self.signals = {}

    def get_windows(self):
        return self.windows

    def get_active_window(self):
        return self.active

    def connect(self, name, callback):
        self.signals[name] = callback

    def force_update(self):
        pass

    def emit(self, name, *args):
        self.signals[name](self, *args)


class AeroWindowTests(unittest.TestCase):
    @staticmethod
    def _snapper(window):
        mask = SimpleNamespace(X=1, Y=2, WIDTH=4, HEIGHT=8)
        wnck = SimpleNamespace(Window=SimpleNamespace(
            get=lambda xid: window if xid == window.xid and not window.disposed else None),
            WindowType=SimpleNamespace(NORMAL="normal"),
            WindowMoveResizeMask=mask,
            WindowGravity=SimpleNamespace(NORTHWEST="northwest"))
        return WindowSnapController(wnck)

    def test_snap_splits_odd_workarea_without_gaps(self):
        left = half_screen_geometry((-1920, 30, 1919, 1010), "left")
        right = half_screen_geometry((-1920, 30, 1919, 1010), "right")
        self.assertEqual(left, (-1920, 30, 959, 1010))
        self.assertEqual(right, (-961, 30, 960, 1010))
        self.assertEqual(right[0] + right[2], -1)
        with self.assertRaises(ValueError):
            half_screen_geometry((0, 0, 1, 90), "left")

    def test_desktop_layouts_use_available_monitor_area(self):
        area = (-1920, 40, 1919, 1001)
        side = window_layout(area, 3, "side-by-side")
        self.assertEqual(len(side), 3)
        self.assertEqual(side[0][0], -1920)
        self.assertEqual(side[-1][0] + side[-1][2], -1)
        self.assertTrue(all(r[1] == 40 and r[3] == 1001 for r in side))
        stacked = window_layout(area, 3, "stacked")
        self.assertEqual(len(stacked), 3)
        self.assertEqual(stacked[-1][1] + stacked[-1][3], 1041)
        cascaded = window_layout(area, 3, "cascade")
        self.assertEqual(len(cascaded), 3)
        self.assertLess(cascaded[0][0], cascaded[-1][0])
        self.assertLess(cascaded[0][1], cascaded[-1][1])
        self.assertTrue(all(x >= -1920 and y >= 40 for x, y, _, _ in cascaded))

    def test_desktop_layout_refuses_unusable_screens_or_overcrowding(self):
        area = (0, 0, 800, 600)
        for layout in ("cascade", "stacked", "side-by-side"):
            self.assertEqual(window_layout(area, 0, layout), ())
            self.assertEqual(window_layout(area, 13, layout), ())
        self.assertEqual(window_layout((0, 0, 320, 240), 12, "stacked"), ())
        with self.assertRaises(ValueError):
            window_layout(area, 2, "random")

    def test_desktop_layout_can_arrange_and_undo_using_original_geometry(self):
        window = FakeWindow("Editor")
        controller = self._snapper(window)
        position = window_layout((0, 0, 1000, 700), 2, "side-by-side")[0]
        self.assertTrue(controller.place(window.xid, position, 20))
        self.assertEqual(window.geometry, (0, 0, 500, 700))
        self.assertTrue(controller.arrange(window.xid, "restore", (0, 0, 1000, 700), 21))
        self.assertEqual(window.geometry, (150, 160, 640, 460))
        self.assertFalse(controller.place(window.xid, (0, 0, 0, 400), 22))

    def test_snap_selects_correct_workarea_on_negative_monitor(self):
        areas = ((0, 0, 1920, 1040), (-1920, 30, 1920, 1050))
        self.assertEqual(closest_workarea((-1600, 90, 420, 400), areas), areas[1])
        self.assertEqual(closest_workarea((500, 90, 420, 400), areas), areas[0])
        with self.assertRaises(ValueError):
            closest_workarea((0, 0, 20, 20), ())

    def test_snap_native_tile_and_restore_are_reversible(self):
        window = FakeWindow("Editor")
        controller = self._snapper(window)
        area = (0, 0, 1920, 1040)
        self.assertTrue(controller.arrange(window.xid, "left", area, 123))
        self.assertEqual(window.geometry, (0, 0, 960, 1040))
        self.assertEqual(controller.original[window.xid], ((150, 160, 640, 460), False))
        self.assertTrue(controller.arrange(window.xid, "right", area, 124))
        self.assertEqual(window.geometry, (960, 0, 960, 1040))
        self.assertTrue(controller.arrange(window.xid, "restore", area, 125))
        self.assertEqual(window.geometry, (150, 160, 640, 460))
        self.assertEqual(controller.original, {})
        self.assertFalse(controller.arrange(window.xid, "restore", area, 126))

    def test_snap_restores_previous_maximized_state(self):
        window = FakeWindow("Editor")
        window.maximized = True
        controller = self._snapper(window)
        self.assertTrue(controller.arrange(window.xid, "left", (0, 0, 1000, 700), 1))
        self.assertIn(("unmaximize",), window.calls)
        self.assertTrue(controller.arrange(window.xid, "restore", (0, 0, 1000, 700), 2))
        self.assertTrue(window.maximized)
        self.assertIn(("maximize",), window.calls)

    def test_snap_refuses_fullscreen_dialogs_and_closed_windows(self):
        window = FakeWindow("Video")
        controller = self._snapper(window)
        window.fullscreen = True
        self.assertFalse(controller.arrange(window.xid, "left", (0, 0, 1000, 700), 1))
        window.fullscreen = False
        window.kind = "dialog"
        self.assertFalse(controller.arrange(window.xid, "left", (0, 0, 1000, 700), 1))
        window.kind = "normal"
        self.assertFalse(controller.arrange(window.xid, "left", (0, 0, 1, 700), 1))
        window.disposed = True
        self.assertFalse(controller.arrange(window.xid, "left", (0, 0, 1000, 700), 1))
        self.assertFalse(controller.arrange(window.xid, "suspend", (0, 0, 1000, 700), 1))

    def test_snap_forgets_closed_window_states(self):
        window = FakeWindow("Editor")
        controller = self._snapper(window)
        self.assertTrue(controller.arrange(window.xid, "maximize", (0, 0, 1000, 700), 1))
        self.assertIn(window.xid, controller.original)
        controller.forget_closed(())
        self.assertEqual(controller.original, {})

    def test_only_normal_visible_titled_windows_appear(self):
        wnck = SimpleNamespace(WindowType=SimpleNamespace(NORMAL="normal"))
        self.assertTrue(is_task_window(FakeWindow("Files"), wnck))
        for window in (FakeWindow("Dock", "dock"), FakeWindow("Hidden", skipped=True),
                       FakeWindow("")):
            self.assertFalse(is_task_window(window, wnck))

    def test_task_button_minimizes_active_window(self):
        window = FakeWindow("Files")
        toggle_window(window, window, 123)
        self.assertEqual(window.calls, [("minimize",)])

    def test_task_button_restores_and_activates_minimized_window(self):
        window = FakeWindow("Files")
        window.minimized = True
        toggle_window(window, window, 321)
        self.assertEqual(window.calls, [("unminimize", 321), ("activate", 321)])

    def test_closed_task_button_is_inert_without_retaining_a_native_window(self):
        screen = FakeScreen([])
        wnck = SimpleNamespace(Window=SimpleNamespace(get=lambda _xid: None))
        self.assertFalse(toggle_window_id(wnck, screen, 123, 777))

    def test_live_task_button_resolves_window_only_on_click(self):
        first = FakeWindow("Files")
        screen = FakeScreen([first])
        wnck = SimpleNamespace(Window=SimpleNamespace(get=lambda xid: first if xid == first.xid else None))
        self.assertTrue(toggle_window_id(wnck, screen, first.xid, 555))
        self.assertEqual(first.calls, [("minimize",)])

    def test_window_signals_are_coalesced_without_polling(self):
        first, second = FakeWindow("Files"), FakeWindow("Start", "utility")
        first.wmclass = "Thunar"
        first.attention = True
        screen = FakeScreen([first, second])
        wnck = SimpleNamespace(Screen=SimpleNamespace(get_default=lambda: screen),
                               WindowType=SimpleNamespace(NORMAL="normal"))
        jobs, notifications = [], []
        tracker = WindowTracker(wnck, jobs.append, lambda windows, active: notifications.append((windows, active)))
        self.assertTrue(tracker.start())
        self.assertEqual(len(notifications), 1)
        windows, active = notifications[0]
        self.assertEqual(len(windows), 1)
        self.assertIsInstance(windows[0], WindowSnapshot)
        self.assertEqual((windows[0].xid, windows[0].title, windows[0].minimized),
                         (first.xid, "Files", False))
        self.assertEqual(windows[0].group_id, "Thunar")
        self.assertIs(windows[0].large_icon, first.large_icon)
        self.assertTrue(windows[0].needs_attention)
        self.assertEqual(active, windows[0])
        self.assertEqual(set(tracker._window_handlers), {first.xid, second.xid})
        first.emit("name-changed")
        first.emit("icon-changed")
        screen.emit("active-window-changed")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(len(notifications), 1)
        self.assertFalse(jobs.pop()())
        self.assertEqual(len(notifications), 2)
        first.title = "Files — renamed"
        first.attention = False
        first.emit("name-changed")
        self.assertFalse(jobs.pop()())
        self.assertEqual(notifications[-1][0][0].title, "Files — renamed")
        self.assertFalse(notifications[-1][0][0].needs_attention)

    def test_snapshots_do_not_retain_native_window_objects(self):
        first = FakeWindow("Editor")
        screen = FakeScreen([first])
        wnck = SimpleNamespace(Screen=SimpleNamespace(get_default=lambda: screen),
                               WindowType=SimpleNamespace(NORMAL="normal"))
        snapshots = []
        tracker = WindowTracker(wnck, lambda _: None, lambda windows, _active: snapshots.extend(windows))
        tracker.start()
        screen.windows = []
        screen.active = None
        screen.emit("window-closed", first)
        first.disposed = True
        self.assertEqual(snapshots[0].title, "Editor")
        self.assertEqual(snapshots[0].xid, first.xid)
        self.assertNotIn(first, tracker._window_handlers)
        self.assertNotIn(first, vars(snapshots[0]).values())

    def test_window_close_disconnects_signals(self):
        first = FakeWindow("Files")
        screen = FakeScreen([first])
        wnck = SimpleNamespace(Screen=SimpleNamespace(get_default=lambda: screen),
                               WindowType=SimpleNamespace(NORMAL="normal"))
        jobs = []
        tracker = WindowTracker(wnck, jobs.append, lambda *_: None)
        tracker.start()
        screen.windows = []
        screen.active = None
        screen.emit("window-closed", first)
        # libwnck may dispose the native object before the queued idle redraw.
        first.disposed = True
        jobs.pop()()
        self.assertEqual(len(first.disconnected), 3)
        self.assertEqual(tracker._window_handlers, {})

    def test_unannounced_disposal_never_disconnects_a_stale_native_window(self):
        first = FakeWindow("Files")
        screen = FakeScreen([first])
        wnck = SimpleNamespace(Screen=SimpleNamespace(get_default=lambda: screen),
                               WindowType=SimpleNamespace(NORMAL="normal"))
        jobs = []
        tracker = WindowTracker(wnck, jobs.append, lambda *_: None)
        tracker.start()
        screen.windows = []
        screen.active = None
        first.disposed = True
        screen.emit("active-window-changed")
        jobs.pop()()
        self.assertEqual(tracker._window_handlers, {})

    def test_unavailable_window_screen_is_a_safe_fallback(self):
        wnck = SimpleNamespace(Screen=SimpleNamespace(get_default=lambda: None))
        self.assertFalse(WindowTracker(wnck, lambda _: None, lambda *_: None).start())

    @unittest.skipUnless(os.environ.get("RICEHUB_WNCK_INTEGRATION") == "1",
                         "requires a running X11 window manager and isolated D-Bus session")
    def test_native_window_open_close_does_not_crash_shell(self):
        """Exercise real libwnck/GObject disposal, not only fake Python windows."""
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Wnck", "3.0")
        from gi.repository import Gtk, Wnck

        Wnck.set_client_type(Wnck.ClientType.PAGER)
        wnck_screen = Wnck.Screen.get_default()
        self.assertIsNotNone(wnck_screen)

        repo = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["RICEHUB_AERO_TRAY"] = "0"
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, str(repo / "launcher.py"), "aero-shell"],
                cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )

            def assert_running():
                if process.poll() is not None:
                    log.seek(0)
                    self.fail(f"Aero taskbar exited {process.returncode}: {log.read()[-3000:]}")

            def spin(seconds):
                until = time.monotonic() + seconds
                while time.monotonic() < until:
                    while Gtk.events_pending():
                        Gtk.main_iteration_do(False)
                    assert_running()
                    time.sleep(0.02)

            try:
                spin(0.8)
                for iteration in range(5):
                    title = f"RiceHub lifecycle fixture {iteration}"
                    fixture = Gtk.Window(title=title)
                    fixture.set_default_size(200, 120)
                    fixture.show_all()
                    deadline = time.monotonic() + 1.5
                    while time.monotonic() < deadline:
                        spin(0.05)
                        wnck_screen.force_update()
                        if any(win.get_name() == title for win in wnck_screen.get_windows()):
                            break
                    else:
                        self.fail(f"libwnck did not discover the fixture: {title}")
                    fixture.destroy()
                    spin(0.3)
                assert_running()
                subprocess.run(
                    [sys.executable, str(repo / "launcher.py"), "aero-shell", "--quit"],
                    cwd=repo, env=env, timeout=5, capture_output=True, check=True,
                )
                self.assertEqual(process.wait(timeout=5), 0)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
