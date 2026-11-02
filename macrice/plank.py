"""Read and open the system Plank dock without taking ownership of it.

Plank is GPL-3.0 software distributed separately by the Linux distribution.
MacRice never copies its executable, edits dock items or manages its autostart.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from .environment import _query


DOCK_SCHEMA = "net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/"


@dataclass(frozen=True)
class DockPreferences:
    theme: str | None = None
    position: str | None = None
    icon_size: str | None = None
    hide_mode: str | None = None
    alignment: str | None = None


def installed() -> bool:
    return shutil.which("plank") is not None


def preferences() -> DockPreferences:
    """Inspect dock1 defaults and overrides via its relocatable GSettings path."""
    if not installed():
        return DockPreferences()
    return DockPreferences(
        theme=_query("gsettings", "get", DOCK_SCHEMA, "theme"),
        position=_query("gsettings", "get", DOCK_SCHEMA, "position"),
        icon_size=_query("gsettings", "get", DOCK_SCHEMA, "icon-size"),
        hide_mode=_query("gsettings", "get", DOCK_SCHEMA, "hide-mode"),
        alignment=_query("gsettings", "get", DOCK_SCHEMA, "alignment"),
    )


def running() -> bool:
    if not installed() or not shutil.which("pgrep"):
        return False
    try:
        result = subprocess.run(
            ["pgrep", "-u", str(os.getuid()), "-x", "plank"],
            capture_output=True, timeout=1.5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def open_dock(*, show_preferences: bool = False) -> str:
    """Start the installed dock or show its own settings, never a duplicate dock."""
    executable = shutil.which("plank")
    if not executable:
        raise RuntimeError("Plank is missing. On Linux Mint run: sudo apt install plank")
    if not show_preferences and running():
        return "Plank is already running."
    args = [executable]
    if show_preferences:
        args.append("--preferences")
    subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True,
    )
    return "Plank preferences opened." if show_preferences else "Plank started."
