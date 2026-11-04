"""Opt-in XP desktop launchers for XFDesktop, never a replacement desktop daemon.

Only RiceBowl-owned, byte-identical desktop entries can be removed. Existing
user files and even edited RiceBowl entries are always preserved.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path


def desktop_path(home: Path | None = None, config: Path | None = None) -> Path:
    home = home or Path.home()
    config = config or Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    setting = config / "user-dirs.dirs"
    try:
        value = re.search(r'^XDG_DESKTOP_DIR="([^"\n]*)"\s*$',
                          setting.read_text(encoding="utf-8"), re.MULTILINE)
        if value:
            decoded = value.group(1).replace("$HOME", str(home), 1)
            path = Path(decoded)
            if path.is_absolute() and path != home and home in path.parents:
                return path
    except (OSError, UnicodeError):
        pass
    return home / "Desktop"


def _desktop_entry(label: str, icon: str, uri: str) -> str:
    # Desktop Entry Exec field codes use %, unlike a shell or URL. Escape it.
    escaped = uri.replace("%", "%%").replace("\\", "\\\\").replace('"', '\\"')
    return ("[Desktop Entry]\nType=Application\nVersion=1.0\n"
            f"Name={label}\nComment=Open {label} using the default file manager\n"
            f"Icon={icon}\nExec=gio open \"{escaped}\"\nTerminal=false\n"
            "StartupNotify=true\nX-RiceBowl-XP-Managed=true\n")


def entries(home: Path | None = None) -> dict[str, str]:
    home = home or Path.home()
    from gi.repository import GLib

    documents = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    docs = Path(documents) if documents else home / "Documents"
    # If Documents doesn't exist, use the user's real home and make it explicit.
    label = "My Documents" if docs.is_dir() else "My Documents (Home)"
    return {
        "ricebowl-xp-computer.desktop": _desktop_entry("My Computer", "computer", "computer:///"),
        "ricebowl-xp-documents.desktop": _desktop_entry(
            label, "folder-documents", (docs if docs.is_dir() else home).as_uri()),
        "ricebowl-xp-network.desktop": _desktop_entry(
            "My Network Places", "network-workgroup", "network:///"),
        "ricebowl-xp-trash.desktop": _desktop_entry("Recycle Bin", "user-trash", "trash:///"),
    }


def manage(action: str, *, folder: Path | None = None,
           catalog: dict[str, str] | None = None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (changed, preserved); write/create only with explicit install.

    `remove` deletes only files exactly matching our generated content. `status`
    is read-only and reports which managed entries are absent/modified.
    """
    if action not in ("install", "remove", "status"):
        raise ValueError("Expected install, remove or status")
    folder = folder or desktop_path()
    catalog = catalog if catalog is not None else entries()
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise ValueError("Desktop directory must not be a symlink or regular file")
    if action == "install" and not folder.exists():
        raise RuntimeError("Desktop directory does not exist; set it up in XFCE first")
    changed, preserved = [], []
    for filename, content in catalog.items():
        if not re.fullmatch(r"ricebowl-xp-[a-z-]+\.desktop", filename):
            raise ValueError("Unexpected desktop entry name")
        target = folder / filename
        if target.is_symlink() or (target.exists() and not target.is_file()):
            preserved.append(filename + " (unsafe target)")
            continue
        if target.exists():
            try:
                matches = target.read_text(encoding="utf-8") == content
            except (OSError, UnicodeError):
                matches = False
            if not matches:
                preserved.append(filename + " (user-modified or existing)")
                continue
            if action == "remove":
                target.unlink()
                changed.append(filename)
            else:
                preserved.append(filename + " (installed)")
        elif action == "install":
            descriptor, temporary = tempfile.mkstemp(prefix=".ricebowl-xp-", dir=folder)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(temporary, 0o755)
                # Hard link ensures an existing user file is never overwritten.
                os.link(temporary, target)
                changed.append(filename)
            except FileExistsError:
                preserved.append(filename + " (created by another process)")
            finally:
                Path(temporary).unlink(missing_ok=True)
    return tuple(changed), tuple(preserved)
