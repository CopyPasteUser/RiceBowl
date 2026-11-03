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



def _block(style: str) -> str:
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
        if current_block not in ({_block(name) for name in PALETTES} | {_legacy_block(name) for name in PALETTES}):
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
