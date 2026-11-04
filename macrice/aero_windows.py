"""Event-driven X11 window tracking for the optional Aero task list.

Wnck is an optional desktop library. If its GObject introspection package is
missing, Aero still offers pinned launchers, search and a clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, sqrt


@dataclass(frozen=True)
class WindowSnapshot:
    """Safe task-list data; never keep a libwnck GObject in GTK callbacks."""

    xid: int
    title: str = field(compare=False)
    minimized: bool = field(compare=False)
    mini_icon: object | None = field(compare=False, repr=False)
    group_id: str = field(default="", compare=False)
    large_icon: object | None = field(default=None, compare=False, repr=False)
    needs_attention: bool = field(default=False, compare=False)


def half_screen_geometry(workarea: tuple[int, int, int, int], side: str) -> tuple[int, int, int, int]:
    """Tile in the monitor's usable area, not underneath taskbars or docks."""
    if side not in ("left", "right"):
        raise ValueError(f"Unsupported tile side: {side}")
    x, y, width, height = workarea
    if width < 2 or height < 1:
        raise ValueError("Monitor workarea is too small for two tiled windows")
    left_width = width // 2
    if side == "left":
        return x, y, left_width, height
    return x + left_width, y, width - left_width, height


def closest_workarea(window_geometry: tuple[int, int, int, int],
                     workareas: tuple[tuple[int, int, int, int], ...]) -> tuple[int, int, int, int]:
    """Select the real monitor containing a window, including negative X/Y."""
    if not workareas:
        raise ValueError("No monitor workarea is available")
    x, y, width, height = window_geometry
    center_x, center_y = x + width // 2, y + height // 2

    def distance(area):
        ax, ay, aw, ah = area
        dx = max(ax - center_x, 0, center_x - (ax + aw))
        dy = max(ay - center_y, 0, center_y - (ay + ah))
        return dx * dx + dy * dy

    return min(workareas, key=distance)


def window_layout(workarea: tuple[int, int, int, int], count: int,
                  layout: str) -> tuple[tuple[int, int, int, int], ...]:
    """Safe native-X11 window positions for the Win7 taskbar arrangement menu.

    To prevent postage-stamp windows the menu refuses more than 12 at once.
    Tiled rectangles cover the workarea exactly, including odd pixel sizes.
    """
    if layout not in ("cascade", "stacked", "side-by-side"):
        raise ValueError("Unknown window layout")
    x, y, width, height = workarea
    if count <= 0 or count > 12 or width < 320 or height < 240:
        return ()
    if layout == "cascade":
        step = min(32, width // (count + 4), height // (count + 4))
        rectangles = [(x + index * step, y + index * step,
                       width - step * (count - 1) - width // 5,
                       height - step * (count - 1) - height // 5)
                      for index in range(count)]
    else:
        if count <= 3:
            columns = count if layout == "side-by-side" else 1
        else:
            columns = ceil(sqrt(count)) if layout == "side-by-side" else max(1, int(sqrt(count)))
        rows = ceil(count / columns)
        rectangles = []
        for index in range(count):
            row, column = divmod(index, columns)
            left, right = x + width * column // columns, x + width * (column + 1) // columns
            top, bottom = y + height * row // rows, y + height * (row + 1) // rows
            rectangles.append((left, top, right - left, bottom - top))
    if any(width < 180 or height < 120 for _x, _y, width, height in rectangles):
        return ()
    return tuple(rectangles)


class WindowSnapController:
    """Use the existing X11 WM; never install global window hooks or hotkeys.

    Only immutable geometry and the former maximization state are retained.
    Wnck windows are resolved on every action so closing an app cannot leave
    an invalid GObject in a GTK menu or Python callback.
    """

    def __init__(self, wnck):
        self.wnck = wnck
        self.original: dict[int, tuple[tuple[int, int, int, int], bool]] = {}

    def forget_closed(self, live_xids) -> None:
        live = set(live_xids)
        for xid in tuple(self.original):
            if xid not in live:
                del self.original[xid]

    def place(self, xid: int, geometry: tuple[int, int, int, int], timestamp: int) -> bool:
        """Position an existing normal window, keeping one reversible snapshot."""
        if len(geometry) != 4 or geometry[2] < 1 or geometry[3] < 1:
            return False
        window = self.wnck.Window.get(xid)
        if (window is None or window.get_window_type() != self.wnck.WindowType.NORMAL
                or window.is_skip_tasklist() or window.is_fullscreen()):
            return False
        if xid not in self.original:
            self.original[xid] = (tuple(window.get_geometry()), bool(window.is_maximized()))
        if window.is_maximized():
            window.unmaximize()
        self._move(window, geometry)
        if window.is_minimized():
            window.unminimize(timestamp)
        window.activate(timestamp)
        return True

    def arrange(self, xid: int, action: str, workarea: tuple[int, int, int, int],
                timestamp: int) -> bool:
        if action not in ("left", "right", "maximize", "restore"):
            return False
        window = self.wnck.Window.get(xid)
        if (window is None or window.get_window_type() != self.wnck.WindowType.NORMAL
                or window.is_skip_tasklist() or window.is_fullscreen()):
            return False
        if action == "restore":
            previous = self.original.pop(xid, None)
            if previous is None:
                return False
            geometry, was_maximized = previous
            if was_maximized:
                window.maximize()
            else:
                if window.is_maximized():
                    window.unmaximize()
                self._move(window, geometry)
        else:
            if action in ("left", "right"):
                try:
                    target = half_screen_geometry(workarea, action)
                except ValueError:
                    return False
                return self.place(xid, target, timestamp)
            if xid not in self.original:
                self.original[xid] = (tuple(window.get_geometry()), bool(window.is_maximized()))
            window.maximize()
        if window.is_minimized():
            window.unminimize(timestamp)
        window.activate(timestamp)
        return True

    def _move(self, window, geometry) -> None:
        mask = self.wnck.WindowMoveResizeMask
        window.set_geometry(self.wnck.WindowGravity.NORTHWEST,
                            mask.X | mask.Y | mask.WIDTH | mask.HEIGHT, *geometry)


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
                # WM_CLASS is the closest native X11 analogue to Win7 AppUserModelID.
                # Never retain a libwnck class-group object beyond this refresh.
                class_group = getattr(window, "get_class_group", lambda: None)()
                group_id = (class_group.get_id() or "").strip() if class_group else ""
                snapshots.append(WindowSnapshot(xid, window.get_name() or "Application",
                                                bool(window.is_minimized()), window.get_mini_icon(),
                                                group_id, window.get_icon(),
                                                bool(getattr(window, "needs_attention", lambda: False)())))
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
