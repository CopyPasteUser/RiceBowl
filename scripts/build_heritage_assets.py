#!/usr/bin/env python3
"""Build original, reproducible GTK/XFWM, icon and wallpaper artwork.

Development-only dependency: Pillow. No downloaded OS textures or logos.
The generated assets are checked into the source distribution.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from build_ten_assets import ART, chrome, gtk
from ricebowl_artwork import write_generated_icon


ROOT = Path(__file__).resolve().parents[1]
W, H = 1920, 1080

PALETTES = {
    "Luna": {"background": "#e9f2ff", "surface": "#d1e6fd", "field": "#ffffff",
             "ink": "#123c79", "muted": "#5075a3", "edge": "#85a8da", "accent": "#2265cf",
             "inactive": (125, 161, 205), "active": (32, 94, 203)},
    "Classic": {"background": "#c0c0c0", "surface": "#c0c0c0", "field": "#ffffff",
                "ink": "#101010", "muted": "#4c4c4c", "edge": "#777777", "accent": "#000080",
                "inactive": (128, 128, 128), "active": (0, 0, 128)},
    "Chrome": {"background": "#f5f8fe", "surface": "#e9effb", "field": "#ffffff",
               "ink": "#293b57", "muted": "#5e759a", "edge": "#bfcfe4", "accent": "#4a7ed4",
               "inactive": (197, 209, 230), "active": (225, 236, 249)},
    "Frutiger": {"background": "#e5fff8", "surface": "#c0f3ee", "field": "#f9fffe",
                 "ink": "#0b4a68", "muted": "#32859b", "edge": "#7ec8cf", "accent": "#16aabf",
                 "inactive": (82, 179, 200), "active": (32, 161, 193)},
}


def _vertical(upper, lower):
    image = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(image)
    for y in range(H):
        t = y / (H - 1)
        draw.line((0, y, W, y), fill=tuple(int(a * (1 - t) + b * t) for a, b in zip(upper, lower)))
    return image


def _save(image, name):
    destination = ROOT / "assets/wallpapers" / name
    # Each release ships hand-reviewed wallpaper artwork. Rebuilding the GTK
    # icons must never silently replace the selected full-resolution images.
    if not destination.exists():
        image.save(destination, "JPEG", quality=90, optimize=True)


def _luna():
    image = _vertical((37, 119, 219), (197, 227, 252))
    draw = ImageDraw.Draw(image)
    draw.ellipse((1335, 140, 1515, 320), fill=(240, 248, 220))
    for x, y, radius in ((240, 180, 90), (370, 195, 115), (480, 165, 80),
                         (1050, 265, 85), (1195, 290, 110)):
        draw.ellipse((x-radius, y-radius//2, x+radius, y+radius//2), fill=(246, 251, 255))
    draw.ellipse((-450, 360, 1550, 1880), fill=(73, 157, 56))
    draw.ellipse((670, 435, 2340, 1980), fill=(83, 183, 53))
    draw.ellipse((-300, 580, 1290, 2020), fill=(58, 151, 43))
    draw.arc((20, 385, 1940, 1795), start=206, end=332, fill=(155, 216, 99), width=17)
    for x in range(20, 1850, 135):
        y = int(835 + 64 * math.sin(x / 210))
        draw.line((x, y, x+7, y-32), fill=(144, 213, 94), width=3)
    _save(image, "luna-hills.jpg")


def _classic():
    image = Image.new("RGB", (W, H), (0, 122, 121))
    draw = ImageDraw.Draw(image, "RGBA")
    for n in range(0, 1650, 21):
        draw.line((n, 0, n + 580, H), fill=(160, 220, 207, 9), width=2)
    draw.polygon([(W-550, 0), (W, 0), (W, H), (W-130, H)], fill=(31, 155, 150, 43))
    draw.rounded_rectangle((W-500, 160, W-150, 490), radius=5,
                           outline=(202, 249, 237, 30), width=9)
    _save(image, "classic-teal.jpg")


def _chrome():
    image = _vertical((230, 239, 253), (247, 231, 237))
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.ellipse((-480, -620, 1260, 1030), fill=(138, 179, 246, 148))
    draw.ellipse((680, -300, 2440, 1450), fill=(244, 180, 210, 125))
    draw.ellipse((400, 330, 1450, 1410), fill=(218, 235, 255, 170))
    overlay = overlay.filter(ImageFilter.GaussianBlur(90))
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
    _save(image, "chrome-pastel.jpg")


def _frutiger():
    image = _vertical((45, 170, 219), (197, 254, 232))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.ellipse((-540, 365, 1260, 1920), fill=(37, 166, 111, 255))
    draw.ellipse((720, 445, 2460, 1770), fill=(70, 201, 142, 255))
    draw.ellipse((-200, 560, 2010, 2100), fill=(98, 221, 141, 220))
    for x, y, r in ((310, 200, 140), (1410, 320, 228), (1040, 170, 66), (1730, 160, 84)):
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(222, 255, 255, 77),
                     outline=(242, 255, 255, 180), width=7)
        draw.ellipse((x-r//2, y-r//2, x+r//4, y+r//6), fill=(255, 255, 255, 55))
    for x in range(90, 1840, 190):
        y = int(785 + 40 * math.sin(x / 160))
        draw.arc((x, y-150, x+200, y+130), 180, 295, fill=(225, 255, 239, 100), width=8)
    _save(image.convert("RGB"), "frutiger-future.jpg")


def _icons(name, palette):
    base = ROOT / "assets/icons" / ("RiceHub-" + name + "-Icons")
    base.mkdir(parents=True, exist_ok=True)
    (base / "index.theme").write_text(
        "[Icon Theme]\nName=RiceBowl " + name + " Icons\n"
        "Comment=Original RiceBowl themed icons; inherited Linux fallbacks\n"
        "Inherits=Adwaita,hicolor\nDirectories=scalable/apps,scalable/places\n"
        "[scalable/apps]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=128\n"
        "[scalable/places]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=128\n",
        encoding="utf-8",
    )
    for relative, artwork in ART.items():
        target = base / "scalable" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        artwork = artwork.replace("#0078d7", palette["accent"]).replace("#267bc3", palette["accent"])
        write_generated_icon(
            target, relative,
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            + artwork + '</svg>\n',
            heritage=True,
        )
    # Each historical desktop carries its own design-reviewed Start symbol.
    icon_names = {
        "Luna": "ricebowl-xp-start.svg",
        "Classic": "ricebowl-classic-start.svg",
        "Chrome": "ricebowl-chrome-start.svg",
        "Frutiger": "ricebowl-frutiger-start.svg",
    }
    logo = (ROOT / "assets" / icon_names[name]).read_text(encoding="utf-8")
    for filename in ("start-here", "xfce4-menu", "ricehub-start", "ricebowl-start"):
        (base / "scalable/apps" / f"{filename}.svg").write_text(logo, encoding="utf-8")


def main():
    for name, palette in PALETTES.items():
        path = ROOT / "assets/themes" / ("RiceHub-" + name)
        chrome(path, palette)
        gtk(path, palette)
        _icons(name, palette)
    _luna()
    _classic()
    _chrome()
    _frutiger()
    print("Generated four original XFCE window/GTK/icon themes and desktop wallpapers")


if __name__ == "__main__":
    main()
