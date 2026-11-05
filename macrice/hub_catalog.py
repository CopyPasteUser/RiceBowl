"""RiceBowl's seven installable styles and private restore history."""

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


FAMILIES: tuple[RiceFamily, ...] = (
    RiceFamily(
        "macos", "macOS · Aurora", "MacBar · Control Center",
        "A macOS-inspired desktop with a native app menu, Control Center and optional Plank dock.",
        True, ("night", "day", "aqua"),
        ("Three complete themes", "MacMenu + Control Center", "MacBar + Plank", "Reversible GTK and Thunar styling"),
    ),
    RiceFamily(
        "windows10", "Windows 10", "Flat · Midnight / Blue",
        "A flat taskbar, live app list, pinned Start tiles and functional Action Center.",
        True, ("ten-dark", "ten-light"),
        ("Live Start and taskbar", "Dark/light GTK & XFWM", "Persistent pins & Action Center", "Reversible installation"),
    ),
    RiceFamily(
        "windows7", "Windows 7 · Aero", "Glass · Blue / Night",
        "A 48px glass Superbar, live window previews, Jump Lists and Explorer-style Thunar.",
        True, ("aero-meadow", "aero-cascade"),
        ("Searchable Aero Start", "GTK/XFWM chrome", "Custom icons and wallpapers", "Glass taskbar"),
    ),
    RiceFamily(
        "winxp", "Windows XP · Luna", "Classic 2001 interface",
        "Blue/green taskbar, two-column Start and XP-style category Control Panel.",
        True, ("winxp",), ("Luna taskbar", "Live Start and window list", "XFWM4 window theme", "Recoverable switching"),
    ),
    RiceFamily(
        "winclassic", "Windows 98 SE", "Classic · Teal",
        "Beveled taskbar, cascading Start menus and authentic square window frames.",
        True, ("winclassic",), ("Classic Start", "Live taskbar", "Original classic window chrome", "Recoverable switching"),
    ),
    RiceFamily(
        "chromeos", "ChromeOS", "Material · Pastel",
        "Rounded shelf, searchable app launcher and Linux-backed Quick Settings.",
        True, ("chromeos",), ("Bottom shelf", "Searchable live apps", "Quick settings", "Recoverable switching"),
    ),
    RiceFamily(
        "frutiger", "Frutiger Aero", "Aqua · Nature",
        "Pearl-glass taskbar, nature wallpaper and live Apps / Places / Settings launcher.",
        True, ("frutiger",), ("Aqua taskbar", "Bright original desktop", "Live launchers", "Recoverable switching"),
    ),
)

FAMILY_BY_KEY = {family.key: family for family in FAMILIES}
AVAILABLE_STYLE_KEYS = frozenset(style for family in FAMILIES if family.available for style in family.styles)


def style_options(family_key: str, user_packs=()) -> tuple[tuple[str, str], ...]:
    """Show validated user presets beside their original rice family."""
    from .rice import STYLES

    family = FAMILY_BY_KEY[family_key]
    built_in = tuple((key, STYLES[key].name) for key in family.styles)
    custom = tuple((pack.id, f"{pack.name} · preset") for pack in user_packs
                   if pack.source == "user" and pack.base_style in family.styles)
    return built_in + custom


def selected_style(choice: str | None, user_packs=()) -> tuple[str | None, str | None]:
    """Resolve a dropdown choice to the canonical, reversible rice target."""
    from .rice import STYLES

    if choice in STYLES:
        return choice, STYLES[choice].name
    for pack in user_packs:
        if pack.source == "user" and pack.id == choice and pack.base_style in STYLES:
            return pack.base_style, pack.name
    return None, None


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
