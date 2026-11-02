"""Installable RiceHub XP, Classic, ChromeOS and Aqua profiles.

Every profile shares the proven GTK/X11 taskbar engine and reversible XFCE
transaction. Only RiceHub-owned themes and login entries are managed.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .aero import AeroAssetError, preflight as preflight_bundles
from .environment import bin_home


@dataclass(frozen=True)
class HeritageProfile:
    key: str
    name: str
    theme: str
    icon_theme: str
    wallpaper: str
    start_label: str
    menu_heading: str
    control_heading: str
    logo: str
    menu_layout: str


PROFILES = {
    "winxp": HeritageProfile("winxp", "Windows XP Luna", "RiceHub-Luna", "RiceHub-Luna-Icons",
                              "luna-hills.jpg", "start", "All Programs", "Control Panel",
                              "aero-penguin.svg", "classic"),
    "winclassic": HeritageProfile("winclassic", "Windows 98 / 2000", "RiceHub-Classic", "RiceHub-Classic-Icons",
                                   "classic-teal.jpg", "Start", "Programs", "Control Panel",
                                   "ten-start.svg", "classic"),
    "chromeos": HeritageProfile("chromeos", "ChromeOS", "RiceHub-Chrome", "RiceHub-Chrome-Icons",
                                 "chrome-pastel.jpg", "Apps", "Launcher", "Quick Settings",
                                 "ten-start.svg", "tiles"),
    "frutiger": HeritageProfile("frutiger", "Y2K / Frutiger Aero", "RiceHub-Frutiger", "RiceHub-Frutiger-Icons",
                                 "frutiger-future.jpg", "Apps", "Applications", "Quick Settings",
                                 "aero-penguin.svg", "classic"),
}

BY_THEME = {profile.theme: profile for profile in PROFILES.values()}


def bundles(key: str) -> tuple[tuple[str, str], ...]:
    profile = PROFILES[key]
    return ((f"assets/themes/{profile.theme}", f"themes/{profile.theme}"),
            (f"assets/icons/{profile.icon_theme}", f"icons/{profile.icon_theme}"))


def preflight(key: str, source_root: Path, data_root: Path) -> list[tuple[Path, Path]]:
    return preflight_bundles(source_root, data_root, bundles(key))


def _target(key: str, config_root: Path) -> Path:
    return config_root / f"autostart/ricehub-{key}-shell.desktop"


def autostart_content(key: str) -> str:
    profile = PROFILES[key]
    executable = str(bin_home() / "macrice").replace('"', '\\"')
    return (
        "[Desktop Entry]\nType=Application\nVersion=1.0\n"
        f"Name=RiceHub {profile.name} Shell\n"
        f"Comment=Native RiceHub {profile.name} taskbar\n"
        f'Exec="{executable}" {key}-shell\n'
        "Terminal=false\nOnlyShowIn=XFCE;\nX-GNOME-Autostart-enabled=true\n"
        f"# RiceHub {key} autostart (managed by RiceHub)\n"
    )


def read_autostart(key: str, config_root: Path) -> str | None:
    target = _target(key, config_root)
    if target.is_symlink() or target.parent.is_symlink():
        raise AeroAssetError(f"Unmanaged symlink at {key} autostart path")
    if not target.exists():
        return None
    if not target.is_file() or target.stat().st_size > 16 * 1024:
        raise AeroAssetError(f"Unexpected file at {key} autostart path")
    content = target.read_text(encoding="utf-8")
    if content != autostart_content(key):
        raise AeroAssetError(f"Existing {key} autostart was customized; refusing overwrite")
    return content


def write_autostart(key: str, config_root: Path, content: str | None) -> None:
    target = _target(key, config_root)
    read_autostart(key, config_root)
    if content is None:
        target.unlink(missing_ok=True)
        return
    if content != autostart_content(key):
        raise AeroAssetError("Refusing non-canonical shell autostart")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".ricehub-{key}-start-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
