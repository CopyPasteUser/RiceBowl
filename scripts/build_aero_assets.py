#!/usr/bin/env python3
"""Regenerate RiceBowl's original XFWM4 raster chrome and SVG icon artwork.

Development-only: Pillow is required to run this, NOT to install RiceBowl.
Generated assets are tracked so user systems need no imaging dependencies.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
CHROME = ROOT / "assets/themes/RiceHub-Aero/xfwm4"
ICONS = ROOT / "assets/icons/RiceHub-Aero/scalable"


def gradient(size: tuple[int, int], stops: list[tuple[int, int, int]], *, vertical: bool = True) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    extent = max(1, (height if vertical else width) - 1)
    for n in range(extent + 1):
        t = n / extent
        scaled = t * (len(stops) - 1)
        left = min(int(scaled), len(stops) - 2)
        f = scaled - left
        color = tuple(int(stops[left][i] * (1 - f) + stops[left + 1][i] * f) for i in range(3)) + (255,)
        if vertical:
            draw.line((0, n, width, n), fill=color)
        else:
            draw.line((n, 0, n, height), fill=color)
    return image


def frame_assets() -> None:
    CHROME.mkdir(parents=True, exist_ok=True)
    for state, colors in {
        "active": [(213, 247, 255), (135, 201, 239), (82, 161, 213), (141, 207, 244)],
        "inactive": [(238, 246, 250), (202, 222, 233), (172, 203, 221), (210, 228, 240)],
    }.items():
        base = gradient((15, 33), colors)
        # XFWM4 tiles its title slices horizontally; edges/corners are separate sprites.
        for name in ("title-1", "title-2", "title-3", "title-4", "title-5"):
            base.save(CHROME / f"{name}-{state}.png")
        for name, flip in (("top-left", False), ("top-right", True)):
            part = gradient((9, 33), colors)
            d = ImageDraw.Draw(part)
            x = 8 if flip else 0
            d.line([(x, 0), (x, 32)], fill=(36, 100, 153, 235), width=1)
            d.line([(0, 0), (8, 0)], fill=(244, 254, 255), width=1)
            part.save(CHROME / f"{name}-{state}.png")
        border = (47, 108, 158, 255) if state == "active" else (130, 166, 191, 255)
        for name in ("left", "right"):
            tile = gradient((5, 8), colors, vertical=False)
            ImageDraw.Draw(tile).line((0 if name == "left" else 4, 0, 0 if name == "left" else 4, 7), fill=border)
            tile.save(CHROME / f"{name}-{state}.png")
        bottom = gradient((9, 6), list(reversed(colors)))
        ImageDraw.Draw(bottom).line((0, 5, 8, 5), fill=border)
        bottom.save(CHROME / f"bottom-{state}.png")
        for name, flip in (("bottom-left", False), ("bottom-right", True)):
            corner = gradient((9, 8), list(reversed(colors)))
            d = ImageDraw.Draw(corner)
            x = 8 if flip else 0
            d.line((x, 0, x, 7), fill=border)
            d.line((0, 7, 8, 7), fill=border)
            corner.save(CHROME / f"{name}-{state}.png")


def button_assets() -> None:
    for button in ("close", "maximize", "hide", "menu", "stick", "shade"):
        for state in ("active", "inactive", "prelight", "pressed"):
            red = button == "close"
            stops = (
                [(255, 232, 227), (239, 93, 77)] if red else
                [(244, 254, 255), (131, 193, 230)]
            )
            if state == "inactive":
                stops = [(238, 244, 248), (190, 211, 223)]
            elif state == "prelight":
                stops = [(255, 255, 247), (255, 139, 103)] if red else [(245, 255, 255), (99, 202, 251)]
            elif state == "pressed":
                stops = [(189, 79, 68), (242, 163, 147)] if red else [(50, 126, 181), (157, 212, 246)]
            img = gradient((29, 23), stops)
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((1, 0, 27, 21), radius=4, outline=(44, 104, 149, 255), width=1)
            d.line((5, 2, 22, 2), fill=(255, 255, 255, 180), width=1)
            ink = (20, 57, 82, 255)
            if button == "close":
                d.line((11, 7, 18, 15), fill=ink, width=2)
                d.line((18, 7, 11, 15), fill=ink, width=2)
            elif button == "maximize":
                d.rectangle((10, 7, 19, 15), outline=ink, width=2)
                d.line((11, 9, 18, 9), fill=ink, width=1)
            elif button == "hide":
                d.line((10, 15, 19, 15), fill=ink, width=2)
            elif button == "menu":
                d.rounded_rectangle((10, 6, 18, 16), radius=2, outline=ink, width=1)
            elif button == "stick":
                d.ellipse((12, 7, 17, 12), fill=ink)
                d.line((15, 12, 15, 17), fill=ink, width=2)
            else:
                d.polygon([(10, 13), (19, 13), (14, 8)], fill=ink)
            img.save(CHROME / f"{button}-{state}.png")


DEFS = """<defs>
  <linearGradient id="glass" x2="0" y2="1"><stop stop-color="#e8ffff"/><stop offset=".42" stop-color="#91e0ff"/><stop offset="1" stop-color="#2676bb"/></linearGradient>
  <linearGradient id="leaf" x2="0" y2="1"><stop stop-color="#b6f9a2"/><stop offset="1" stop-color="#309f6d"/></linearGradient>
