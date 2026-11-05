"""ricePlate: shared desktop inventory, appearance and opt-in XFDesktop shortcuts.

The desktop canvas is a preview, not a second desktop owner. XFDesktop retains
wallpaper, desktop icon placement, DnD and file operations until proven safe.
"""

from __future__ import annotations

import configparser
import heapq
import os
import json
from dataclasses import dataclass
from pathlib import Path

from .. import luna_desktop, win7_desktop
from ..environment import config_home
from ..themes import _stage_json
from .profiles import family


DEFAULT_DESKTOP = {
    "win98": (32, "left", True),
    "winxp": (48, "left", True),
    "win7": (48, "left", True),
    "win10": (48, "left", True),
    "chromeos": (48, "left", False),
    "frutiger": (56, "left", True),
    "macos": (56, "right", True),
}
APPEARANCE_KEYS = frozenset(("icon_size", "placement", "show_icons", "show_hidden"))


@dataclass(frozen=True)
class DesktopAppearance:
    style: str
    family: str
    icon_size: int
    placement: str
    show_icons: bool
    show_hidden: bool


def _appearance_value(name: str, value):
    if name == "icon_size":
        if type(value) is not int or not 24 <= value <= 96:
            raise ValueError("Desktop icon size must be 24–96 pixels")
    elif name == "placement":
        if value not in ("left", "right"):
            raise ValueError("Desktop icon placement must be left or right")
    elif name in ("show_icons", "show_hidden"):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a Boolean")
    else:
        raise ValueError(f"Unknown ricePlate preference: {name}")
    return value


def _preferences_path(config_root: Path | None = None) -> Path:
    root = config_root if config_root is not None else config_home()
    parent = root / "ricebowl"
    target = parent / "plate.json"
    if root.is_symlink() or parent.is_symlink() or target.is_symlink():
        raise ValueError("Refusing to access symlinked desktop preferences")
    if parent.exists() and (not parent.is_dir() or parent.stat().st_uid != os.getuid()):
        raise ValueError("Unmanaged desktop preferences directory")
    return target


def _preferences(config_root: Path | None = None) -> dict:
    target = _preferences_path(config_root)
    if not target.exists():
        return {"version": 1, "styles": {}}
    if (not target.is_file() or target.stat().st_uid != os.getuid()
            or target.stat().st_size > 64 * 1024):
        raise ValueError("Unmanaged or oversized desktop preferences")
    try:
        values = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("Could not read desktop preferences; original kept") from exc
    if (not isinstance(values, dict) or type(values.get("version")) is not int
            or values["version"] != 1 or not isinstance(values.get("styles"), dict)):
        raise ValueError("Unsupported desktop preferences format; original kept")
    return values


def appearance(style: str, *, config_root: Path | None = None) -> DesktopAppearance:
    """Read scoped per-rice settings without probing any desktop service."""
    family_name = family(style)
    size, placement, enabled = DEFAULT_DESKTOP[family_name]
    values = _preferences(config_root)["styles"].get(style, {})
    if not isinstance(values, dict):
        raise ValueError("Invalid desktop preferences for this rice")
    resolved = {"icon_size": size, "placement": placement,
                "show_icons": enabled, "show_hidden": False}
    for key, value in values.items():
        resolved[key] = _appearance_value(key, value)
    return DesktopAppearance(style, family_name, **resolved)


def save_appearance(style: str, *, config_root: Path | None = None,
                    **changes) -> DesktopAppearance:
    """Save only this style's preferences; never change XFCE or user files."""
    family(style)  # Validate before touching the filesystem.
    if not changes:
        raise ValueError("No desktop preferences to save")
    for key, value in changes.items():
        _appearance_value(key, value)
    target = _preferences_path(config_root)
    data = _preferences(config_root)
    current = data["styles"].get(style, {})
    if not isinstance(current, dict):
        raise ValueError("Invalid desktop preferences for this rice")
    data["styles"][style] = {**current, **changes}
    if target.parent.exists() and target.parent.stat().st_uid != os.getuid():
        raise ValueError("Desktop preferences belong to another user")
    temporary = _stage_json(target, data)
    try:
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return appearance(style, config_root=config_root)


@dataclass(frozen=True)
class DesktopItem:
    filename: str
    path: str
    kind: str  # launcher, directory, file, link
    display_name: str | None = None
    icon_name: str | None = None
    hidden: bool = False


@dataclass(frozen=True)
class DesktopSnapshot:
    folder: str
    exists: bool
    items: tuple[DesktopItem, ...]
    truncated: bool = False


def _clean(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    value = "".join(char for char in value if char.isprintable()).strip()
    return value[:limit] or None


def _launcher_metadata(path: Path) -> tuple[str | None, str | None, bool]:
    """Read bounded desktop-entry metadata only; never evaluate Exec lines."""
    try:
        if path.is_symlink() or path.stat().st_size > 128 * 1024:
            return None, None, False
        with path.open("r", encoding="utf-8") as stream:
            content = stream.read(128 * 1024 + 1)
        if len(content) > 128 * 1024:
            return None, None, False
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.optionxform = str
        config.read_string(content)
        if not config.has_section("Desktop Entry"):
            return None, None, False
        entry = config["Desktop Entry"]
        return (_clean(entry.get("Name"), 120), _clean(entry.get("Icon"), 256),
                entry.getboolean("Hidden", fallback=False))
    except (OSError, UnicodeError, configparser.Error, ValueError):
        return None, None, False


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
        name, icon, hidden = _launcher_metadata(path) if kind == "launcher" else (None, None, False)
        items.append(DesktopItem(path.name, str(path), kind, name, icon, hidden))
    return DesktopSnapshot(str(folder), True, tuple(items), len(selected) > limit)


def manage_shortcuts(profile: str, action: str, *, folder: Path | None = None,
                     catalog: dict[str, str] | None = None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Reuse the existing, byte-identical removal protections for XP/Win7."""
    if profile == "xp":
        return luna_desktop.manage(action, folder=folder, catalog=catalog)
    if profile == "win7":
        return win7_desktop.manage(action, folder=folder, catalog=catalog)
    raise ValueError("Managed desktop shortcut profiles are xp and win7")
