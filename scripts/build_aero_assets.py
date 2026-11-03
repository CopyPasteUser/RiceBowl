#!/usr/bin/env python3
"""Regenerate RiceBowl's original XFWM4 raster chrome and SVG icon artwork.

Development-only: Pillow is required to run this, NOT to install RiceBowl.
Generated assets are tracked so user systems need no imaging dependencies.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw
from ricebowl_artwork import write_generated_icon


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
        "active": [(220, 247, 255), (119, 183, 224), (82, 146, 200), (154, 215, 245)],
        "inactive": [(245, 249, 251), (199, 219, 231), (161, 191, 211), (210, 227, 239)],
    }.items():
        base = gradient((15, 33), colors)
        shine = ImageDraw.Draw(base)
        shine.line((0, 0, 14, 0), fill=(255, 255, 255, 235))
        shine.line((0, 2, 14, 2), fill=(246, 254, 255, 165))
        shine.line((0, 16, 14, 16), fill=(218, 245, 255, 95))
        shine.line((0, 32, 14, 32), fill=(18, 74, 131, 130))
        # XFWM4 tiles its title slices horizontally; edges/corners are separate sprites.
        for name in ("title-1", "title-2", "title-3", "title-4", "title-5"):
            base.save(CHROME / f"{name}-{state}.png")
        for name, flip in (("top-left", False), ("top-right", True)):
            part = base.resize((9, 33))
            d = ImageDraw.Draw(part)
            x = 8 if flip else 0
            d.line([(x, 2), (x, 32)], fill=(26, 91, 151, 235), width=1)
            d.line([(0, 0), (8, 0)], fill=(244, 254, 255), width=1)
            # True rounded outer window corners, not rectangular blue blocks.
            for dy, inset in ((0, 3), (1, 2), (2, 1)):
                for dx in range(inset):
                    part.putpixel((8 - dx if flip else dx, dy), (0, 0, 0, 0))
            part.save(CHROME / f"{name}-{state}.png")
        border = (47, 108, 158, 255) if state == "active" else (130, 166, 191, 255)
        for name in ("left", "right"):
            tile = gradient((5, 8), [(43, 113, 170), (137, 206, 239), (85, 160, 209)]) if state == "active" else gradient((5, 8), colors)
            edge = ImageDraw.Draw(tile)
            edge.line((0 if name == "left" else 4, 0, 0 if name == "left" else 4, 7), fill=border)
            edge.line((1 if name == "left" else 3, 0, 1 if name == "left" else 3, 7), fill=(225, 248, 255, 140))
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
                [(255, 216, 202), (227, 88, 66), (175, 49, 43)] if red else
                [(236, 251, 255), (147, 207, 238), (85, 156, 204)]
            )
            if state == "inactive":
                stops = [(239, 244, 247), (200, 216, 226), (182, 201, 215)]
            elif state == "prelight":
                stops = [(255, 236, 205), (255, 117, 68), (211, 43, 37)] if red else [(255, 255, 255), (148, 224, 255), (74, 170, 229)]
            elif state == "pressed":
                stops = [(159, 58, 48), (227, 121, 92), (193, 68, 50)] if red else [(49, 127, 184), (137, 205, 244), (91, 172, 217)]
            img = gradient((29, 23), stops)
            d = ImageDraw.Draw(img)
            d.rounded_rectangle((1, 0, 27, 21), radius=4, outline=(103, 51, 45, 250) if red else (43, 103, 151, 255), width=1)
            d.line((5, 2, 22, 2), fill=(255, 255, 255, 200), width=1)
            d.line((5, 3, 22, 3), fill=(255, 255, 255, 95), width=1)
            ink = (255, 255, 255, 250) if red else (27, 66, 99, 255)
            if button == "close":
                d.line((11, 7, 18, 15), fill=(104, 35, 31, 220), width=3)
                d.line((18, 7, 11, 15), fill=(104, 35, 31, 220), width=3)
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
    "places/folder-documents.svg": '<path d="M5 16h20l6 6h28v34H5Z" fill="#dca84f" stroke="#996d2f" stroke-width="2"/><path d="M7 25h50v28H7Z" fill="url(#glass)" stroke="#4791c5" stroke-width="2"/><path d="M24 31h24v18H24Z" fill="#fff" stroke="#5a9dcc" stroke-width="1.6"/><path d="M28 36h16m-16 5h16m-16 5h12" stroke="#8ab4d0" stroke-width="2"/>',
    "places/folder-pictures.svg": '<path d="M5 16h20l6 6h28v34H5Z" fill="#dca84f" stroke="#996d2f" stroke-width="2"/><path d="M7 25h50v28H7Z" fill="url(#glass)" stroke="#4791c5" stroke-width="2"/><rect x="19" y="29" width="31" height="21" rx="2" fill="#fff" stroke="#407fa6" stroke-width="2"/><path d="m21 47 9-10 7 6 5-6 6 10Z" fill="#4da466"/><circle cx="27" cy="35" r="3" fill="#efc65a"/>',
    "places/folder-music.svg": '<path d="M5 16h20l6 6h28v34H5Z" fill="#dca84f" stroke="#996d2f" stroke-width="2"/><path d="M7 25h50v28H7Z" fill="url(#glass)" stroke="#4791c5" stroke-width="2"/><path d="M32 31v16m0-14 15-3v14" fill="none" stroke="#28618f" stroke-width="4"/><ellipse cx="27" cy="48" rx="6" ry="4" fill="#28618f"/><ellipse cx="42" cy="45" rx="6" ry="4" fill="#28618f"/>',
    "places/folder-download.svg": '<path d="M5 16h20l6 6h28v34H5Z" fill="#dca84f" stroke="#996d2f" stroke-width="2"/><path d="M7 25h50v28H7Z" fill="url(#glass)" stroke="#4791c5" stroke-width="2"/><path d="M32 29v17m-9-8 9 10 9-10" stroke="#2b8c66" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 51h20" stroke="#24744e" stroke-width="3"/>',
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
        write_generated_icon(
            target, path,
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{DEFS}{art}</svg>\n',
        )
    logo = (ROOT / "assets/aero-penguin.svg").read_text(encoding="utf-8")
    for name in ("start-here", "xfce4-menu", "ricehub-aero"):
        (ICONS / "apps" / f"{name}.svg").write_text(logo, encoding="utf-8")


if __name__ == "__main__":
    frame_assets()
    button_assets()
    icon_assets()
    print("Generated original RiceBowl Aero assets")
