"""Start the selected RiceHub shell and quit the inactive managed shell.

Only targets RiceHub's own Gtk.Application IDs. Never kills xfce4-panel or
other user processes. The X11 session must already be running.
"""

from __future__ import annotations

import os
import subprocess
import sys

from .installer import project_root


SHELLS = {"aero": "aero-shell", "ten": "windows10-shell"}


def sync_theme(theme: str) -> tuple[str, ...]:
    if not os.environ.get("DISPLAY"):
        return ()
    desired = "aero" if theme == "RiceHub-Aero" else "ten" if theme in (
        "RiceHub-Ten-Dark", "RiceHub-Ten-Light") else None
    warnings = []
    # A quit is a remote Gtk.Application command; wait for it to finish before
    # starting another taskbar, otherwise the docks can briefly overlap.
    for profile, command in SHELLS.items():
        if profile == desired:
            continue
        argv = [sys.executable, str(project_root() / "launcher.py"), command, "--quit"]
        try:
            result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, text=True, timeout=4, check=False)
            if result.returncode:
                warnings.append(f"{profile} taskbar did not quit: {result.stderr.strip()[:160]}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            warnings.append(f"{profile} taskbar did not quit: {exc}")
    if desired is not None and not warnings:
        try:
            subprocess.Popen([sys.executable, str(project_root() / "launcher.py"), SHELLS[desired]],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            warnings.append(f"Could not start {desired} taskbar: {exc}")
    return tuple(warnings)
