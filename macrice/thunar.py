"""Small, scoped Thunar styling; never modify the installed WhiteSur theme.

Only the marked block in ~/.config/gtk-3.0/gtk.css belongs to MacRice.
Existing user CSS is preserved byte-for-byte outside that block.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


START = "/* MacRice Thunar: begin */"
END = "/* MacRice Thunar: end */"
PREFERENCES = (
    ("/last-location-bar", "ThunarLocationButtons"),
    ("/last-side-pane", "ThunarShortcutsPane"),
    ("/last-view", "ThunarIconView"),
)

PALETTES = {
    "night": {"chrome": "#202733", "sidebar": "#19212d", "text": "#f0f3f7",
              "accent": "#577ca6", "edge": "#343e4e"},
    "day": {"chrome": "#f4f6f9", "sidebar": "#e9edf3", "text": "#222936",
            "accent": "#91b8e2", "edge": "#d5dce5"},
    "aero": {"chrome": "#b8dcef", "sidebar": "#e0f0fa", "text": "#1a405f",
             "accent": "#62b2e3", "edge": "#80acd0"},
    "ten-dark": {"chrome": "#252527", "sidebar": "#202020", "text": "#f5f5f5",
                 "accent": "#0078d7", "edge": "#464646"},
    "ten-light": {"chrome": "#f4f4f4", "sidebar": "#e8e8e8", "text": "#202020",
                  "accent": "#0078d7", "edge": "#c8c8c8"},
    "winxp": {"chrome": "#e0ecff", "sidebar": "#c8dcfa", "text": "#153c75",
              "accent": "#3b83dd", "edge": "#80a8d7"},
    "winclassic": {"chrome": "#c0c0c0", "sidebar": "#dedede", "text": "#111111",
                   "accent": "#000080", "edge": "#808080"},
    "chromeos": {"chrome": "#f4f7ff", "sidebar": "#e8eef8", "text": "#27364e",
                 "accent": "#6393eb", "edge": "#c9d5e9"},
    "frutiger": {"chrome": "#d7fff7", "sidebar": "#c7f3e5", "text": "#145269",
                 "accent": "#36bdd9", "edge": "#8dd9d7"},
}


def _legacy_block(style: str) -> str:
    p = PALETTES[style]
    return f"""{START}
