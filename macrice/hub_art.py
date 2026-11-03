"""Small GTK3 image helpers; no Cairo Python bindings required."""

from __future__ import annotations

from math import ceil


# JPEG thumbs are derived from the actual X11 screenshots because a WebP
# GdkPixbuf loader is not installed on every supported XFCE system.
PREVIEW_FILES = {
    "windows7": "aero.jpg",
    "windows10": "windows10.jpg",
    "winxp": "winxp.jpg",
    "winclassic": "winclassic.jpg",
    "chromeos": "chromeos.jpg",
    "frutiger": "frutiger.jpg",
}

FAMILY_ICONS = {
    "macos": "macrice-symbolic.svg",
    "windows7": "aero-penguin.svg",
    "windows10": "ten-start.svg",
    "winxp": "ricebowl-xp-start.svg",
    "winclassic": "ricebowl-classic-start.svg",
    "chromeos": "ricebowl-chrome-start.svg",
    "frutiger": "ricebowl-frutiger-start.svg",
}


def aspect_fill(pixbuf, width: int, height: int, interpolation):
    """Return a centered crop that covers the exact destination rectangle.

    The parent GTK widget defines the available width; a pixbuf never gets
    to enlarge the window's minimum size. Only called on preview resize.
    """
    if width <= 0 or height <= 0 or pixbuf.get_width() <= 0 or pixbuf.get_height() <= 0:
        raise ValueError("The wallpaper and preview dimensions must be positive")
    scale = max(width / pixbuf.get_width(), height / pixbuf.get_height())
    sw = max(width, ceil(pixbuf.get_width() * scale))
    sh = max(height, ceil(pixbuf.get_height() * scale))
    scaled = pixbuf.scale_simple(sw, sh, interpolation)
    if scaled is None:
        raise ValueError("The wallpaper could not be scaled")
    return scaled.new_subpixbuf((sw - width) // 2, (sh - height) // 2, width, height)


def aspect_contain(pixbuf, width: int, height: int, interpolation):
    """Fit a complete desktop capture without cropping its menus or taskbar."""
    if width <= 0 or height <= 0 or pixbuf.get_width() <= 0 or pixbuf.get_height() <= 0:
        raise ValueError("The screenshot and preview dimensions must be positive")
    scale = min(width / pixbuf.get_width(), height / pixbuf.get_height())
    sw = max(1, int(pixbuf.get_width() * scale))
    sh = max(1, int(pixbuf.get_height() * scale))
    return pixbuf.scale_simple(sw, sh, interpolation)
