"""Protect hand-curated RiceBowl vector icons during development asset regeneration.

The 42 design-reviewed SVGs are source assets checked into git, not outputs of
the legacy generic-art generator. Never replace them with its old placeholders.
"""
from __future__ import annotations
from pathlib import Path

CURATED_ICONS = frozenset({
    "apps/system-file-manager.svg",
    "apps/preferences-system.svg",
    "apps/web-browser.svg",
    "apps/utilities-terminal.svg",
    "places/folder.svg",
    "places/user-home.svg",
    "places/user-trash.svg",
})


CURATED_HERITAGE_ICONS = frozenset({
    "places/folder-documents.svg",
    "places/folder-download.svg",
    "places/folder-music.svg",
    "places/folder-pictures.svg",
    "places/folder-videos.svg",
    "places/user-desktop.svg",
    "devices/computer.svg",
    "devices/drive-harddisk.svg",
    "places/network-workgroup.svg",
})


def write_generated_icon(target: Path, relative: str, svg: str, *,
                         heritage: bool = False) -> bool:
    """Write generator-owned icons only; fail if a curated source is missing.

    Returns True if written. This is deliberately strict: a fresh source
    checkout carries curated SVGs; missing ones mean a corrupt build tree.
    """
    if relative in CURATED_ICONS or (heritage and relative in CURATED_HERITAGE_ICONS):
        if not target.is_file() or target.is_symlink():
            raise FileNotFoundError(
                f"Missing hand-curated RiceBowl artwork: {target}. "
                "Restore the source asset from git; do not generate a placeholder."
            )
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg, encoding="utf-8")
    return True
