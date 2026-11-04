"""ricePlate: a read-only desktop model plus safe opt-in XFDesktop shortcuts.

Rendering, DnD and file mutations remain with XFDesktop/GIO/riceExplorer.
This module never replaces XFDesktop or modifies wallpaper and icon positions.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass
from pathlib import Path

from .. import luna_desktop, win7_desktop


@dataclass(frozen=True)
class DesktopItem:
    filename: str
    path: str
    kind: str  # launcher, directory, file, link


@dataclass(frozen=True)
class DesktopSnapshot:
    folder: str
    exists: bool
    items: tuple[DesktopItem, ...]
    truncated: bool = False


def snapshot(folder: Path | None = None, *, limit: int = 512) -> DesktopSnapshot:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 4096:
        raise ValueError("Desktop item limit must be between 1 and 4096")
    folder = folder if folder is not None else luna_desktop.desktop_path()
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise ValueError("Unsafe desktop directory")
    if not folder.exists():
        return DesktopSnapshot(str(folder), False, ())
    items = []
    # Bounded memory even with an unexpectedly huge desktop directory.
    selected = heapq.nsmallest(limit + 1, folder.iterdir(),
                               key=lambda item: (item.name.casefold(), item.name))
    for path in selected[:limit]:
        kind = ("link" if path.is_symlink() else "directory" if path.is_dir()
                else "launcher" if path.suffix == ".desktop" and path.is_file()
                else "file" if path.is_file() else "other")
        items.append(DesktopItem(path.name, str(path), kind))
    return DesktopSnapshot(str(folder), True, tuple(items), len(selected) > limit)


def manage_shortcuts(profile: str, action: str, *, folder: Path | None = None,
                     catalog: dict[str, str] | None = None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Reuse the existing, byte-identical removal protections for XP/Win7."""
    if profile == "xp":
        return luna_desktop.manage(action, folder=folder, catalog=catalog)
    if profile == "win7":
        return win7_desktop.manage(action, folder=folder, catalog=catalog)
    raise ValueError("Managed desktop shortcut profiles are xp and win7")
