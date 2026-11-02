#!/usr/bin/env python3
"""Render honest illustrative MacRice desktop compositions (not live captures).

The GUI itself is native GTK. These static release images document theme color
relationships when a real XFCE test session is not available in CI.
Requires ffmpeg only when generating documentation screenshots.
"""

from __future__ import annotations

import base64
import html
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def rect(x, y, w, h, color, r=0, **extra):
    props = " ".join(f'{name.replace("_", "-")}="{value}"' for name, value in extra.items())
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" {props}/>'


def text(x, y, label, color="#f0f4fa", size=13, weight=400):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" font-family="DejaVu Sans, sans-serif">'
            f'{html.escape(label)}</text>')


def render(style):
    night = style == "night"
    wallpaper = ROOT / "assets/wallpapers" / ("aurora-night.jpg" if night else "aurora-day.jpg")
    photo = base64.b64encode(wallpaper.read_bytes()).decode("ascii")
    blocks = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="995" height="708" viewBox="0 0 995 708">',
        rect(0, 0, 995, 708, "#141922"),
        text(15, 36, "Complete desktop preview", size=14, weight=650),
        rect(714, 11, 123, 41, "#293240", 8, stroke="#707d90"),
        text(725, 37, "Aurora Night" if night else "Aurora Day"),
        rect(847, 11, 132, 41, "#293240", 8, stroke="#707d90"),
        text(862, 37, "Overview" if night else "Files (Thunar)"),
        f'<image x="15" y="63" width="965" height="520" preserveAspectRatio="xMidYMid slice" '
        f'href="data:image/jpeg;base64,{photo}"/>',
    ]
    bar_bg, bar_fg = ("#f8f9fb", "#25313e") if night else ("#10151d", "#f1f5fa")
    dock_bg, icon_bg, icon_fg = (("#f0f4f8", "#c9d7e8", "#1b2938") if night else
                                  ("#10151d", "#35445b", "#f5f7fb"))
    blocks += [rect(15, 63, 965, 30, bar_bg),
               text(26, 82, "◉   Applications     Files     View", bar_fg, 12),
               text(803, 82, "Network · Audio   12:42", bar_fg, 12)]

    if night:
        for px, width, title, names in ((42, 286, "Applications", ("Files", "Browser", "Terminal", "Settings", "Editor", "Music")),
                                        (678, 275, "Control Center", ("Wi-Fi", "Bluetooth", "Volume", "Brightness", "Quick Actions"))):
            height = 410 if px == 42 else 308
            blocks += [rect(px, 116, width, height, "#151b29", 13, opacity=".94"),
                       text(px + 15, 147, title, size=16, weight=650)]
            offset = 0
            if px == 42:
                blocks += [rect(px + 15, 161, width - 30, 40, "#354256", 9),
                           text(px + 25, 186, "Search apps", "#c4d0dd", 12)]
                offset = 48
            for index, label in enumerate(names):
                y = 163 + offset + index * 50
                blocks += [rect(px + 15, y, width - 30, 41, "#263244", 9),
                           rect(px + 25, y + 6, 30, 29, "#637d9f", 6),
                           text(px + 36, y + 26, label[0], size=13),
                           text(px + 65, y + 26, label, size=13)]
    else:
        # Finder-style sidebar, breadcrumb path and icon view, in Thunar.
        blocks += [rect(208, 158, 572, 306, "#f4f6f9", 15, stroke="#cdd7e3"),
                   rect(208, 158, 166, 306, "#e8edf3", 14),
                   text(230, 192, "FAVORITES", "#6d7a8f", 11, 650)]
        for i, label in enumerate(("Home", "Documents", "Downloads", "Pictures", "Devices")):
            blocks.append(text(235, 231 + i * 39, "▣   " + label, "#243246", 13))
        blocks += [text(399, 194, "Home  ›  Documents", "#283546", 13),
                   rect(392, 209, 366, 1, "#d6dee8"),
                   text(402, 242, "Files and folders", "#25313f", 16, 650)]
        for i, label in enumerate(("Projects", "Music", "Pictures", "Desktop", "Notes", "Backups")):
            x = 415 + i % 3 * 118
            y = 292 + i // 3 * 79
            blocks += [text(x + 20, y + 16, "▰", "#7eabda", 34),
                       text(x + 7, y + 38, label, "#334356", 12)]

    blocks.append(rect(330, 506, 336, 63, dock_bg, 18, opacity=".95"))
    for i, letter in enumerate(("F", "W", ">_", "M", "S", "+")):
        x = 340 + i * 54
        blocks += [rect(x, 516, 44, 43, icon_bg, 10),
                   text(x + 13, 545, letter, icon_fg, 18, 650)]

    blocks += [text(15, 602, "Illustrative preview — your actual app icons, screens and live desktop may differ.", "#a2acba", 11),
               rect(15, 626, 148, 37, "#2876d0", 7, stroke="#5a93d8"),
               text(26, 649, "Apply complete Rice", size=12),
               rect(171, 626, 179, 37, "#364354", 7, stroke="#657487"),
               text(182, 649, "Restore previous desktop", size=12),
               text(15, 689, "Nothing changes until you confirm Apply.", "#a2acba", 11),
               "</svg>"]
    return "\n".join(blocks)


def main():
    for style, name in (("night", "full-rice-overview-0.2.0rc2.png"),
                        ("day", "full-rice-thunar-day-0.2.0rc2.png")):
        with tempfile.TemporaryDirectory(prefix="macrice-preview-") as directory:
            vector = Path(directory) / "preview.svg"
            vector.write_text(render(style), encoding="utf-8")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(vector), "-frames:v", "1", str(OUT / name)], check=True)
        print(OUT / name)


if __name__ == "__main__":
    main()
