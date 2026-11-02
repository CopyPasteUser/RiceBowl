"""Wnck's optional event-driven task list, tested without an X server."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace

from macrice.aero_windows import (WindowSnapshot, WindowTracker, is_task_window,
                                 toggle_window, toggle_window_id)


class FakeWindow:
    next_handler = 0
    next_xid = 100

    def __init__(self, title, kind="normal", skipped=False):
        self.title, self.kind, self.skipped = title, kind, skipped
        self.signals = {}
        self.disconnected = []
        self.minimized = False
        self.calls = []
        self.disposed = False
        FakeWindow.next_xid += 1
        self.xid = FakeWindow.next_xid

    def get_xid(self):
        return self.xid

    def get_mini_icon(self):
        return None

    def get_window_type(self):
        return self.kind

    def is_skip_tasklist(self):
        return self.skipped

    def get_name(self):
        return self.title

    def is_minimized(self):
        return self.minimized

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
        first.emit("name-changed")
        self.assertFalse(jobs.pop()())
        self.assertEqual(notifications[-1][0][0].title, "Files — renamed")

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
