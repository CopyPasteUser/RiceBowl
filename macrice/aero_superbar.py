"""Pure Windows 7 Superbar model: stable X11 WM_CLASS grouping and overflow.

The GTK shell consumes copied immutable snapshots; no Wnck GObjects are held
inside callbacks, timers, or cached previews after a window closes.
"""
from __future__ import annotations

from dataclasses import dataclass

from .aero_windows import WindowSnapshot


@dataclass(frozen=True)
class AppGroup:
    key: str
    windows: tuple[WindowSnapshot, ...]

    @property
    def title(self) -> str:
        return self.windows[0].title

    @property
    def xids(self) -> tuple[int, ...]:
        return tuple(window.xid for window in self.windows)


def group_windows(windows: tuple[WindowSnapshot, ...]) -> tuple[AppGroup, ...]:
    """Group by WM_CLASS without merging unidentified or transient windows."""
    by_key: dict[str, list[WindowSnapshot]] = {}
    for window in windows:
        identifier = window.group_id.strip().casefold()
        key = "app:" + identifier if identifier else f"window:{window.xid}"
        by_key.setdefault(key, []).append(window)
    return tuple(AppGroup(key, tuple(members)) for key, members in by_key.items())


def select_groups(groups: tuple[AppGroup, ...], active_xid: int | None,
                  capacity: int) -> tuple[tuple[AppGroup, ...], tuple[AppGroup, ...]]:
    """Keep the active app visible; overflow entire groups, never split windows."""
    visible = list(groups[:max(0, capacity)])
    active = next((group for group in groups if active_xid in group.xids), None)
    if visible and active is not None and active not in visible:
        visible[-1] = active
    return tuple(visible), tuple(group for group in groups if group not in visible)
