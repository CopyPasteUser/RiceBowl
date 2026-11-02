"""Event-driven X11 window tracking for the optional Aero task list.

Wnck is an optional desktop library. If its GObject introspection package is
missing, Aero still offers pinned launchers, search and a clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WindowSnapshot:
    """Safe task-list data; never keep a libwnck GObject in GTK callbacks."""

    xid: int
    title: str = field(compare=False)
    minimized: bool = field(compare=False)
    mini_icon: object | None = field(compare=False, repr=False)


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


def toggle_window_id(wnck, screen, xid: int, timestamp: int) -> bool:
    """Resolve a native window only while handling the click; tolerate closure."""
    window = wnck.Window.get(xid)
    if window is None:
        return False
    toggle_window(window, screen.get_active_window(), timestamp)
    return True


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
        # A WnckWindow must never be retained after the close notification.
        for handler in self._window_handlers.pop(int(window.get_xid()), ()):
            window.disconnect(handler)
        self._changed()

    def refresh(self):
        """Rebuild immutable task data after a layout or pin-count change."""
        self._refresh()

    def _refresh(self):
        self._pending = False
        current = set()
        snapshots = []
        for window in self.screen.get_windows():
            xid = int(window.get_xid())
            current.add(xid)
            if xid not in self._window_handlers:
                self._window_handlers[xid] = tuple(
                    window.connect(signal, self._changed)
                    for signal in ("name-changed", "icon-changed", "state-changed"))
            if is_task_window(window, self.wnck):
                snapshots.append(WindowSnapshot(xid, window.get_name() or "Application",
                                                bool(window.is_minimized()), window.get_mini_icon()))
        for old_xid in tuple(self._window_handlers):
            if old_xid not in current:
                # Do not touch a native window that vanished without a signal.
                del self._window_handlers[old_xid]
        active = self.screen.get_active_window()
        active_xid = int(active.get_xid()) if active is not None else None
        active_snapshot = next((window for window in snapshots if window.xid == active_xid), None)
        self.on_change(tuple(snapshots), active_snapshot)
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
