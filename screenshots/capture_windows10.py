#!/usr/bin/env python3
"""Capture the real GTK Windows 10 prototype inside an X11 display.

Run with xvfb-run on CI or a disposable X11 session. No XFCE profile is applied.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from macrice.windows10_proto import show_dialog


if __name__ == "__main__":
    if not Gtk.init_check()[0]:
        raise SystemExit("An X11 GTK display is required for screenshot capture")
    show_dialog(None, Gtk, Gdk, GLib, (
        ROOT / "screenshots/windows10-start-preview-0.5.0rc2.png",
        ROOT / "screenshots/windows10-action-center-preview-0.5.0rc2.png",
    ))
