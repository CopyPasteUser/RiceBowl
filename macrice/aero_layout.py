"""Pure, bounded layout decisions for the XFCE/X11 Aero shell.

Keeping screen geometry in one module prevents off-screen menus and makes
small-display behavior testable without GTK or an X server.
"""
from __future__ import annotations

PANEL_HEIGHT = 53


def menu_geometry(x: int, y: int, width: int, height: int,
                  preferred_width: int = 490, preferred_height: int = 505,
                  margin: int = 8) -> tuple[int, int, int, int]:
    """Place the Start menu directly above the panel, inside its monitor.

    Returns (x, y, width, height). Caller must avoid showing the menu
    if the monitor is too small for an accessible menu (width < 180,
    height < 180).
    """
    w = max(0, min(preferred_width, width - 2 * margin))
    h = max(0, min(preferred_height, height - PANEL_HEIGHT - 2 * margin))
    return (x + margin, y + height - PANEL_HEIGHT - margin - h, w, h)


def task_capacity(width: int, pinned: int, tray_reserve: int = 185) -> int:
    """Conservatively reserve space for Start, launchers, status and tray.

    Task overflow is mandatory when there is no space; never force the
    panel larger than the monitor solely to display window titles.
    """
    reserved = 125 + min(max(pinned, 0), 4) * 48 + max(tray_reserve, 0)
    return max(0, min(9, (width - reserved) // 145))


def select_windows(windows: tuple, active, capacity: int) -> tuple[tuple, tuple]:
    """Preserve stable task order while ensuring the active task is visible."""
    count = max(0, capacity)
    visible = list(windows[:count])
    if visible and active in windows and active not in visible:
        visible[-1] = active
    return tuple(visible), tuple(window for window in windows if window not in visible)
