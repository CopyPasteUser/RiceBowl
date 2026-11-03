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


def _luna_chrome(destination: Path) -> None:
    """Original XP-inspired molded XFWM4 art; never embed Microsoft bitmaps."""
    frame = destination / "xfwm4"
    (frame / "themerc").write_text(
        "active_text_color=#ffffff\ninactive_text_color=#eff4ff\n"
        "button_offset=2\nbutton_spacing=1\nfull_width_title=true\n"
        "frame_border_top=0\nmaximized_offset=0\nshow_app_icon=true\n"
        "title_horizontal_offset=6\ntitle_vertical_offset_active=1\n"
        "title_vertical_offset_inactive=1\ntitle_shadow_active=true\n"
        "title_shadow_inactive=false\n",
        encoding="utf-8",
    )

    def gradient(width, height, upper, lower):
        image = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(image)
        for y in range(height):
            t = y / max(1, height - 1)
            color = tuple(round(a * (1-t) + b*t) for a, b in zip(upper, lower)) + (255,)
            draw.line((0, y, width, y), fill=color)
        return image

    for state, upper, lower in (
        ("active", (74, 143, 239), (15, 65, 165)),
        ("inactive", (144, 181, 228), (93, 129, 191)),
    ):
        for number in range(1, 6):
            image = gradient(15, 32, upper, lower)
            draw = ImageDraw.Draw(image)
            draw.line((0, 0, 15, 0), fill=(163, 208, 255, 255), width=1)
            draw.line((0, 2, 15, 2), fill=(109, 169, 245, 150), width=1)
            image.save(frame / f"title-{number}-{state}.png")
        for side in ("top-left", "top-right"):
            image = gradient(6, 32, upper, lower)
            draw = ImageDraw.Draw(image)
            x = 0 if side == "top-left" else 5
            draw.line((x, 4, x, 31), fill=(4, 43, 135, 255), width=1)
            # Three transparent pixels evoke Luna's softly rounded top corners.
            px = image.load()
            for dy, n in ((0, 3), (1, 2), (2, 1)):
                for dx in range(n):
                    px[dx if side == "top-left" else 5-dx, dy] = (0, 0, 0, 0)
            image.save(frame / f"{side}-{state}.png")
        for side in ("left", "right"):
            image = Image.new("RGBA", (4, 8), (39, 97, 192, 255) if state == "active" else
                              (103, 139, 190, 255))
            draw = ImageDraw.Draw(image)
            draw.line((0 if side == "left" else 3, 0, 0 if side == "left" else 3, 8),
                      fill=(23, 66, 154, 255), width=1)
            image.save(frame / f"{side}-{state}.png")
        for part in ("bottom", "bottom-left", "bottom-right"):
            image = gradient(6, 5, lower, (8, 49, 144) if state == "active" else (74, 113, 178))
            image.save(frame / f"{part}-{state}.png")

    for button in ("close", "maximize", "hide", "menu", "shade", "stick"):
        for state in ("active", "inactive", "prelight", "pressed"):
            image = Image.new("RGBA", (27, 27), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            if button == "close":
                upper, lower = ((252, 137, 100), (182, 40, 25))
                if state == "prelight": upper, lower = ((255, 178, 137), (223, 56, 40))
            else:
                upper, lower = ((113, 170, 246), (25, 87, 190))
                if state == "prelight": upper, lower = ((158, 207, 255), (43, 120, 221))
            if state == "inactive":
                upper, lower = ((192, 207, 232), (122, 149, 199))
            if state == "pressed":
                upper, lower = lower, upper
            draw.rounded_rectangle((3, 3, 25, 24), radius=5, fill=lower,
                                   outline=(245, 250, 255, 230), width=1)
            for y in range(5, 15):
                t = (y-5)/10
                color = tuple(round(a*(1-t)+b*t) for a,b in zip(upper,lower))+(255,)
                draw.line((5,y,23,y), fill=color)
            symbol = (255, 255, 255, 255)
            if button == "close":
                draw.line((10, 10, 18, 18), fill=symbol, width=2)
                draw.line((18, 10, 10, 18), fill=symbol, width=2)
            elif button == "maximize":
                draw.rectangle((10, 10, 19, 18), outline=symbol, width=2)
                draw.line((10, 10, 19, 10), fill=symbol, width=2)
            elif button == "hide":
                draw.line((9, 18, 19, 18), fill=symbol, width=2)
            elif button == "menu":
                draw.rectangle((10, 10, 18, 18), outline=symbol, width=1)
            elif button == "shade":
                draw.polygon([(10, 15), (19, 15), (14, 10)], fill=symbol)
            else:
                draw.ellipse((12, 11, 17, 17), fill=symbol)
            image.save(frame / f"{button}-{state}.png")


def _luna_gtk(destination: Path) -> None:
    """Layer tactile Luna Blue GTK3 widgets over the base theme, including Thunar."""
    target = destination / "gtk-3.0/gtk.css"
    base = target.read_text(encoding="utf-8")
    if "/* Original RiceBowl Luna GTK3/Thunar chrome." in base:
        return
    target.write_text(base + """
/* Original RiceBowl Luna GTK3/Thunar chrome. Keep Linux widget semantics. */
window, dialog, .background, viewport { background-color: #ece9d8; color: #151515; }
button { background-image: linear-gradient(#ffffff, #e4ecf9 65%, #c4d6ed);
  border: 1px solid #7f9db9; border-radius: 3px; box-shadow: inset 0 1px #fff;
  color: #171717; padding: 4px 9px; }
button:hover { background-image: linear-gradient(#fff, #f5f8e5 60%, #f4d58d);
  border-color: #d59e37; }
button:active, button:checked { background-image: linear-gradient(#b9d5f5, #dceafc);
  color: #15387d; border-color: #316ac5; }
entry, spinbutton, combobox box.linked { background: #fff; color: #111;
  border: 1px solid #7f9db9; border-radius: 1px; padding: 3px; }
entry:focus { border-color: #316ac5; }
selection, :selected, row:selected, treeview.view:selected { background: #316ac5; color: #fff; }
menubar, menu, popover, .menu, .popup { background: #fff; color: #111;
  border: 1px solid #a1a1a1; }
menuitem:hover, modelbutton:hover { background: #316ac5; color: #fff; }
headerbar, .titlebar { background-image: linear-gradient(#5798ed, #1453b6);
  color: #fff; border: 1px solid #2154a0; box-shadow: inset 0 1px #91c6ff; }
toolbar { background-image: linear-gradient(#ffffff, #f3f1e6);
  color: #222; border-bottom: 1px solid #c6c4b4; }
toolbar button { border-color: transparent; background: transparent; box-shadow: none; }
toolbar button:hover { background: #fff5d9; border-color: #e3ad54; }
notebook header { background: #ece9d8; border-color: #a7bce1; }
notebook tab { background-image: linear-gradient(#e9eef9, #d2e2f6);
  border: 1px solid #94afd6; border-radius: 4px 4px 0 0; padding: 4px 12px; }
notebook tab:checked { background: #fff; color: #1b3c71; border-bottom: 1px solid #fff; }
scrollbar slider { background-image: linear-gradient(#e9f3ff, #8cb6ed);
  border: 1px solid #608fc5; border-radius: 2px; min-width: 11px; min-height: 11px; }
scrollbar trough { background: #e3edfa; }
progressbar progress, scale highlight { background-image: linear-gradient(#a6df71, #4da735);
  border: 1px solid #478b25; border-radius: 1px; }
tooltip { background: #fffcd9; color: #141414; border: 1px solid #8f8b7d; }
/* Thunar's real navigation/sidebar remains functional; style visible widgets. */
thunar toolbar, .thunar toolbar { background-image: linear-gradient(#fff, #e9e9db); }
thunar treeview.view, .thunar treeview.view { background: #fff; color: #242424; }
thunar treeview.view:selected, .thunar treeview.view:selected { background: #316ac5; color: #fff; }
thunar paned separator, .thunar paned separator { background: #acbed8; }
""", encoding="utf-8")


def _frutiger_chrome(destination: Path) -> None:
    """Draw original pearl-and-lagoon XFWM artwork for Aqua World alone."""
    frame = destination / "xfwm4"
    (frame / "themerc").write_text(
        "active_text_color=#ffffff\ninactive_text_color=#e1fcfa\n"
        "button_offset=2\nbutton_spacing=2\nfull_width_title=true\n"
        "frame_border_top=0\nmaximized_offset=0\nshow_app_icon=true\n"
        "title_horizontal_offset=8\ntitle_vertical_offset_active=1\n"
        "title_vertical_offset_inactive=1\ntitle_shadow_active=true\n"
        "title_shadow_inactive=false\n", encoding="utf-8",
    )

    def gradient(width, height, upper, lower):
        canvas = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(canvas)
        for y in range(height):
            t = y / max(1, height - 1)
            col = tuple(round(a * (1 - t) + b * t) for a, b in zip(upper, lower))
            draw.line((0, y, width, y), fill=col + (255,))
        return canvas

    for state, top, bottom in (
        ("active", (118, 238, 230), (5, 114, 170)),
        ("inactive", (180, 235, 230), (77, 157, 176)),
    ):
        for number in range(1, 6):
            image = gradient(15, 32, top, bottom)
            draw = ImageDraw.Draw(image, "RGBA")
            draw.rectangle((0, 0, 14, 1), fill=(255, 255, 255, 230))
            draw.line((0, 13, 14, 13), fill=(240, 255, 255, 116))
            draw.line((0, 31, 14, 31), fill=(1, 83, 136, 225))
            image.save(frame / f"title-{number}-{state}.png")
        for side in ("top-left", "top-right"):
            image = gradient(8, 32, top, bottom)
            draw = ImageDraw.Draw(image, "RGBA")
            x = 0 if side == "top-left" else 7
            draw.line((x, 5, x, 31), fill=(12, 123, 153, 230))
            pixels = image.load()
            for y, cut in ((0, 4), (1, 3), (2, 2), (3, 1)):
                for d in range(cut):
                    pixels[d if side == "top-left" else 7-d, y] = (0, 0, 0, 0)
            image.save(frame / f"{side}-{state}.png")
        for side in ("left", "right"):
            image = gradient(5, 8, bottom, (7, 111, 145))
            draw = ImageDraw.Draw(image)
            x = 0 if side == "left" else 4
            draw.line((x, 0, x, 8), fill=(12, 92, 137, 255))
            image.save(frame / f"{side}-{state}.png")
        for part in ("bottom", "bottom-left", "bottom-right"):
            image = gradient(8, 6, bottom, (3, 91, 138))
            image.save(frame / f"{part}-{state}.png")

    for name in ("close", "maximize", "hide", "menu", "shade", "stick"):
        for state in ("active", "inactive", "prelight", "pressed"):
            if name == "close":
                top, bottom = (255, 169, 130), (208, 59, 56)
            elif name in ("shade", "stick"):
                top, bottom = (209, 255, 159), (61, 168, 96)
            else:
                top, bottom = (220, 255, 255), (28, 156, 200)
            if state == "inactive":
                top, bottom = (226, 245, 244), (120, 178, 192)
            elif state == "prelight":
                top = tuple(min(255, component + 26) for component in top)
            elif state == "pressed":
                top, bottom = bottom, top
            image = Image.new("RGBA", (27, 27), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image, "RGBA")
            draw.rounded_rectangle((2, 2, 25, 24), radius=10,
                                   fill=bottom + (255,), outline=(235, 255, 255, 255), width=1)
            for y in range(4, 15):
                t = (y - 4) / 11
                col = tuple(round(a * (1 - t) + b * t) for a, b in zip(top, bottom))
                draw.line((5, y, 22, y), fill=col + (255,))
            draw.arc((5, 3, 22, 18), 190, 350, fill=(255, 255, 255, 210), width=2)
            stroke = (255, 255, 255, 255)
            if name == "close":
                draw.line((10, 10, 18, 18), fill=stroke, width=2)
                draw.line((18, 10, 10, 18), fill=stroke, width=2)
            elif name == "maximize":
                draw.rectangle((9, 10, 18, 18), outline=stroke, width=2)
            elif name == "hide":
                draw.line((8, 18, 19, 18), fill=stroke, width=2)
            elif name == "menu":
                draw.ellipse((10, 10, 18, 18), outline=stroke, width=2)
            elif name == "shade":
                draw.polygon(((9, 16), (19, 16), (14, 10)), fill=stroke)
            else:
                draw.ellipse((11, 11, 17, 17), fill=stroke)
            image.save(frame / f"{name}-{state}.png")


def _frutiger_gtk(destination: Path) -> None:
    """Add scoped eco-glass GTK widgets without regenerating other rice themes."""
    target = destination / "gtk-3.0/gtk.css"
    css = target.read_text(encoding="utf-8")
    marker = "/* RiceBowl Aqua World 0.9: light-refracting Frutiger widgets. */"
    if marker in css:
        css = css[:css.index(marker)].rstrip() + "\n"
    target.write_text(css + """
/* RiceBowl Aqua World 0.9: light-refracting Frutiger widgets. */
window, dialog, .background, viewport { background-color: #e7fff8; color: #07506a; }
button { background-image: linear-gradient(#fff, #ecfff9 38%, #bcf2ed 51%, #84d6df);
  border: 1px solid #77c8d0; border-radius: 11px; color: #07506a;
  padding: 7px 11px; box-shadow: inset 0 1px #fff; }
button:hover { background-image: linear-gradient(#fff, #dfffed 40%, #a0efd6 55%, #57ccce);
  border-color: #2ca6bf; }
button:active, button:checked { background-image: linear-gradient(#efffd4, #b4ee68 50%, #72c943);
  border-color: #4baa5d; color: #124d62; }
button:focus { border-color: #127ba8; box-shadow: 0 0 3px #3bc3db; }
button:disabled { color: #4e8491; opacity: .66; }
entry, spinbutton, combobox box.linked { background: #faffff; color: #07506a;
  border: 1px solid #77c6d7; border-radius: 11px; padding: 7px 10px; }
entry:focus { border-color: #1588b4; box-shadow: 0 0 3px #70e5ed; }
selection, :selected, row:selected, treeview.view:selected { background: #9ce54b;
  color: #164e64; }
headerbar, .titlebar { background-image: linear-gradient(#e2ffff 0%, #9bf0e4 42%,
  #45b8cc 48%, #168baa 100%); color: #064b67; border-bottom: 2px solid #0e88a5;
  box-shadow: inset 0 1px #fff; }
headerbar button { border-radius: 12px; }
toolbar { background-image: linear-gradient(#f8ffff, #c3fff2 48%, #81d8e3);
  color: #07536d; border-bottom: 1px solid #75cbd7; }
menubar, menu, popover, .menu, .popup { background: #e6fff7; color: #07546b;
  border: 1px solid #7acecd; border-radius: 7px; }
menuitem:hover, modelbutton:hover { background: #b9f3ab; color: #14566a; }
notebook header { background: #dcfff3; border-color: #83d6db; }
notebook tab { background-image: linear-gradient(#f7ffff, #bdeee9); border: 1px solid #8dd5d8;
  border-radius: 12px 12px 0 0; padding: 7px 12px; }
notebook tab:checked { background: #fbffed; border-bottom: 2px solid #96df43; }
scrollbar trough { background: #c5f4ed; border-radius: 10px; }
scrollbar slider { background-image: linear-gradient(#f8ffff, #7ad9d9);
  border: 1px solid #5bb9c3; border-radius: 10px; min-width: 11px; min-height: 11px; }
scrollbar slider:hover { background: #7ae6ce; }
progressbar progress, scale highlight, switch:checked {
  background-image: linear-gradient(#e9ff9e, #81d947);
  border: 1px solid #5eae49; border-radius: 9px; }
tooltip { background: #fafff0; color: #0b566a; border: 1px solid #8fd4c4;
  border-radius: 6px; }
window.thunar menubar, window.thunar toolbar { background-image: linear-gradient(#fff,
  #d2fff1 38%, #8fe1e6); border-bottom: 2px solid #6bcbd5; }
window.thunar toolbar button { border-radius: 11px; box-shadow: inset 0 1px #fff; }
window.thunar .path-bar button, window.thunar .location-bar button {
  background-image: linear-gradient(#fff, #c6fff3 40%, #8cdee0);
  border: 1px solid #7bd2d2; border-radius: 15px; }
window.thunar .sidebar, window.thunar .shortcuts-pane {
  background-image: linear-gradient(to right, #e7fff3, #afe9e6);
  border-right: 2px solid #84d3d2; }
window.thunar .sidebar .view:selected, window.thunar treeview.view:selected {
  background: #a1ed43; color: #174960; }
window.thunar statusbar { background-image: linear-gradient(#effff5, #a5ecdf);
  color: #075f7d; border-top: 1px solid #83cfd0; }
""", encoding="utf-8")


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


def main(*, luna_only: bool = False, frutiger_only: bool = False):
    if luna_only and frutiger_only:
        raise ValueError("Choose only one targeted art build")
    if frutiger_only:
        # Preserve every other rice and the already reviewed Frutiger wallpaper,
        # icons and project-specific Thunar rules. Only redraw owned chrome.
        path = ROOT / "assets/themes/RiceHub-Frutiger"
        _frutiger_chrome(path)
        _frutiger_gtk(path)
        print("Refreshed original Frutiger window chrome and GTK styles only")
        return
    for name, palette in PALETTES.items():
        if luna_only and name != "Luna":
            continue
        path = ROOT / "assets/themes" / ("RiceHub-" + name)
        if name == "Luna":
            # Preserve hand-reviewed GTK/Thunar rules present in shipped builds.
            if not (path / "gtk-3.0/gtk.css").exists():
                gtk(path, palette)
            _luna_chrome(path)
            _luna_gtk(path)
        else:
            chrome(path, palette)
            gtk(path, palette)
        if not luna_only:
            _icons(name, palette)
    if luna_only:
        print("Refreshed original Luna window chrome and GTK styles only")
        return
    _luna()
    _classic()
    _chrome()
    _frutiger()
    print("Generated four original XFCE window/GTK/icon themes and desktop wallpapers")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--luna-only", action="store_true",
                        help="Refresh just Luna XFWM and GTK, preserving reviewed other rices")
    parser.add_argument("--frutiger-only", action="store_true",
                        help="Refresh only the reviewed Frutiger XFWM and GTK glass styles")
    arguments = parser.parse_args()
    main(luna_only=arguments.luna_only, frutiger_only=arguments.frutiger_only)
