#!/usr/bin/env python3
"""Regenerate original Windows 10-inspired assets (Pillow needed only for development)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
COLORS = {
    "Dark": {"background": "#202020", "surface": "#2d2d30", "field": "#181818",
             "ink": "#f5f5f5", "muted": "#aeb2ba", "edge": "#484848", "accent": "#0078d7",
             "inactive": (58, 58, 61), "active": (34, 34, 36)},
    "Light": {"background": "#f5f5f5", "surface": "#ffffff", "field": "#ffffff",
              "ink": "#202020", "muted": "#565e65", "edge": "#cacdd1", "accent": "#0078d7",
              "inactive": (235, 235, 235), "active": (255, 255, 255)},
}


def chrome(destination: Path, palette: dict) -> None:
    folder = destination / "xfwm4"
    folder.mkdir(parents=True, exist_ok=True)
    (destination / "index.theme").write_text(
        f"[Desktop Entry]\nType=X-GNOME-Metatheme\nName={destination.name}\nComment=Original RiceHub flat window theme\n",
        encoding="utf-8",
    )
    (folder / "themerc").write_text(
        "active_text_color=" + palette["ink"] + "\n"
        + "inactive_text_color=" + palette["muted"] + "\n"
        + "button_offset=0\nbutton_spacing=0\nfull_width_title=true\n"
        + "frame_border_top=0\nmaximized_offset=0\nshow_app_icon=false\n"
        + "title_horizontal_offset=12\ntitle_vertical_offset_active=1\n"
        + "title_vertical_offset_inactive=1\ntitle_shadow_active=false\n"
        + "title_shadow_inactive=false\n",
        encoding="utf-8",
    )
    for state in ("active", "inactive"):
        color = palette[state] + (255,)
        for n in range(1, 6):
            Image.new("RGBA", (15, 32), color).save(folder / f"title-{n}-{state}.png")
        for part in ("top-left", "top-right"):
            Image.new("RGBA", (5, 32), color).save(folder / f"{part}-{state}.png")
        for part in ("left", "right"):
            Image.new("RGBA", (3, 8), color).save(folder / f"{part}-{state}.png")
        for part in ("bottom", "bottom-left", "bottom-right"):
            Image.new("RGBA", (5, 4), color).save(folder / f"{part}-{state}.png")
    for button in ("close", "maximize", "hide", "menu", "shade", "stick"):
        for state in ("active", "inactive", "prelight", "pressed"):
            bg = palette["active"] if state != "inactive" else palette["inactive"]
            if state in ("prelight", "pressed"):
                bg = (232, 17, 35) if button == "close" else (76, 76, 79)
            image = Image.new("RGBA", (46, 31), bg + (255,))
            draw = ImageDraw.Draw(image)
            ink = (255, 255, 255, 255) if state in ("prelight", "pressed") or palette["ink"] == "#f5f5f5" else (35, 35, 35, 255)
            if button == "close":
                draw.line((20, 12, 26, 18), ink, 1)
                draw.line((26, 12, 20, 18), ink, 1)
            elif button == "maximize":
                draw.rectangle((19, 11, 27, 19), outline=ink, width=1)
            elif button == "hide":
                draw.line((19, 19, 27, 19), ink, 1)
            elif button == "menu":
                draw.rectangle((20, 11, 26, 18), outline=ink)
            elif button == "shade":
                draw.polygon([(19, 17), (27, 17), (23, 12)], fill=ink)
            else:
                draw.ellipse((21, 12, 25, 16), fill=ink)
            image.save(folder / f"{button}-{state}.png")


def gtk(destination: Path, palette: dict) -> None:
    folder = destination / "gtk-3.0"
    folder.mkdir(parents=True, exist_ok=True)
    content = """/* RiceHub Ten: compact flat GTK3 theme, original artwork. */
