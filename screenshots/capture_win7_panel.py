#!/usr/bin/env python3
"""Capture the real Win7 Aero XFWM4 frame and GTK Control Panel in Xvfb.

The virtual desktop uses an isolated HOME and never changes host XFCE prefs.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from screenshots.capture_native_workspace import prepare_isolated_desktop  # noqa: E402
from macrice.aero_shell import run  # noqa: E402


def main() -> int:
    if not os.environ.get("DISPLAY"):
        raise SystemExit("Capture requires a disposable Xvfb display")
    with tempfile.TemporaryDirectory(prefix="ricebowl-win7-panel-") as directory:
        prepare_isolated_desktop(Path(directory), "aero")
        wm = subprocess.Popen(
            ["xfwm4", "--compositor=off", "--vblank=off"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            return run(["ricebowl-aero-shell", "--capture-gallery"], profile="aero")
        finally:
            wm.terminate()
            try:
                wm.wait(timeout=5)
            except subprocess.TimeoutExpired:
                wm.kill()
                wm.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
