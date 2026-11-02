#!/usr/bin/env python3
"""Capture actual RiceHub Ten GTK windows against a disposable X11 wallpaper fixture.

Run with xvfb-run or a disposable virtual X11 display. Never applies rice.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from macrice.ten_shell import run


if __name__ == "__main__":
    raise SystemExit(run(["ricehub-ten-shell", "--capture-gallery"]))
