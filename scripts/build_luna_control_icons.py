#!/usr/bin/env python3
"""Reproducible original XP-era Control Panel artwork (no Microsoft assets)."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
ICON_DIR = ROOT / "assets/icons/RiceHub-Luna-Icons/scalable/apps"

# A compact, object-like 2001 visual language: dark ink outlines, molded
# surfaces, glass highlights and individual material colors per category.
# These are not reskinned monochrome symbol-font glyphs.
ART = {
    "appearance": '''
<rect x="4" y="8" width="45" height="35" rx="4" fill="#3c455b" stroke="#182d4e" stroke-width="2"/>
<rect x="7" y="11" width="39" height="29" rx="2" fill="url(#screen)"/>
<path d="M10 30Q23 12 43 15" fill="none" stroke="#fff" stroke-width="4" opacity=".72"/>
<path d="M20 44h13v6H20zM14 50h25v4H14z" fill="url(#steel)" stroke="#536b87"/>
<path d="M47 25l9 4-14 26-11 6 4-12z" fill="url(#gold)" stroke="#8f5b22" stroke-width="1.5"/>
<path d="M47 25l9 4-4 7-10-5z" fill="#f05a42" stroke="#a32e2b"/>
<path d="M35 49l7 6-11 6z" fill="#d7ac6a"/>
''',
    "network": '''
<circle cx="37" cy="26" r="22" fill="url(#globe)" stroke="#2260a0" stroke-width="2"/>
<ellipse cx="37" cy="26" rx="11" ry="21" fill="none" stroke="#e5ffff" stroke-width="2"/>
<path d="M17 26h40M23 14h28M23 39h28" fill="none" stroke="#d5faff" stroke-width="2"/>
<path d="M20 12Q30 4 47 10" fill="none" stroke="#fff" stroke-width="4" opacity=".65"/>
<rect x="2" y="34" width="30" height="22" rx="3" fill="url(#steel)" stroke="#304967" stroke-width="2"/>
<rect x="5" y="37" width="24" height="15" fill="url(#screen)"/>
<path d="M15 57h6v3h7v2H8v-2h7z" fill="#63788b"/>
''',
    "programs": '''
<rect x="3" y="22" width="44" height="34" rx="3" fill="url(#gold)" stroke="#97611f" stroke-width="2"/>
<path d="M3 27h44M11 22v34" stroke="#e2b56d" stroke-width="2"/>
<circle cx="41" cy="24" r="20" fill="url(#disc)" stroke="#7085a4" stroke-width="1.5"/>
<circle cx="41" cy="24" r="5" fill="#71859b" stroke="#fff" stroke-width="2"/>
<path d="M28 12q17-14 27 3" fill="none" stroke="#fff" stroke-width="5" opacity=".85"/>
<path d="M17 43l7 7 11-14" fill="none" stroke="#267e37" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
''',
    "audio": '''
<path d="M5 25h14L36 10v44L19 39H5z" fill="url(#steel)" stroke="#405b81" stroke-width="2"/>
<path d="M9 28h10L31 18v27L19 36H9z" fill="#7cbbf9" opacity=".78"/>
<path d="M41 20q13 12 0 24M47 13q21 19 0 38" fill="none" stroke="#2e69bd" stroke-width="5" stroke-linecap="round"/>
<path d="M41 20q13 12 0 24" fill="none" stroke="#c1e5ff" stroke-width="2"/>
<circle cx="49" cy="8" r="5" fill="#eea449" stroke="#c07128"/>
''',
    "performance": '''
<path d="M24 3h14l2 9 8-4 9 9-5 8 9 3v13l-9 3 4 8-9 9-8-5-3 8H23l-3-8-9 5-8-9 5-8-7-3V28l8-3-4-8 9-9 8 4z" fill="url(#gold)" stroke="#926429" stroke-width="2"/>
<circle cx="30" cy="34" r="16" fill="url(#steel)" stroke="#455b76" stroke-width="2"/>
<circle cx="30" cy="34" r="10" fill="#fff8cf" stroke="#9f9c88"/>
<path d="M30 25v9l7 5" stroke="#31588b" stroke-width="2.5" fill="none" stroke-linecap="round"/>
''',
    "hardware": '''
<rect x="10" y="5" width="39" height="21" rx="2" fill="url(#steel)" stroke="#53647b" stroke-width="2"/>
<rect x="13" y="8" width="33" height="15" fill="#fff5dd"/>
<rect x="4" y="23" width="52" height="29" rx="5" fill="url(#screen)" stroke="#435d7c" stroke-width="2"/>
<rect x="11" y="41" width="38" height="17" rx="2" fill="#ebf4ff" stroke="#8c9db1"/>
<path d="M16 46h28M16 50h20" stroke="#3a71b6" stroke-width="2"/>
<circle cx="48" cy="33" r="3" fill="#71d654" stroke="#348b3e"/>
''',
    "accounts": '''
<circle cx="23" cy="19" r="13" fill="url(#gold)" stroke="#99682c" stroke-width="2"/>
<path d="M12 20q0-14 11-14t12 14" fill="#7b4a24"/>
<path d="M3 52q2-20 20-20t20 20v8H3z" fill="url(#screen)" stroke="#335eaa" stroke-width="2"/>
<circle cx="46" cy="26" r="10" fill="#f8d0a1" stroke="#ba8554" stroke-width="1.5"/>
<path d="M37 26q0-13 10-11t9 11" fill="#6b493b"/>
<path d="M41 38q18-8 21 18H43z" fill="#78b958" stroke="#36773c" stroke-width="2"/>
''',
    "regional": '''
<circle cx="28" cy="31" r="26" fill="url(#steel)" stroke="#5e6b7c" stroke-width="2"/>
<circle cx="28" cy="31" r="21" fill="#fffefa" stroke="#8c9bad" stroke-width="2"/>
<path d="M28 14v17l12 7" stroke="#2460ae" stroke-width="3" fill="none" stroke-linecap="round"/>
<circle cx="28" cy="31" r="3" fill="#ba512f"/>
<path d="M28 12v4M28 47v4M9 31h4M43 31h4" stroke="#6b83a4" stroke-width="2"/>
<circle cx="51" cy="47" r="12" fill="url(#globe)" stroke="#277d94" stroke-width="2"/>
<path d="M40 47h22M51 36q-10 11 0 22M51 36q10 11 0 22" stroke="#dcffff" fill="none"/>
''',
    "accessibility": '''
<circle cx="29" cy="11" r="8" fill="url(#gold)" stroke="#9a662a" stroke-width="1.5"/>
<path d="M29 24v16h17l6 11" fill="none" stroke="#266cbb" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="30" cy="45" r="15" fill="none" stroke="#587faa" stroke-width="5"/>
<path d="M29 26l-2 15h17" fill="none" stroke="#1a4d9c" stroke-width="4" stroke-linecap="round"/>
<path d="M42 56l7 5 9-6" fill="none" stroke="#3d9b36" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
''',
}

SHARED_DEFS = '''<defs>
<linearGradient id="screen" x2="0" y2="1"><stop stop-color="#f8ffff"/><stop offset=".46" stop-color="#b0e0fc"/><stop offset="1" stop-color="#2877ca"/></linearGradient>
<linearGradient id="steel" x2="0" y2="1"><stop stop-color="#f6f9ff"/><stop offset=".53" stop-color="#a5b5cb"/><stop offset="1" stop-color="#657996"/></linearGradient>
<linearGradient id="gold" x2="0" y2="1"><stop stop-color="#fff5bb"/><stop offset=".48" stop-color="#f6bf60"/><stop offset="1" stop-color="#c7832b"/></linearGradient>
<radialGradient id="globe" cx=".37" cy=".25"><stop stop-color="#e3ffff"/><stop offset=".55" stop-color="#69c8ee"/><stop offset="1" stop-color="#2170bf"/></radialGradient>
<linearGradient id="disc" x2=".7" y2="1"><stop stop-color="#f4f5fe"/><stop offset=".4" stop-color="#a5e3f4"/><stop offset=".65" stop-color="#f6cadb"/><stop offset="1" stop-color="#94b3df"/></linearGradient>
</defs>'''

# Distinctive miniature badges keep individual applets recognizable in Classic
# View while the larger 3D object communicates the owning XP category.
TASK_BADGES = {
    "preferences-desktop-theme": '<path d="M42 51l8-13 8 5-8 13z" fill="#f06c50" stroke="#a83a33"/>',
    "preferences-desktop-wallpaper": '<path d="M38 53l7-8 4 4 4-8 8 15H38z" fill="#51b44b"/>',
    "preferences-system-windows": '<rect x="39" y="41" width="21" height="14" rx="2" fill="#cde9ff" stroke="#3172bc"/><path d="M40 45h19" stroke="#3566b1" stroke-width="3"/>',
    "network-workgroup": '<path d="M39 49h8l5-8 6 10" fill="none" stroke="#266ac4" stroke-width="4"/>',
    "bluetooth": '<path d="M49 39v17l7-6-14-8m0 13 14-14-7-4" fill="none" stroke="#3276c9" stroke-width="2.6"/>',
    "system-software-install": '<path d="M40 43h18v12H40z" fill="#f6b857" stroke="#a96826"/><path d="M49 40v15m-5-5 5 5 5-5" stroke="#2b8d3b" fill="none" stroke-width="3"/>',
    "system-search": '<circle cx="46" cy="45" r="7" fill="#d7edff" stroke="#3174b8" stroke-width="3"/><path d="M51 50l7 7" stroke="#38659d" stroke-width="4"/>',
    "preferences-desktop-default-applications": '<path d="M40 48l7 7 12-15" fill="none" stroke="#299f39" stroke-width="4" stroke-linecap="round"/>',
    "audio-card": '<path d="M39 45h6l6-5v16l-6-5h-6z" fill="#e1f6ff" stroke="#3a72b8"/><path d="M54 43q8 6 0 11" fill="none" stroke="#246ac1" stroke-width="3"/>',
    "preferences-desktop-notification": '<path d="M42 51l3-11h9l4 11z" fill="#f5c058" stroke="#a77529"/><circle cx="50" cy="54" r="2" fill="#b9702c"/>',
    "utilities-system-monitor": '<path d="M39 55l5-9 4 5 5-12 6 16" stroke="#4ca653" stroke-width="3" fill="none"/>',
    "battery": '<rect x="39" y="43" width="17" height="12" rx="2" fill="#92dc79" stroke="#438c39"/><path d="M56 47h3v4h-3" stroke="#438c39" stroke-width="3"/>',
    "preferences-system": '<path d="M48 40l2 4 4-1 3 4-3 4 2 4-6 3-3-4-4 1-3-5 4-4-1-3z" fill="#89a4c9" stroke="#355884"/><circle cx="49" cy="49" r="4" fill="#e7f7ff"/>',
    "printer": '<rect x="40" y="43" width="19" height="13" rx="2" fill="#c5d9f0" stroke="#527091"/><rect x="44" y="50" width="11" height="10" fill="#fff" stroke="#7b92b2"/>',
    "video-display": '<rect x="39" y="40" width="20" height="14" fill="#a9daf8" stroke="#30629e" stroke-width="2"/><path d="M49 54v5m-7 0h14" stroke="#567ca5" stroke-width="2"/>',
    "input-mouse": '<rect x="45" y="39" width="12" height="20" rx="6" fill="#e8edf4" stroke="#627e9d" stroke-width="2"/><path d="M51 41v8" stroke="#3d6dad" stroke-width="2"/>',
    "system-users": '<circle cx="46" cy="43" r="5" fill="#f1c080"/><path d="M39 57q2-12 9-12t11 12" fill="#4a94dc" stroke="#2c69aa"/>',
    "system-log-out": '<path d="M40 48h17m-6-6 6 6-6 6" fill="none" stroke="#f1993a" stroke-width="4" stroke-linecap="round"/>',
    "preferences-system-time": '<circle cx="49" cy="49" r="10" fill="#fff" stroke="#4779b5" stroke-width="2"/><path d="M49 42v7l5 3" stroke="#2d67ad" stroke-width="2" fill="none"/>',
    "input-keyboard": '<rect x="39" y="44" width="22" height="13" rx="2" fill="#ebf0fa" stroke="#607f9d"/><path d="M42 48h16m-16 4h16" stroke="#5582b2" stroke-width="2"/>',
    "preferences-desktop-accessibility": '<circle cx="49" cy="41" r="4" fill="#f5bb62"/><path d="M49 46v8h8m-8-4-7 6" stroke="#3276bf" stroke-width="3" fill="none"/>',
}


def _svg(title, artwork):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<title>RiceBowl XP Control Panel: ' + title + '</title>'
            + SHARED_DEFS + artwork + '</svg>\n')


def generate():
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    for category, artwork in ART.items():
        (ICON_DIR / f"ricehub-luna-cp-{category}.svg").write_text(
            _svg(category, artwork), encoding="utf-8")
    # The applet badges are embedded in each SVG, not runtime image overlays.
    # GTK's icon cache therefore scales the whole 64px drawing correctly.
    from macrice.luna_control_panel import LUNA_CATEGORIES, LUNA_TASKS

    categories = {name: icon.removeprefix("ricehub-luna-cp-")
                  for name, icon, _tools, _detail in LUNA_CATEGORIES}
    for name, tasks in LUNA_TASKS.items():
        base = ART[categories[name]]
        for _label, icon, _tools, _detail in tasks:
            if icon not in TASK_BADGES:
                raise ValueError("Luna Control Panel badge missing: " + icon)
            badge = ('<circle cx="49" cy="49" r="14" fill="#fffdf0" '
                     'stroke="#9aacc4" stroke-width="1.6"/>' + TASK_BADGES[icon])
            (ICON_DIR / f"ricehub-luna-task-{icon}.svg").write_text(
                _svg(icon, base + badge), encoding="utf-8")


if __name__ == "__main__":
    generate()