@define-color theme_bg_color BG;
@define-color theme_fg_color INK;
@define-color theme_base_color FIELD;
@define-color theme_text_color INK;
@define-color theme_selected_bg_color ACCENT;
@define-color theme_selected_fg_color #ffffff;
@define-color insensitive_fg_color MUTED;
@define-color borders EDGE;
window, dialog, .background, viewport { color: INK; background-color: BG; }
entry, textview text, treeview.view, .view, spinbutton { color: INK; background-color: FIELD; }
entry, spinbutton, combobox box.linked { border: 1px solid EDGE; border-radius: 0; padding: 5px; }
entry:focus { border: 1px solid ACCENT; }
selection, :selected, row:selected { background: ACCENT; color: #ffffff; }
button { border: 1px solid EDGE; border-radius: 0; padding: 5px 12px; background-image: none; background-color: SURFACE; color: INK; box-shadow: none; }
button:hover { background-color: HOVER; border-color: ACCENT; }
button:active, button:checked { background-color: ACCENT; color: #ffffff; }
button:disabled { color: MUTED; opacity: .62; }
headerbar, .titlebar, toolbar { background-image: none; background-color: SURFACE; color: INK; border-bottom: 1px solid EDGE; box-shadow: none; }
headerbar button { border: 0; padding: 4px 8px; }
menubar, menu, popover, .menu, .popup { background: SURFACE; color: INK; border: 1px solid EDGE; }
menuitem:hover, modelbutton:hover { background: ACCENT; color: #ffffff; }
notebook header { background: BG; border-bottom: 1px solid EDGE; }
notebook tab { padding: 7px 12px; border-radius: 0; }
notebook tab:checked { background: SURFACE; border-bottom: 2px solid ACCENT; }
scrollbar slider { background: EDGE; border-radius: 0; min-height: 7px; min-width: 7px; }
scrollbar slider:hover { background: MUTED; }
progressbar progress, scale highlight, switch:checked { background: ACCENT; border-radius: 0; }
tooltip { background: SURFACE; color: INK; border: 1px solid EDGE; }
"""
    replaces = {"BG": palette["background"], "INK": palette["ink"], "FIELD": palette["field"],
                "SURFACE": palette["surface"], "MUTED": palette["muted"], "EDGE": palette["edge"],
                "ACCENT": palette["accent"], "HOVER": "#3d3d40" if destination.name.endswith("Dark") else "#e5f1fb"}
    import re
    content = re.sub(r"\b(?:BG|INK|FIELD|SURFACE|MUTED|EDGE|ACCENT|HOVER)\b",
                     lambda match: replaces[match.group()], content)
    (folder / "gtk.css").write_text(content, encoding="utf-8")


ART = {
    "places/folder.svg": '<path d="M5 19h20l6 6h28v28H5Z" fill="#e7b74a"/><path d="M5 27h54v26H5Z" fill="#f4cc5f"/>',
    "places/user-home.svg": '<path d="M7 30 32 9l25 21v25H7Z" fill="#178fca"/><path d="M25 37h15v18H25Z" fill="#eaf8ff"/>',
    "places/computer.svg": '<rect x="5" y="8" width="54" height="39" rx="2" fill="#267bc3"/><rect x="9" y="12" width="46" height="31" fill="#d7eefc"/><path d="M32 47v8m-15 1h30" stroke="#336a8c" stroke-width="4"/>',
    "places/user-trash.svg": '<path d="M18 21h29l-4 35H22Z" fill="#9dd7e6"/><path d="M15 19h34m-23-5h12" stroke="#357f9b" stroke-width="4"/>',
    "apps/system-file-manager.svg": '<path d="M5 19h20l6 6h28v28H5Z" fill="#e7b74a"/><path d="M5 27h54v26H5Z" fill="#f4cc5f"/>',
    "apps/web-browser.svg": '<circle cx="32" cy="32" r="26" fill="#0078d7"/><path d="M8 32h48M32 6c-13 15-13 37 0 52M32 6c13 15 13 37 0 52" stroke="white" stroke-width="2" fill="none"/>',
    "apps/utilities-terminal.svg": '<rect x="6" y="12" width="52" height="40" fill="#202020"/><path d="m16 23 10 9-10 9m17 0h15" stroke="white" stroke-width="4" fill="none"/>',
    "apps/preferences-system.svg": '<circle cx="32" cy="32" r="24" fill="#0078d7"/><circle cx="32" cy="32" r="14" stroke="white" stroke-width="7" fill="none"/><circle cx="32" cy="32" r="5" fill="white"/>',
    "apps/accessories-calculator.svg": '<rect x="12" y="6" width="40" height="52" fill="#0078d7"/><path d="M19 19h26M19 30h6m8 0h6m-20 9h6m8 0h6m-20 9h6m8 0h6" stroke="white" stroke-width="5"/>',
    "apps/accessories-text-editor.svg": '<rect x="12" y="6" width="42" height="52" fill="#f0f5f9" stroke="#0078d7" stroke-width="3"/><path d="M20 19h25m-25 9h25m-25 9h20m-20 9h25" stroke="#3995d9" stroke-width="3"/>',
    "apps/applications-other.svg": '<rect x="6" y="6" width="24" height="24" fill="#0078d7"/><rect x="34" y="6" width="24" height="24" fill="#0078d7"/><rect x="6" y="34" width="24" height="24" fill="#0078d7"/><rect x="34" y="34" width="24" height="24" fill="#0078d7"/>',
}


def icons() -> None:
    root = ROOT / "assets/icons/RiceHub-Ten"
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.theme").write_text(
        "[Icon Theme]\nName=RiceHub Ten\nComment=Original flat icons, inherited system app coverage\n"
        "Inherits=Adwaita,hicolor\nDirectories=scalable/apps,scalable/places\n"
        "[scalable/apps]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=128\n"
        "[scalable/places]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=128\n",
        encoding="utf-8",
    )
    for path, artwork in ART.items():
        target = root / "scalable" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">' + artwork + '</svg>\n', encoding="utf-8")
    logo = (ROOT / "assets/ten-start.svg").read_text(encoding="utf-8")
    for name in ("start-here", "xfce4-menu", "ricehub-ten"):
        (root / "scalable/apps" / (name + ".svg")).write_text(logo, encoding="utf-8")


def wallpapers() -> None:
    root = ROOT / "assets/wallpapers"
    width, height = 1920, 1080
    for name, base, glow in (("ten-blue.jpg", (5, 36, 90), (0, 122, 215)),
                             ("ten-midnight.jpg", (10, 17, 40), (13, 89, 169))):
        image = Image.new("RGB", (width, height), base)
        pix = image.load()
        for y in range(height):
            for x in range(width):
                factor = max(0, 1 - abs(x - 1280) / 1020) * max(0, 1 - abs(y - 520) / 880)
                pix[x, y] = tuple(min(255, int(base[i] + (glow[i] - base[i]) * factor)) for i in range(3))
        draw = ImageDraw.Draw(image, "RGBA")
        # Four original luminous panes, with a slight perspective taper and light rays.
        draw.polygon([(1020, 260), (1290, 220), (1290, 508), (1020, 508)], fill=(59, 169, 246, 215))
        draw.polygon([(1310, 218), (1660, 165), (1660, 505), (1310, 505)], fill=(86, 189, 253, 225))
        draw.polygon([(1020, 528), (1290, 528), (1290, 820), (1020, 770)], fill=(39, 154, 235, 220))
        draw.polygon([(1310, 528), (1660, 528), (1660, 875), (1310, 825)], fill=(75, 180, 251, 235))
        draw.polygon([(1020, 260), (1020, 770), (100, 950), (240, 120)], fill=(12, 99, 187, 48))
        image.save(root / name, "JPEG", quality=91, optimize=True)


if __name__ == "__main__":
    for variant, colors in COLORS.items():
        dest = ROOT / "assets/themes" / ("RiceHub-Ten-" + variant)
        chrome(dest, colors)
        gtk(dest, colors)
    icons()
    wallpapers()
    print("Regenerated RiceHub Ten dark/light themes, icons and wallpapers")
