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
import sys
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


def render(style, *, detailed_plank=False):
    night = style == "night"
    wallpaper = ROOT / "assets/wallpapers" / ("aurora-night.jpg" if night else "aurora-day.jpg")
    photo = base64.b64encode(wallpaper.read_bytes()).decode("ascii")
    blocks = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="995" height="708" viewBox="0 0 995 708">',
        rect(0, 0, 995, 708, "#141922"),
        text(15, 36, "macOS-inspired XFCE + Plank" if detailed_plank else "Complete desktop preview", size=14, weight=650),
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

    if detailed_plank:
        # Deliberately an illustration of the actual Plank layout, never a claimed live screenshot.
        blocks.append(rect(250, 505, 494, 69, dock_bg, 16, opacity=".89", stroke="#d5e6f8", stroke_width="1.5"))
        shades = ("#3f9eed", "#e0af54", "#427bcf", "#1b344e", "#eff5ff", "#7994b7", "#445c7e", "#dfe9f4")
        for i, color in enumerate(shades):
            x = 266 + i * 59
            blocks.append(rect(x, 516, 49, 47, color, 10, stroke="#f5fbff", stroke_width="1", opacity=".97"))
            if i == 0:
                blocks += [rect(x + 2, 518, 21, 43, "#c0efff", 9),
                           '<path d="M280 532q5-6 10 0m-15 11q11 12 21 0" fill="none" stroke="#20578a" stroke-width="2"/>']
            elif i == 1:
                blocks += [rect(x + 8, 531, 34, 22, "#fff3bc", 5, stroke="#ba8b40"),
                           rect(x + 8, 526, 17, 8, "#fff3bc", 3)]
            elif i == 2:
                blocks += [f'<circle cx="{x+25}" cy="539" r="17" fill="#48bbef"/>',
                           f'<path d="M{x+13} 530q-4 24 19 24q15-11 5-26q3 15-10 12q-10-4-3-16" fill="#ff8b3d" stroke="#f4d377" stroke-width="2"/>']
            elif i == 3:
                blocks += [rect(x + 6, 523, 37, 30, "#101c2d", 6),
                           text(x + 13, 545, ">_", "#bcebd9", 16, 650)]
            elif i == 4:
                blocks += [f'<ellipse cx="{x+25}" cy="540" rx="15" ry="17" fill="#193c60"/>',
                           f'<ellipse cx="{x+25}" cy="543" rx="10" ry="13" fill="#fff"/>',
                           f'<circle cx="{x+21}" cy="537" r="2" fill="#101c2d"/>',
                           f'<circle cx="{x+29}" cy="537" r="2" fill="#101c2d"/>']
            elif i == 5:
                blocks += [f'<circle cx="{x+25}" cy="539" r="15" fill="#bdcfe7" stroke="#283f65" stroke-width="4"/>',
                           f'<circle cx="{x+25}" cy="539" r="7" fill="#3c5f93"/>']
            elif i == 6:
                for offset in (0, 10, 20):
                    blocks += [rect(x + 9, 528 + offset, 31, 3, "#dbeaff", 1),
                               f'<circle cx="{x+17+offset//2}" cy="{529+offset}" r="5" fill="#9dc4e7" stroke="#2d4568"/>']
            else:
                blocks += [rect(x + 14, 525, 23, 28, "#f7fcff", 4, stroke="#728c9e"),
                           rect(x + 19, 520, 14, 6, "#fff", 3, stroke="#728c9e")]
        blocks += [rect(268, 567, 42, 3, "#2a648e", 1), rect(445, 567, 42, 3, "#2a648e", 1)]
    else:
        blocks.append(rect(330, 506, 336, 63, dock_bg, 18, opacity=".95"))
        for i, letter in enumerate(("F", "W", ">_", "M", "S", "+")):
            x = 340 + i * 54
            blocks += [rect(x, 516, 44, 43, icon_bg, 10),
                       text(x + 13, 545, letter, icon_fg, 18, 650)]

    blocks += [text(15, 602, "Illustrative Plank dock composition — your actual apps and layout may differ." if detailed_plank else
                    "Illustrative preview — your actual app icons, screens and live desktop may differ.", "#a2acba", 11),
               rect(15, 626, 148, 37, "#2876d0", 7, stroke="#5a93d8"),
               text(26, 649, "Apply complete Rice", size=12),
               rect(171, 626, 179, 37, "#364354", 7, stroke="#657487"),
               text(182, 649, "Restore previous desktop", size=12),
               text(15, 689, "Nothing changes until you confirm Apply.", "#a2acba", 11),
               "</svg>"]
    return "\n".join(blocks)


def main():
    if "--plank" in sys.argv:
        with tempfile.TemporaryDirectory(prefix="macrice-plank-preview-") as directory:
            vector = Path(directory) / "preview.svg"
            vector.write_text(render("night", detailed_plank=True), encoding="utf-8")
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(vector), "-frames:v", "1",
                            str(OUT / "macos-rice-with-plank-0.2.0rc1.png")], check=True)
        print(OUT / "macos-rice-with-plank-0.2.0rc1.png")
        return
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
