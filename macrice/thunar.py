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
}


def _block(style: str) -> str:
    p = PALETTES[style]
    return f"""{START}
/* Scoped to Thunar's own GTK class; other applications are unaffected. */
window.thunar toolbar {{ background-color: {p['chrome']}; border-bottom: 1px solid {p['edge']}; }}
window.thunar .sidebar .view {{ background-color: {p['sidebar']}; color: {p['text']}; }}
window.thunar .sidebar .view:selected {{ background-color: {p['accent']}; color: #101925; }}
window.thunar .location-button {{ border-radius: 7px; }}
{END}
"""


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
        if current_block not in {_block(name) for name in PALETTES}:
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
