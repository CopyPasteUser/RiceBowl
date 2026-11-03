#!/usr/bin/env python3
"""Reproducible original ChromeOS/Material You artwork for XFCE/X11.

Development-only Pillow dependency. No Google artwork or external assets.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
FRAME = ROOT / "assets/themes/RiceHub-Chrome/xfwm4"


def wallpaper() -> None:
    width, height = 1920, 1080
    canvas = Image.new("RGB", (width, height))
    pixels = canvas.load()
    for y in range(height):
        for x in range(width):
            top = y / (height - 1)
            horizontal = x / (width - 1)
            pixels[x, y] = (
                int(219 + 9 * horizontal + 11 * top),
                int(225 + 6 * horizontal - 5 * top),
                int(246 - 4 * horizontal - 3 * top),
            )
    shapes = Image.new("RGBA", canvas.size)
    d = ImageDraw.Draw(shapes, "RGBA")
    # Abstract layered valleys and scrolls, not the licensed ChromeOS art.
    d.ellipse((-560, -680, 940, 840), fill=(173, 192, 252, 218))
    d.ellipse((890, -480, 2570, 1100), fill=(252, 208, 213, 185))
    d.ellipse((-470, 480, 1690, 2220), fill=(171, 181, 242, 220))
    d.ellipse((620, 620, 2320, 1790), fill=(239, 212, 242, 160))
    shapes = shapes.filter(ImageFilter.GaussianBlur(85))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shapes)
    ribbons = Image.new("RGBA", canvas.size)
    d = ImageDraw.Draw(ribbons, "RGBA")
    # Subtle, broad contour loops make the wallpaper recognizable at a glance.
    for expansion, color, thickness in (
        (0, (246, 247, 255, 145), 95),
        (102, (191, 198, 250, 95), 48),
        (170, (252, 244, 253, 103), 25),
    ):
        d.arc((-260-expansion, -650-expansion, 1630+expansion,
               1250+expansion), 24, 298, fill=color, width=thickness)
    d.arc((790, -320, 2630, 1680), 107, 251,
          fill=(255, 247, 252, 128), width=104)
    ribbons = ribbons.filter(ImageFilter.GaussianBlur(24))
    canvas = Image.alpha_composite(canvas, ribbons)
    output = ROOT / "assets/wallpapers/chrome-pastel.jpg"
    canvas.convert("RGB").save(output, "JPEG", quality=91, subsampling=0,
                                optimize=True)


def window_chrome() -> None:
    FRAME.mkdir(parents=True, exist_ok=True)
    (FRAME / "themerc").write_text(
        "active_text_color=#26334e\ninactive_text_color=#778098\n"
        "button_offset=5\nbutton_spacing=2\nfull_width_title=true\n"
        "frame_border_top=0\nmaximized_offset=0\nshow_app_icon=true\n"
        "title_horizontal_offset=10\ntitle_vertical_offset_active=1\n"
        "title_vertical_offset_inactive=1\ntitle_shadow_active=false\n"
        "title_shadow_inactive=false\n", encoding="utf-8")

    for state, top, bottom in (
        ("active", (250, 250, 255), (229, 234, 250)),
        ("inactive", (246, 246, 250), (230, 233, 243)),
    ):
        for count in range(1, 6):
            tile = Image.new("RGBA", (18, 35), top + (255,))
            d = ImageDraw.Draw(tile)
            for y in range(35):
                f = y / 34
                shade = tuple(round(a * (1-f) + b * f)
                              for a, b in zip(top, bottom))
                d.line((0, y, 17, y), fill=shade + (255,))
            d.line((0, 34, 17, 34), fill=(188, 198, 226, 255))
            tile.save(FRAME / f"title-{count}-{state}.png")
        for side in ("top-left", "top-right"):
            tile = Image.new("RGBA", (9, 35), top + (255,))
            d = ImageDraw.Draw(tile)
            d.line((0 if side == "top-left" else 8, 8,
                    0 if side == "top-left" else 8, 34),
                   fill=(203, 211, 232, 255))
            px = tile.load()
            for y, cut in ((0, 5), (1, 3), (2, 2), (3, 1)):
                for offset in range(cut):
                    px[offset if side == "top-left" else 8-offset, y] = (0, 0, 0, 0)
            tile.save(FRAME / f"{side}-{state}.png")
        for side in ("left", "right"):
            tile = Image.new("RGBA", (4, 8), bottom + (255,))
            ImageDraw.Draw(tile).line(
                (0 if side == "left" else 3, 0,
                 0 if side == "left" else 3, 7),
                fill=(190, 199, 224, 255))
            tile.save(FRAME / f"{side}-{state}.png")
        for part in ("bottom", "bottom-left", "bottom-right"):
            tile = Image.new("RGBA", (9, 4), bottom + (255,))
            ImageDraw.Draw(tile).line((0, 3, 8, 3),
                                     fill=(192, 202, 229, 255))
            tile.save(FRAME / f"{part}-{state}.png")

    for button in ("close", "maximize", "hide", "menu", "shade", "stick"):
        for state in ("active", "inactive", "prelight", "pressed"):
            tile = Image.new("RGBA", (30, 28), (0, 0, 0, 0))
            d = ImageDraw.Draw(tile, "RGBA")
            background = {
                "active": (225, 230, 246, 0),
                "inactive": (225, 229, 239, 0),
                "prelight": (212, 222, 252, 255),
                "pressed": (189, 206, 249, 255),
            }[state]
            if button == "close" and state in ("prelight", "pressed"):
                background = (255, 209, 215, 255)
            d.rounded_rectangle((2, 2, 27, 25), radius=10,
                                fill=background)
            ink = (83, 91, 119, 255) if state == "inactive" else (58, 72, 110, 255)
            if button == "close":
                d.line((11, 9, 19, 17), fill=ink, width=2)
                d.line((19, 9, 11, 17), fill=ink, width=2)
            elif button == "maximize":
                d.rounded_rectangle((10, 9, 20, 18), radius=1,
                                    outline=ink, width=2)
            elif button == "hide":
                d.line((10, 18, 20, 18), fill=ink, width=2)
            elif button == "shade":
                d.polygon(((10, 16), (20, 16), (15, 10)), fill=ink)
            elif button == "stick":
                d.ellipse((12, 10, 18, 16), fill=ink)
            else:
                d.rectangle((11, 10, 19, 18), outline=ink)
            tile.save(FRAME / f"{button}-{state}.png")


def gtk_theme() -> None:
    stylesheet = ROOT / "assets/themes/RiceHub-Chrome/gtk-3.0/gtk.css"
    stylesheet.parent.mkdir(parents=True, exist_ok=True)
    stylesheet.write_text("""/* Original RiceBowl ChromeOS Material You GTK3/Thunar */
