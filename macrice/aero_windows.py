"""Event-driven X11 window tracking for the optional Aero task list.

Wnck is an optional desktop library. If its GObject introspection package is
missing, Aero still offers pinned launchers, search and a clock.
"""

from __future__ import annotations


def is_task_window(window, wnck) -> bool:
    """Include only user-facing top-level application windows."""
    return (window.get_window_type() == wnck.WindowType.NORMAL
            and not window.is_skip_tasklist()
            and bool(window.get_name()))


def toggle_window(window, active_window, timestamp: int) -> None:
    """A second click minimizes the active window, like a classic taskbar."""
    if window == active_window and not window.is_minimized():
        window.minimize()
        return
    if window.is_minimized():
        window.unminimize(timestamp)
    window.activate(timestamp)


class WindowTracker:
    """Coalesce Wnck change signals into one GTK-main-loop redraw."""

    def __init__(self, wnck, schedule_idle, on_change):
        self.wnck = wnck
        self.schedule_idle = schedule_idle
        self.on_change = on_change
        self.screen = None
        self._window_handlers = {}
        self._pending = False

    def start(self) -> bool:
        self.screen = self.wnck.Screen.get_default()
        if self.screen is None:
            return False
        for signal in ("window-opened", "active-window-changed"):
            self.screen.connect(signal, self._changed)
        self.screen.connect("window-closed", self._window_closed)
        self.screen.force_update()
        self._refresh()
        return True

    def _changed(self, *_args):
        if not self._pending:
            self._pending = True
            self.schedule_idle(self._refresh)

    def _window_closed(self, _screen, window):
        # The closed WnckWindow can be disposed before the next idle callback.
        # Disconnect its handlers while libwnck still supplies a live object.
        for handler in self._window_handlers.pop(window, ()):
            window.disconnect(handler)
        self._changed()

    def _refresh(self):
        self._pending = False
        windows = tuple(self.screen.get_windows())
        current = set(windows)
        for old_window in tuple(self._window_handlers):
            if old_window not in current:
                # Never call disconnect() on a window that has already gone
                # missing from libwnck. The native GObject may be disposed.
                del self._window_handlers[old_window]
        for window in windows:
            if window not in self._window_handlers:
                self._window_handlers[window] = tuple(
                    window.connect(signal, self._changed)
                    for signal in ("name-changed", "icon-changed", "state-changed"))
        self.on_change(tuple(window for window in windows if is_task_window(window, self.wnck)),
                       self.screen.get_active_window())
        return False


def create_window_tracker(schedule_idle, on_change):
    """Return a running tracker if libwnck3 and an X11 screen are available."""
    try:
        import gi
        gi.require_version("Wnck", "3.0")
        from gi.repository import Wnck
        Wnck.set_client_type(Wnck.ClientType.PAGER)
        tracker = WindowTracker(Wnck, schedule_idle, on_change)
        return tracker if tracker.start() else None
    except (ImportError, ValueError, RuntimeError):
        return None
