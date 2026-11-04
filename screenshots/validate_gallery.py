#!/usr/bin/env python3
"""Regression guard: a real GTK settings popup must occupy meaningful area.

Checks PNGs from the same Xvfb display, comparing each actual control-window
region with the corresponding Start screenshot. A clipped title strip (the
0.9 pre-release regression) cannot pass this test.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops


PROFILES = ("aero", "windows10", "winxp", "winclassic", "chromeos", "frutiger")
GALLERY_VERSION = "0.9.1"


def changed_area(menu: Path, controls: Path, profile: str = "") -> tuple[int, int]:
    with Image.open(menu) as a_file, Image.open(controls) as b_file:
        a, b = a_file.convert("RGB"), b_file.convert("RGB")
        if a.size != b.size or a.size != (1600, 900):
            raise ValueError("Screenshot size mismatch; expected 1600x900")
        width, height = a.size
        # Windows 7, XP and now Windows 98 use real centered Control Panel windows;
        # the other profiles keep their right-anchored status popups.
        box = ((width // 2 - 340, 170, width // 2 + 340, 750)
               if profile in ("aero", "winxp", "winclassic") else
               (width - 385, height - 515, width - 6, height - 60))
        diff = ImageChops.difference(a.crop(box), b.crop(box))
        changed = sum(1 for pixel in diff.getdata() if max(pixel) > 18)
        return changed, (box[2] - box[0]) * (box[3] - box[1])


def main() -> None:
    folder = Path("screenshots")
    for name in PROFILES:
        start = folder / f"ricebowl-{name}-start-{GALLERY_VERSION}.png"
        controls = folder / f"ricebowl-{name}-controls-{GALLERY_VERSION}.png"
        if not start.is_file() or not controls.is_file():
            raise SystemExit(f"Missing native GTK screenshots for {name}")
        changed, area = changed_area(start, controls, name)
        print(f"{name} control panel: {changed}/{area} visibly changed pixels")
        if changed < 32_000:
            raise SystemExit(
                f"{name}: the settings window is hidden/clipped or failed "
                f"to render ({changed} changed pixels)")
    # Aero's global GTK viewport palette is Explorer-blue. Its Start program
    # list must explicitly retain the white/ivory Windows 7 surface instead.
    with Image.open(folder / f"ricebowl-aero-start-{GALLERY_VERSION}.png") as preview:
        red, green, blue = preview.convert("RGB").getpixel((160, 700))
        if red < 249 or green < 247 or blue < 243:
            raise SystemExit(
                "Aero program-list viewport inherited the blue GTK background: "
                f"{red},{green},{blue}")
    # Verify that the large Launcher is actually X11-shaped. The Quick Settings
    # UTILITY window has a GTK-owned extra backdrop on some uncomposited Xvfb
    # backends even when the native bounding region is correctly rounded;
    # pixel-exact corner matching would falsely fail for that window. Its
    # area, visibility and monitor bounds are checked above and at capture.
    with (Image.open(folder / f"ricebowl-chromeos-start-{GALLERY_VERSION}.png") as start_file,
          Image.open(folder / f"ricebowl-chromeos-controls-{GALLERY_VERSION}.png") as controls_file):
        start = start_file.convert("RGB")
        controls = controls_file.convert("RGB")
        for x, y in ((16, 208),):
            delta = max(abs(a - b) for a, b in
                        zip(start.getpixel((x, y)), controls.getpixel((x, y))))
            if delta > 28:
                raise SystemExit(
                    f"ChromeOS Launcher has an opaque rectangular backing at {x},{y} "
                    f"(color delta {delta}); check X11 rounded window shaping")
    print("Six native GTK settings windows passed visible-area validation")


if __name__ == "__main__":
    main()

