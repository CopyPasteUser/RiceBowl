"""Small, bounded per-rice GTK window geometry preferences.

Only ordinary Settings windows use this module.  Position/size are per-window
and per-user, not global session preferences, and invalid/off-screen geometry
must never strand a window after a monitor is unplugged.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


_ROLE = re.compile(r"ricebowl-[a-z0-9-]{1,64}\Z")
_LIMIT = 1024
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class WindowGeometry:
    x: int
    y: int
    width: int
    height: int


def _validate(geometry: WindowGeometry) -> None:
    values = (geometry.x, geometry.y, geometry.width, geometry.height)
    if any(type(value) is not int for value in values):
        raise ValueError("Window geometry must contain integers")
    if not (-32768 <= geometry.x <= 32768 and -32768 <= geometry.y <= 32768
            and 240 <= geometry.width <= 8192 and 200 <= geometry.height <= 8192):
        raise ValueError("Window geometry is outside supported bounds")


def geometry_path(role: str) -> Path:
    if not isinstance(role, str) or not _ROLE.fullmatch(role):
        raise ValueError("Invalid settings window role")
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "ricehub" / "windows" / f"{role}.json"


def load(role: str, *, path: Path | None = None) -> WindowGeometry | None:
    path = path or geometry_path(role)
    if path.is_symlink():
        raise ValueError("Window geometry preferences cannot be symlinks")
    try:
        if path.stat().st_size > _LIMIT:
            raise ValueError("Window geometry preferences exceed size limit")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot read window geometry preferences") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "x", "y", "width", "height"}:
        raise ValueError("Unsupported window geometry format")
    if type(raw["version"]) is not int or raw["version"] != 1:
        raise ValueError("Unsupported window geometry version")
    result = WindowGeometry(raw["x"], raw["y"], raw["width"], raw["height"])
    _validate(result)
    return result


def save(role: str, geometry: WindowGeometry, *, path: Path | None = None) -> None:
    _validate(geometry)
    path = path or geometry_path(role)
    if path.parent.is_symlink() or path.parent.parent.is_symlink():
        raise ValueError("Window geometry preference directory cannot be a symlink")
    if path.exists() or path.is_symlink():
        load(role, path=path)  # Preserve unknown/corrupt user data.
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    body = json.dumps({"version": 1, "x": geometry.x, "y": geometry.y,
                       "width": geometry.width, "height": geometry.height}) + "\n"
    descriptor, temporary = tempfile.mkstemp(prefix=".window-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        if path.is_symlink():
            raise ValueError("Window geometry preferences became a symlink")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def visible_geometry(geometry: WindowGeometry, monitors) -> WindowGeometry:
    """Constrain saved size and ensure a reachable title strip on some monitor."""
    _validate(geometry)
    monitors = tuple(rect for rect in monitors if rect.width >= 240 and rect.height >= 200)
    if not monitors:
        return geometry
    # Keep a window on its old screen if that screen still exists.
    def overlap(rect):
        return (max(0, min(geometry.x + geometry.width, rect.x + rect.width) -
                    max(geometry.x, rect.x)) *
                max(0, min(geometry.y + geometry.height, rect.y + rect.height) -
                    max(geometry.y, rect.y)))

    rect = max(monitors, key=overlap)
    width = min(geometry.width, rect.width)
    height = min(geometry.height, rect.height)
    if overlap(rect) == 0:
        return WindowGeometry(rect.x + (rect.width - width) // 2,
                              rect.y + (rect.height - height) // 2, width, height)
    x = min(max(geometry.x, rect.x), rect.x + rect.width - min(width, 90))
    y = min(max(geometry.y, rect.y), rect.y + rect.height - min(height, 64))
    return WindowGeometry(x, y, width, height)


def restore_and_track(window, role: str, Gdk, GLib) -> bool:
    """Restore once; debounce subsequent geometry writes in the GTK loop."""
    try:
        saved = load(role)
    except (OSError, ValueError) as exc:
        _LOG.warning("Ignoring invalid %s window geometry: %s", role, exc)
        saved = None
    restored = False
    if saved is not None:
        try:
            screen = window.get_screen() or Gdk.Screen.get_default()
            monitors = (screen.get_monitor_geometry(index)
                        for index in range(screen.get_n_monitors())) if screen else ()
            safe = visible_geometry(saved, monitors)
            window.set_default_size(safe.width, safe.height)
            window.move(safe.x, safe.y)
            restored = True
        except (AttributeError, ValueError, TypeError) as exc:
            _LOG.warning("Cannot restore %s geometry: %s", role, exc)

    pending = [None]
    source = [0]

    def flush():
        source[0] = 0
        if pending[0] is not None:
            try:
                save(role, pending[0])
            except (OSError, ValueError) as exc:
                _LOG.warning("Cannot persist %s geometry: %s", role, exc)
        return False

    def configured(_window, _event):
        if not window.get_visible():
            return False
        gdk_window = window.get_window()
        if gdk_window is not None and gdk_window.get_state() & Gdk.WindowState.MAXIMIZED:
            return False
        x, y = window.get_position()
        width, height = window.get_size()
        candidate = WindowGeometry(x, y, width, height)
        try:
            _validate(candidate)
        except ValueError:
            return False
        pending[0] = candidate
        if source[0]:
            GLib.source_remove(source[0])
        source[0] = GLib.timeout_add(450, flush)
        return False

    def stopped(*_args):
        if source[0]:
            GLib.source_remove(source[0])
            source[0] = 0
        flush()
        return False

    window.connect("configure-event", configured)
    window.connect("unmap-event", stopped)
    window.connect("destroy", stopped)
    return restored
