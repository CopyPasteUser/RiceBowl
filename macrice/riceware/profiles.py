"""Stable RiceBowl style-to-family identities for gradual UI migrations.

The family selects the renderer only. Device state, file operations and
notification ownership must never depend on the visual family.
"""

from __future__ import annotations


PROFILE_FAMILIES = {
    "night": "macos", "day": "macos", "aqua": "macos",
    "aero-meadow": "win7", "aero-cascade": "win7",
    "ten-dark": "win10", "ten-light": "win10",
    "winxp": "winxp", "winclassic": "win98",
    "chromeos": "chromeos", "frutiger": "frutiger",
}


def family(style: str) -> str:
    try:
        return PROFILE_FAMILIES[style]
    except KeyError as exc:
        raise ValueError(f"Unknown RiceBowl style: {style}") from exc
