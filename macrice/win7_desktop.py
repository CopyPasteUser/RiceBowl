"""Explicit, recoverable Windows 7 desktop links managed by XFDesktop.

Only byte-identical RiceBowl Windows 7 shortcuts may be removed. No user
desktop files, default file associations or XFDesktop configuration are changed.
"""

from __future__ import annotations

from pathlib import Path

from .luna_desktop import _desktop_entry, desktop_path, manage as _manage


def _entry(label: str, icon: str, uri: str) -> str:
    return _desktop_entry(label, icon, uri, managed_marker="X-RiceBowl-Win7-Managed")


def entries(home: Path | None = None) -> dict[str, str]:
    home = home or Path.home()
    from gi.repository import GLib

    documents = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    docs = Path(documents) if documents else home / "Documents"
    return {
        "ricebowl-win7-computer.desktop": _entry("Computer", "computer", "computer:///"),
        "ricebowl-win7-documents.desktop": _entry(
            "Documents" if docs.is_dir() else "Documents (Home)",
            "folder-documents", (docs if docs.is_dir() else home).as_uri()),
        "ricebowl-win7-network.desktop": _entry("Network", "network-workgroup", "network:///"),
        "ricebowl-win7-trash.desktop": _entry("Recycle Bin", "user-trash", "trash:///"),
    }


def manage(action: str, *, folder: Path | None = None,
           catalog: dict[str, str] | None = None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return _manage(action, folder=folder, catalog=entries() if catalog is None else catalog,
                   prefix="ricebowl-win7")
