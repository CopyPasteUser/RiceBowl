"""RiceHub's read-only catalog and private restore history.

The macOS, Windows 7 and Windows 10 palettes use the same reversible engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .environment import data_home


@dataclass(frozen=True)
class RiceFamily:
    key: str
    title: str
    subtitle: str
    description: str
    available: bool
    styles: tuple[str, ...] = ()
    features: tuple[str, ...] = ()
    prototype: bool = False


FAMILIES: tuple[RiceFamily, ...] = (
    RiceFamily(
        "macos", "macOS", "Aurora collection",
        "A calm desktop with a native menu bar, application launcher, Control Center and Plank dock.",
        True, ("night", "day", "aqua"),
        ("Three complete themes", "MacMenu + Control Center", "MacBar + Plank", "Reversible GTK and Thunar styling"),
    ),
    RiceFamily(
        "windows10", "Windows 10", "Classic productivity",
        "An installable XFCE/X11 rice with flat window chrome, live taskbar, searchable apps and pinned Start tiles.",
        True, ("ten-dark", "ten-light"),
        ("Live Start and taskbar", "Dark/light GTK & XFWM", "Persistent pins & Action Center", "Reversible installation"), True,
    ),
    RiceFamily(
        "windows7", "Windows 7", "Aero nostalgia",
        "Aero Meadow and Aero Cascade: original glass window chrome, Linux penguin, icons, Start menu and taskbar.",
        True, ("aero-meadow", "aero-cascade"),
        ("Searchable Aero Start", "GTK/XFWM chrome", "Custom icons and wallpapers", "Glass taskbar"), True,
    ),
    RiceFamily(
        "winxp", "Windows XP Luna", "Luna desktop study",
        "Blue taskbar, green Start and two-column launcher with real XFCE applications.",
        True, ("winxp",), ("Luna taskbar", "Live Start and window list", "XFWM4 window theme", "Recoverable switching"), True,
    ),
    RiceFamily(
        "winclassic", "Windows 98 / 2000", "Classic desktop study",
        "Compact gray system controls, teal wallpaper and old-school application navigation.",
        True, ("winclassic",), ("Classic Start", "Live taskbar", "Original classic window chrome", "Recoverable switching"), True,
    ),
    RiceFamily(
        "chromeos", "ChromeOS", "Lightweight shelf study",
        "A modern, airy XFCE shell with a bottom shelf and searchable application drawer.",
        True, ("chromeos",), ("Bottom shelf", "Searchable live apps", "Quick settings", "Recoverable switching"), True,
    ),
    RiceFamily(
        "frutiger", "Y2K / Frutiger Aero", "Aqua future study",
        "An original eco-futurist Linux desktop with turquoise glass, greenery and a playful launcher.",
        True, ("frutiger",), ("Aqua taskbar", "Bright original desktop", "Live launchers", "Recoverable switching"), True,
    ),
)

FAMILY_BY_KEY = {family.key: family for family in FAMILIES}
AVAILABLE_STYLE_KEYS = frozenset(style for family in FAMILIES if family.available for style in family.styles)


@dataclass(frozen=True)
class BackupRecord:
    folder: Path
    style: str
    created: str
    skipped: bool


def recent_backups(data_root: Path | None = None, limit: int = 6) -> list[BackupRecord]:
    """List private Rice backup metadata without exposing user paths in the GUI."""
    root = (data_root or data_home()) / "macrice-state/backups/rice"
    if root.is_symlink() or not root.is_dir():
        return []
    records = []
    for folder in sorted(root.iterdir(), reverse=True):
        if len(records) >= max(0, min(limit, 30)):
            break
        manifest = folder / "manifest.json"
        try:
            if (folder.is_symlink() or not folder.is_dir() or manifest.is_symlink()
                    or not manifest.is_file() or (folder / "failed").exists()
                    or (folder / "restored").exists() or manifest.stat().st_size > 256 * 1024):
                continue
            content = json.loads(manifest.read_text(encoding="utf-8"))
            style = content.get("style", "unknown")
            if not isinstance(style, str) or style not in AVAILABLE_STYLE_KEYS:
                continue
            date = datetime.strptime(folder.name[:21], "%Y%m%dT%H%M%S%f")
            records.append(BackupRecord(folder, style, date.strftime("%Y-%m-%d %H:%M"),
                                        (folder / "skipped.json").is_file()))
        except (ValueError, TypeError, OSError, json.JSONDecodeError):
            continue
    return records


def search_families(query: str, availability: str = "all") -> tuple[RiceFamily, ...]:
    if availability not in ("all", "available", "soon"):
        raise ValueError("Unknown availability filter")
    q = query.strip().casefold()
    return tuple(
        family for family in FAMILIES
        if (availability == "all" or family.available == (availability == "available"))
        and (not q or q in " ".join((family.title, family.subtitle, family.description)).casefold())
    )
