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


def sync_theme(theme: str) -> None:
    if not os.environ.get("DISPLAY"):
        return
    desired = "aero" if theme == "RiceHub-Aero" else "ten" if theme in (
        "RiceHub-Ten-Dark", "RiceHub-Ten-Light") else None
    for profile, command in SHELLS.items():
        argv = [sys.executable, str(project_root() / "launcher.py"), command]
        if profile != desired:
            argv.append("--quit")
        try:
            subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            # Autostart remains installed; desktop configuration already applied.
            pass