@define-color iris #506cd6;
@define-color primary_text #262b43;
@define-color soft_surface #f9faff;
@define-color outline #d6daeb;
window, dialog, .background, viewport { background-color: #f9faff; color: #262b43; }
headerbar, .titlebar { background: #eff1fc; color: #262b43;
  border: 0; border-bottom: 1px solid #d9dff0; box-shadow: none; }
button { background: #e8ecfa; color: #303a59; border: 1px solid #d9dff0;
  border-radius: 13px; padding: 6px 12px; box-shadow: none; }
button:hover { background: #dce5ff; border-color: #b3c1f2; }
button:active, button:checked { background: #c5d4fd; color: #243c8d; }
button:disabled { background: #f1f2f7; color: #9399ab; }
entry, searchentry, spinbutton { background: #eef0f9; color: #252b42;
  border: 1px solid #d8ddec; border-radius: 16px; padding: 7px 12px; }
entry:focus, searchentry:focus { background: #fff; border-color: #506cd6; }
selection, :selected, row:selected, treeview.view:selected {
  background: #c8d4ff; color: #202e67; }
menubar, menu, popover, .menu, .popup { background: #fdfdff;
  color: #252b43; border: 1px solid #dfe3f0; border-radius: 12px; }
menuitem:hover, modelbutton:hover { background: #e1e8ff; color: #283e8d; }
toolbar { background: #f0f3fc; color: #2b3453;
  border-bottom: 1px solid #dce1ef; }
toolbar button { background: transparent; border-color: transparent; }
toolbar button:hover { background: #dae3ff; }
notebook header { background: #eef1fa; border: 0; }
notebook tab { background: #e7ebf8; border: 1px solid #dce2f0;
  border-radius: 13px 13px 0 0; padding: 7px 13px; }
notebook tab:checked { background: #fff; color: #354caa; }
scrollbar trough { background: #edf0fa; }
scrollbar slider { background: #c5cee7; border-radius: 8px;
  min-width: 8px; min-height: 8px; }
scrollbar slider:hover { background: #9facd1; }
scale highlight, progressbar progress { background: #506cd6; border-radius: 7px; }
tooltip { background: #f1f3fd; color: #252b43;
  border: 1px solid #cdd5e9; border-radius: 8px; }
thunar treeview.view, .thunar treeview.view { background: #fff; color: #29334b; }
window.thunar menubar { background: #f0f3fc; color: #2b3453; }
window.thunar .sidebar { background: #eef2fc; color: #303955; }
window.thunar .sidebar row:selected { background: #c8d4ff; color: #202e67; }
window.thunar toolbar { background: #f0f3fc; border-bottom: 1px solid #dce1ef; }
window.thunar statusbar { background: #f2f4fb; color: #4d5974;
  border-top: 1px solid #dce1ef; }
thunar treeview.view:selected, .thunar treeview.view:selected {
  background: #c8d4ff; color: #202e67; }
thunar paned separator, .thunar paned separator { background: #d8dff0; }
button:focus { outline: 2px solid #506cd6; outline-offset: -2px; }
""", encoding="utf-8")


def main():
    wallpaper()
    window_chrome()
    gtk_theme()
    print("Refreshed original ChromeOS wallpaper, XFWM chrome and GTK theme")


if __name__ == "__main__":
    main()
