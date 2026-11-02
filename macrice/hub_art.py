"""Small GTK3 image helpers; no Cairo Python bindings required."""

from __future__ import annotations

from math import ceil


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
