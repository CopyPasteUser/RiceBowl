"""Read-only, privacy-conscious desktop detection.

Never query SSIDs, IP addresses, device serial numbers, wallpaper paths or
private dotfiles. Appearance values are sufficient for theme suggestions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


def config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")


def bin_home() -> Path:
    return Path(os.environ.get("XDG_BIN_HOME") or Path.home() / ".local/bin")


def _query(*argv: str) -> str | None:
    if not shutil.which(argv[0]):
        return None
    try:
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=1.5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode:
        return None
    value = proc.stdout.strip().strip("'")
    return value[:120] if value else None


def _xfconf(channel: str, key: str) -> str | None:
    return _query("xfconf-query", "-c", channel, "-p", key)


@dataclass(frozen=True)
class DesktopProfile:
    desktop: str
    gtk_theme: str | None
    icon_theme: str | None
    cursor_theme: str | None
    window_theme: str | None
    font: str | None
    plank_theme: str | None
    plank_position: str | None = None
    plank_icon_size: str | None = None
    plank_hide_mode: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "desktop": self.desktop,
            "gtk_theme": self.gtk_theme,
            "icon_theme": self.icon_theme,
            "cursor_theme": self.cursor_theme,
            "window_theme": self.window_theme,
            "font": self.font,
            "plank_theme": self.plank_theme,
            "plank_position": self.plank_position,
            "plank_icon_size": self.plank_icon_size,
            "plank_hide_mode": self.plank_hide_mode,
        }


def detect() -> DesktopProfile:
    from .plank import preferences

    dock = preferences()
    return DesktopProfile(
        desktop=os.environ.get("XDG_CURRENT_DESKTOP", "unknown")[:80],
        gtk_theme=_xfconf("xsettings", "/Net/ThemeName"),
        icon_theme=_xfconf("xsettings", "/Net/IconThemeName"),
        cursor_theme=_xfconf("xsettings", "/Gtk/CursorThemeName"),
        window_theme=_xfconf("xfwm4", "/general/theme"),
        font=_xfconf("xsettings", "/Gtk/FontName"),
        plank_theme=dock.theme,
        plank_position=dock.position,
        plank_icon_size=dock.icon_size,
        plank_hide_mode=dock.hide_mode,
    )


def installed_components() -> dict[str, bool]:
    from .plank import installed

    executable = {
        "MacMenu": bin_home() / "macmenu",
        "Control Center": bin_home() / "macos-control-center-toggle",
        "MacBar": bin_home() / "macbar",
    }
    result = {name: path.is_file() and os.access(path, os.X_OK) for name, path in executable.items()}
    result["Plank"] = installed()
    return result