/* Scoped to Thunar's own GTK class; other applications are unaffected. */
window.thunar toolbar {{ background-color: {p['chrome']}; border-bottom: 1px solid {p['edge']}; }}
window.thunar .sidebar .view {{ background-color: {p['sidebar']}; color: {p['text']}; }}
window.thunar .sidebar .view:selected {{ background-color: {p['accent']}; color: #101925; }}
window.thunar .location-button {{ border-radius: 7px; }}
{END}
"""



def _v080_block(style: str) -> str:
    """Scoped distinct Thunar chrome; macOS palettes remain unchanged."""
    original = _legacy_block(style)
    if style in ("night", "day"):
        return original
    palette = PALETTES[style]
    common = (
        f"window.thunar .sidebar {{ background: {palette['sidebar']}; }}\n"
        f"window.thunar .sidebar .view:selected {{ background: {palette['accent']}; color: white; }}\n"
        f"window.thunar statusbar {{ border-top: 1px solid {palette['edge']}; }}\n"
        f"window.thunar .path-bar button:focus {{ border-color: {palette['accent']}; }}\n"
    )
    distinct = {
        "aero": "window.thunar toolbar { background-image: linear-gradient(#f6fcff, #b8dcef); }\n"
                "window.thunar .path-bar button { border-radius: 5px; }\n",
        "ten-dark": "window.thunar toolbar { background: #222226; }\n"
                    "window.thunar .path-bar button { border-radius: 0; }\n",
        "ten-light": "window.thunar toolbar { background: #f4f4f4; }\n"
                     "window.thunar .path-bar button { border-radius: 0; }\n",
        "winxp": "window.thunar toolbar { background-image: linear-gradient(#fff, #b8d5f6); border-bottom: 2px solid #6595ce; }\n"
                 "window.thunar .path-bar button { background-image: linear-gradient(#fff, #cfe5fd); border: 1px solid #92add6; border-radius: 4px; }\n",
        "winclassic": "window.thunar toolbar, window.thunar statusbar { background: #c0c0c0; color: #111; border-radius: 0; }\n"
                      "window.thunar .path-bar button { background: #c0c0c0; color: #111; border: 2px outset #eee; border-radius: 0; box-shadow: none; }\n"
                      "window.thunar .path-bar button:active { border-style: inset; }\n",
        "chromeos": "window.thunar toolbar { background: #f7faff; padding: 8px; }\n"
                    "window.thunar .path-bar button { background: #e4edfc; color: #293b57; border-radius: 15px; padding: 6px 12px; }\n",
        "frutiger": "window.thunar toolbar { background-image: linear-gradient(#fff, #c6f6ed 60%, #a7dff0); border-bottom: 2px solid #6dc6cb; }\n"
                    "window.thunar .path-bar button { background-image: linear-gradient(#fff, #c1f4ea); border: 1px solid #74d6dc; border-radius: 12px; }\n"
                    "window.thunar .sidebar { background-image: linear-gradient(#f1fffb, #c7f3e5); }\n",
    }[style]
    return original.replace(END + "\n", common + distinct + END + "\n")


# Richer GTK3 styling for four non-macOS file manager identities. The code
# acts only on Thunar windows and never changes macOS CSS.
DETAIL_CSS = {
    "winxp": "/* Luna file manager: warm command bar, glossy blue chrome and blue task pane. */\nwindow.thunar menubar { background-image: linear-gradient(#fff8e8, #e8e0c8); border-bottom: 1px solid #b8b092; color: #202020; padding: 3px 6px; }\nwindow.thunar toolbar, window.thunar .location-bar { background-image: linear-gradient(to bottom, #fcffff, #d8ebff 45%, #afceef); border-bottom: 2px solid #77a7da; padding: 4px 7px; }\nwindow.thunar toolbar button { background-image: linear-gradient(#fff, #d4e8fe); color: #17478c; border: 1px solid #a4bfe0; border-radius: 5px; padding: 6px; }\nwindow.thunar toolbar button:hover { background-image: linear-gradient(#fff, #b7d6ff); border-color: #4b90db; }\nwindow.thunar .sidebar, window.thunar .shortcuts-pane { background-image: linear-gradient(to right, #b0cafa, #dfedff); color: #163c79; border-right: 1px solid #91b0d8; }\nwindow.thunar .sidebar .view, window.thunar .shortcuts-pane .view { background: transparent; color: #143e7a; }\nwindow.thunar .sidebar .view:selected, window.thunar treeview.view:selected { background: #2767cb; color: white; }\nwindow.thunar .path-bar button, window.thunar .location-bar button { background-image: linear-gradient(#fff, #cce5fb); border: 1px solid #9cbadd; border-radius: 4px; padding: 5px 9px; color: #164481; }\nwindow.thunar .standard-view, window.thunar .view { background: #fff; }\nwindow.thunar statusbar { background-image: linear-gradient(#fff8e9, #eae3d1); color: #413a2e; border-top: 1px solid #c6bba1; padding: 3px 6px; }\n",
    "winclassic": "/* Win98/2000: pixel-sharp inset lists, raised toolbar, gray title context. */\nwindow.thunar menubar, window.thunar toolbar, window.thunar .location-bar { background: #c0c0c0; border-top: 2px solid #fff; border-left: 2px solid #fff; border-bottom: 2px solid #7b7b7b; padding: 1px 4px; color: #111; }\nwindow.thunar toolbar button, window.thunar .path-bar button { background: #c0c0c0; border: 2px outset #f4f4f4; border-radius: 0; box-shadow: none; color: #111; padding: 3px 6px; }\nwindow.thunar toolbar button:active, window.thunar .path-bar button:active { border-style: inset; }\nwindow.thunar toolbar button:hover { background: #d8d8d8; }\nwindow.thunar .sidebar, window.thunar .shortcuts-pane { background: #d4d4d4; border: 2px inset #efefef; color: #111; }\nwindow.thunar .sidebar .view, window.thunar .shortcuts-pane .view { background: #d4d4d4; color: #111; }\nwindow.thunar treeview.view, window.thunar .standard-view { background: #fff; border: 2px inset #eee; color: #111; }\nwindow.thunar treeview.view:selected, window.thunar .sidebar .view:selected { background: #000080; color: #fff; }\nwindow.thunar treeview header button { background: #c0c0c0; border: 2px outset #fff; border-radius: 0; color: #111; padding: 2px 4px; }\nwindow.thunar statusbar { background: #c0c0c0; border-top: 2px outset #fff; border-radius: 0; color: #111; padding: 2px; }\nwindow.thunar scrollbar slider { border-radius: 0; background: #b0b0b0; border: 1px solid #666; }\n",
    "chromeos": "/* ChromeOS: soft white tools, pill address field, cool lavender sidebar. */\nwindow.thunar menubar { background: #f4f6ff; border-bottom: 0; color: #344064; padding: 4px 8px; }\nwindow.thunar toolbar, window.thunar .location-bar { background-image: linear-gradient(#fafbff, #edf1fc); border-bottom: 1px solid #dde4f5; padding: 8px 11px; }\nwindow.thunar toolbar button { background: transparent; border: 1px solid transparent; border-radius: 14px; color: #35486d; padding: 6px 8px; }\nwindow.thunar toolbar button:hover { background: #e2eafd; border-color: #d1def5; }\nwindow.thunar .path-bar button, window.thunar .location-bar button { background: #e7ecfc; color: #303d67; border: 1px solid #dee3f5; border-radius: 16px; padding: 7px 13px; }\nwindow.thunar .sidebar, window.thunar .shortcuts-pane { background-image: linear-gradient(#eef1ff, #e4ebfc); color: #34476b; border-right: 1px solid #d4ddf3; }\nwindow.thunar .sidebar .view, window.thunar .shortcuts-pane .view { background: transparent; color: #34476b; }\nwindow.thunar .sidebar .view:selected { background: #cfdbfb; color: #24417a; border-radius: 9px; }\nwindow.thunar treeview.view:selected { background: #d6ddf9; color: #263966; }\nwindow.thunar .standard-view, window.thunar .view { background: #fcfdff; }\nwindow.thunar statusbar { background: #f2f4ff; color: #596987; border-top: 1px solid #e1e6f5; padding: 6px 10px; }\nwindow.thunar scrollbar slider { background: #c6d0ee; border-radius: 9px; }\n",
    "frutiger": "/* Frutiger Aero: layered translucent aqua, neon-green selection and glass buttons. */\nwindow.thunar menubar { background-image: linear-gradient(#effffd, #cdf9f0); border-bottom: 1px solid #7bd7db; color: #075a79; padding: 4px 8px; }\nwindow.thunar toolbar, window.thunar .location-bar { background-image: linear-gradient(#fff, #c5fff2 47%, #83d9e7); border-bottom: 2px solid #65c9d0; padding: 7px 10px; }\nwindow.thunar toolbar button { background-image: linear-gradient(#fff, #b8f6e9 55%, #84d8db); border: 1px solid #70cfd3; border-radius: 11px; color: #096584; padding: 7px; box-shadow: inset 0 1px #fff; }\nwindow.thunar toolbar button:hover { background-image: linear-gradient(#fff, #9df5d8); border-color: #21abc2; }\nwindow.thunar .path-bar button, window.thunar .location-bar button { background-image: linear-gradient(#faffff, #aff7ed); border: 1px solid #61cbd3; border-radius: 16px; color: #09647e; padding: 7px 12px; }\nwindow.thunar .sidebar, window.thunar .shortcuts-pane { background-image: linear-gradient(to right, #d9fff0, #b0eee9); border-right: 2px solid #83d0d9; color: #09677c; }\nwindow.thunar .sidebar .view, window.thunar .shortcuts-pane .view { background: transparent; color: #07576f; }\nwindow.thunar .sidebar .view:selected, window.thunar treeview.view:selected { background: #a1ed43; color: #174960; border-radius: 8px; }\nwindow.thunar .standard-view, window.thunar .view { background: #f5fffe; color: #064f6b; }\nwindow.thunar statusbar { background-image: linear-gradient(#eafff8, #bcf5e6); color: #075f7d; border-top: 1px solid #81cdd7; padding: 5px 9px; }\nwindow.thunar scrollbar slider { background: #78d5d6; border-radius: 10px; }\n"
}


def _block(style: str) -> str:
    original = _v080_block(style)
    if style not in DETAIL_CSS:
        return original
    return original.replace(END + "\n", DETAIL_CSS[style] + END + "\n")


def _read_css(path: Path) -> str | None:
    if path.parent.is_symlink() or path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError("Unmanaged GTK CSS path; refusing to overwrite it")
    if not path.exists():
        return None
    if path.stat().st_size > 60 * 1024:
        raise ValueError("GTK CSS is too large for safe MacRice editing")
    return path.read_text(encoding="utf-8")


def plan_css(style: str, config_root: Path) -> dict[str, str | None]:
    """Return original and intended text without modifying the filesystem."""
    if style not in PALETTES:
        raise ValueError("Unknown Thunar palette")
    path = config_root / "gtk-3.0/gtk.css"
    before = _read_css(path)
    content = before or ""
    if content.count(START) != content.count(END) or content.count(START) > 1:
        raise ValueError("Existing MacRice GTK CSS block is incomplete; nothing changed")
    if START in content:
        left, tail = content.split(START, 1)
        inner, right = tail.split(END, 1)
        current_block = START + inner + END + "\n"
        if current_block not in ({_block(name) for name in PALETTES} | {_v080_block(name) for name in PALETTES} | {_legacy_block(name) for name in PALETTES}):
            raise ValueError("MacRice Thunar styling was customized; refusing to replace it")
        # The existing block owns exactly one newline after END.
        if right.startswith("\n"):
            right = right[1:]
        after = left + _block(style) + right
        if len(after.encode("utf-8")) > 60 * 1024:
            raise ValueError("GTK CSS would exceed the safe size limit")
        return {"before": before, "after": after}
    if content and not content.endswith("\n"):
        content += "\n"
    after = content + ("\n" if content else "") + _block(style)
    if len(after.encode("utf-8")) > 60 * 1024:
        raise ValueError("GTK CSS would exceed the safe size limit")
    return {"before": before, "after": after}


def write_css(config_root: Path, content: str | None) -> None:
    """Atomic update, with an explicit no-symlink policy for the target."""
    path = config_root / "gtk-3.0/gtk.css"
    _read_css(path)
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".macrice-thunar-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)
