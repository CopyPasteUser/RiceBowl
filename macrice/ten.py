"""User-local Windows 10 artwork and managed Xfce/X11 shell autostart.

The installer deliberately refuses to replace customized directories or
autostart entries. Existing generic Aero asset staging is reused.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .aero import AeroAssetError, preflight as preflight_bundles
from .environment import bin_home


THEMES = ("RiceHub-Ten-Dark", "RiceHub-Ten-Light")
ICON_THEME = "RiceHub-Ten"
BUNDLES = tuple((f"assets/themes/{theme}", f"themes/{theme}") for theme in THEMES) + (
    ("assets/icons/RiceHub-Ten", "icons/RiceHub-Ten"),
)
MARKER = "# RiceHub Windows 10 autostart (managed by RiceHub)"


def preflight(source_root: Path, data_root: Path) -> list[tuple[Path, Path]]:
    return preflight_bundles(source_root, data_root, BUNDLES)


def autostart_file(config_root: Path) -> Path:
    return config_root / "autostart/ricehub-ten-shell.desktop"


def autostart_content(source_root: Path) -> str:
    command = str(bin_home() / "macrice").replace('"', '\\"')
    icon = str(source_root / "assets/ten-start.svg").replace('"', '\\"')
    return (
        "[Desktop Entry]\nType=Application\nVersion=1.0\n"
        "Name=RiceHub Windows 10 Taskbar\n"
        "Comment=Windows 10-inspired Start menu and taskbar for XFCE/X11\n"
        f'Exec="{command}" windows10-shell\nIcon={icon}\n'
        "Terminal=false\nOnlyShowIn=XFCE;\nX-GNOME-Autostart-enabled=true\n"
        f"{MARKER}\n"
    )


def read_autostart(config_root: Path) -> str | None:
    target = autostart_file(config_root)
    if target.is_symlink() or target.parent.is_symlink():
        raise AeroAssetError("Unmanaged symlink at Windows 10 autostart path")
    if not target.exists():
        return None
    if not target.is_file() or target.stat().st_size > 16 * 1024:
        raise AeroAssetError("Unexpected file at Windows 10 autostart path")
    content = target.read_text(encoding="utf-8")
    from .installer import project_root
    if content != autostart_content(project_root()):
        raise AeroAssetError("Existing Windows 10 autostart is not managed by RiceHub or was customized")
    return content


def write_autostart(config_root: Path, content: str | None) -> None:
    target = autostart_file(config_root)
    read_autostart(config_root)
    if content is None:
        target.unlink(missing_ok=True)
        return
    from .installer import project_root
    if content != autostart_content(project_root()):
        raise AeroAssetError("Refusing non-canonical Windows 10 autostart content")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".ricehub-ten-start-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, target)
    finally:
        Path(temp).unlink(missing_ok=True)