</defs>"""

ART = {
    "places/folder.svg": '<path d="M5 17q0-4 4-4h14l5 5h19q5 0 5 5v27H5Z" fill="#d19c4b"/><path d="M6 23q0-4 4-4h39v26q0 5-5 5H6Z" fill="url(#glass)" stroke="#2671b4" stroke-width="2"/><path d="M9 23h37" stroke="#fff" stroke-width="2" opacity=".8"/>',
    "places/user-home.svg": '<path d="M7 29 32 9l25 20" fill="none" stroke="#266eaa" stroke-width="5" stroke-linejoin="round"/><path d="M15 27h34v28H15Z" fill="url(#glass)" stroke="#266eaa" stroke-width="2"/><path d="M28 37h9v18h-9Z" fill="#e7f9ff" stroke="#4896c7" stroke-width="2"/>',
    "places/computer.svg": '<rect x="6" y="10" width="52" height="37" rx="5" fill="#235d92"/><rect x="9" y="13" width="46" height="30" rx="2" fill="url(#glass)"/><path d="M23 53h18m-9-6v6M17 57h30" stroke="#275b86" stroke-width="4" stroke-linecap="round"/>',
    "places/user-trash.svg": '<path d="M19 18h26l-3 38H22Z" fill="url(#glass)" stroke="#387aa8" stroke-width="2"/><path d="M17 18h30M26 14h12" stroke="#3c789e" stroke-width="4" stroke-linecap="round"/><path d="M28 25v24m8-24v24" stroke="#a0d5ef" stroke-width="3"/>',
    "apps/system-file-manager.svg": '<path d="M8 15h20l5 5h22v30H8Z" fill="url(#glass)" stroke="#2a6eac" stroke-width="2"/><path d="M9 25h45M16 32h17m-17 7h25" stroke="#fff" stroke-opacity=".85" stroke-width="3"/>',
    "apps/web-browser.svg": '<circle cx="32" cy="32" r="26" fill="url(#glass)" stroke="#2e6d9f" stroke-width="2"/><path d="M8 33h48M32 6q-18 24 0 52M32 6q18 24 0 52" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="3"/><path d="M14 17h36m-36 30h36" stroke="#fff" stroke-opacity=".5" stroke-width="2"/>',
    "apps/utilities-terminal.svg": '<rect x="7" y="12" width="50" height="40" rx="5" fill="#183953" stroke="#85c9eb" stroke-width="3"/><path d="m17 23 8 8-8 8m15 0h12" fill="none" stroke="#a7f3c4" stroke-width="4" stroke-linecap="round"/>',
    "apps/preferences-system.svg": '<circle cx="32" cy="32" r="23" fill="url(#glass)" stroke="#2a6eac" stroke-width="3"/><circle cx="32" cy="32" r="13" fill="none" stroke="#e7fcff" stroke-width="7"/><circle cx="32" cy="32" r="5" fill="#298fc5"/><path d="M30 5h4v15m-4 24v15M5 30h15m24 0h15" stroke="#276ba1" stroke-width="5"/>',
    "apps/accessories-calculator.svg": '<rect x="11" y="6" width="42" height="52" rx="5" fill="#347eaa" stroke="#1b4d71" stroke-width="2"/><rect x="17" y="12" width="30" height="12" rx="2" fill="#e8feff"/><path d="M18 33h7m6 0h7m6 0h3M18 42h7m6 0h7m6 0h3M18 51h7m6 0h7m6 0h3" stroke="#def8ff" stroke-width="5" stroke-linecap="round"/>',
    "apps/accessories-text-editor.svg": '<rect x="12" y="7" width="41" height="51" rx="3" fill="#f5fdff" stroke="#528bb8" stroke-width="2"/><path d="M20 19h24M20 27h24M20 35h20M20 43h22" stroke="#90bdd7" stroke-width="3"/><path d="m32 51 15-15 4 4-15 15Z" fill="url(#leaf)"/>',
    "apps/applications-other.svg": '<rect x="9" y="9" width="20" height="20" rx="5" fill="url(#glass)"/><rect x="35" y="9" width="20" height="20" rx="5" fill="url(#leaf)"/><rect x="9" y="35" width="20" height="20" rx="5" fill="url(#leaf)"/><rect x="35" y="35" width="20" height="20" rx="5" fill="url(#glass)"/>',
}


def icon_assets() -> None:
    for path, art in ART.items():
        target = ICONS / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{DEFS}{art}</svg>\n', encoding="utf-8")
    logo = (ROOT / "assets/aero-penguin.svg").read_text(encoding="utf-8")
    for name in ("start-here", "xfce4-menu", "ricehub-aero"):
        (ICONS / "apps" / f"{name}.svg").write_text(logo, encoding="utf-8")


if __name__ == "__main__":
    frame_assets()
    button_assets()
    icon_assets()
    print("Generated original RiceBowl Aero assets")
