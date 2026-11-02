#!/usr/bin/env python3
"""Capture the Windows 10 selection in the actual RiceHub GTK application."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from macrice.hub import run


def descendants(widget):
    yield widget
    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            yield from descendants(child)


def capture():
    app = Gtk.Application.get_default()
    window = app.get_active_window()
    if window is None:
        raise RuntimeError("RiceHub did not open its main window")

    def save():
        pixels = Gdk.pixbuf_get_from_window(window.get_window(), 0, 0, *window.get_size())
        if pixels is None:
            raise RuntimeError("Unable to capture the RiceHub gallery")
        pixels.savev(str(ROOT / "screenshots/ricehub-windows10-gallery-0.5.0rc2.png"), "png", [], [])
        app.quit()
        return False

    for widget in descendants(window):
        if isinstance(widget, Gtk.Button) and (widget.get_accessible().get_name() or "").startswith(
                "Windows 10 —"):
            widget.clicked()
            GLib.timeout_add(450, save)
            return False
    raise RuntimeError("Windows 10 catalog button was not found")


if __name__ == "__main__":
    if not Gtk.init_check()[0]:
        raise SystemExit("An X11 GTK display is required for screenshot capture")
    GLib.timeout_add(850, capture)
    raise SystemExit(run())
