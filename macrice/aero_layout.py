"""Pure, bounded layout decisions for the XFCE/X11 Aero shell.

Keeping screen geometry in one module prevents off-screen menus and makes
small-display behavior testable without GTK or an X server.
"""
from __future__ import annotations

PANEL_HEIGHT = 53


def menu_geometry(x: int, y: int, width: int, height: int,
                  preferred_width: int = 490, preferred_height: int = 505,
                  margin: int = 8, panel_height: int = PANEL_HEIGHT) -> tuple[int, int, int, int]:
    """Place the Start menu directly above the panel, inside its monitor.

    Returns (x, y, width, height). Caller must avoid showing the menu
    if the monitor is too small for an accessible menu (width < 180,
    height < 180).
    """
    w = max(0, min(preferred_width, width - 2 * margin))
    h = max(0, min(preferred_height, height - panel_height - 2 * margin))
    return (x + margin, y + height - panel_height - margin - h, w, h)


def actual_popup_y(monitor_y: int, monitor_height: int, actual_height: int,
                   margin: int = 8, panel_height: int = PANEL_HEIGHT) -> int:
    """Anchor a mapped GTK popup using its real, not requested, height."""
    return max(monitor_y + margin,
               monitor_y + monitor_height - panel_height - margin - actual_height)


def task_capacity(width: int, pinned: int, tray_reserve: int = 185) -> int:
    """Conservatively reserve space for Start, launchers, status and tray.

    Task overflow is mandatory when there is no space; never force the
    panel larger than the monitor solely to display window titles.
    """
    reserved = 125 + min(max(pinned, 0), 6) * 48 + max(tray_reserve, 0)
    return max(0, min(9, (width - reserved) // 145))


def select_windows(windows: tuple, active, capacity: int) -> tuple[tuple, tuple]:
    """Preserve stable task order while ensuring the active task is visible."""
    count = max(0, capacity)
    visible = list(windows[:count])
    if visible and active in windows and active not in visible:
        visible[-1] = active
    return tuple(visible), tuple(window for window in windows if window not in visible)


def bottom_strut(x: int, y: int, width: int, height: int,
                 root_height: int, panel_height: int = PANEL_HEIGHT) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """EWMH bottom strut and partial strut; zero when not on root bottom edge.

    A monitor floating above another monitor must not reserve a global strip.
    """
    bottom = panel_height if width > 0 and height >= panel_height and y + height == root_height else 0
    short = (0, 0, 0, bottom)
    partial = (0, 0, 0, bottom, 0, 0, 0, 0, 0, 0,
               max(0, x) if bottom else 0,
               max(0, x + width - 1) if bottom else 0)
    return short, partial
