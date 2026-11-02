"""Wnck's optional event-driven task list, tested without an X server."""

import unittest
from types import SimpleNamespace

from macrice.aero_windows import WindowTracker, is_task_window, toggle_window


class FakeWindow:
    next_handler = 0

    def __init__(self, title, kind="normal", skipped=False):
        self.title, self.kind, self.skipped = title, kind, skipped
        self.signals = {}
        self.disconnected = []
        self.minimized = False
        self.calls = []
        self.disposed = False

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

    def test_window_signals_are_coalesced_without_polling(self):
        first, second = FakeWindow("Files"), FakeWindow("Start", "utility")
        screen = FakeScreen([first, second])
        wnck = SimpleNamespace(Screen=SimpleNamespace(get_default=lambda: screen),
                               WindowType=SimpleNamespace(NORMAL="normal"))
        jobs, notifications = [], []
        tracker = WindowTracker(wnck, jobs.append, lambda windows, active: notifications.append((windows, active)))
        self.assertTrue(tracker.start())
        self.assertEqual(notifications, [((first,), first)])
        first.emit("name-changed")
        first.emit("icon-changed")
        screen.emit("active-window-changed")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(len(notifications), 1)
        self.assertFalse(jobs.pop()())
        self.assertEqual(len(notifications), 2)

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


if __name__ == "__main__":
    unittest.main()
