"""Bounded, atomic user preferences for Windows 7 StatusNotifier icons."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


MAX_PREFERENCES = 64
MAX_FILE_BYTES = 16384
MODES = ("auto", "show", "hide")
_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z")


@dataclass(frozen=True)
class TrayPreferences:
    visible_limit: int = 3
    icons: dict[str, str] = field(default_factory=dict)


def stable_icon_id(value: object) -> str | None:
    """Only persist a protocol Id, never an ephemeral D-Bus unique name."""
    if isinstance(value, str) and _KEY.fullmatch(value):
        return value
    return None


def preferences_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "ricehub" / "win7-tray.json"


def validate(prefs: TrayPreferences) -> None:
    if (not isinstance(prefs.visible_limit, int) or isinstance(prefs.visible_limit, bool)
            or not 0 <= prefs.visible_limit <= 8):
        raise ValueError("Visible icon count must be between 0 and 8")
    if not isinstance(prefs.icons, dict) or len(prefs.icons) > MAX_PREFERENCES:
        raise ValueError("Too many tray icon preferences")
    for key, value in prefs.icons.items():
        if stable_icon_id(key) is None or value not in MODES:
            raise ValueError("Invalid tray icon preference")


def load(path: Path | None = None) -> TrayPreferences:
    path = path or preferences_path()
    if path.is_symlink():
        raise ValueError("Tray preferences cannot be a symlink")
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("Tray preferences exceed size limit")
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return TrayPreferences()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot read Windows 7 tray preferences") from exc
    if (not isinstance(raw, dict) or raw.get("version") != 1 or
            set(raw) != {"version", "visible_limit", "icons"}):
        raise ValueError("Unsupported Windows 7 tray preferences format")
    prefs = TrayPreferences(raw["visible_limit"], raw["icons"])
    validate(prefs)
    return prefs


def save(prefs: TrayPreferences, path: Path | None = None) -> None:
    """Commit verified config atomically; never follow a symlink target."""
    validate(prefs)
    path = path or preferences_path()
    if path.exists() or path.is_symlink():
        load(path)  # Invalid or user-owned unknown data must not be overwritten.
    if path.parent.is_symlink():
        raise ValueError("Configuration directory cannot be a symlink")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    body = json.dumps({"version": 1, "visible_limit": prefs.visible_limit,
                       "icons": prefs.icons}, sort_keys=True, ensure_ascii=True) + "\n"
    if len(body.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("Tray preferences exceed size limit")
    descriptor, temporary = tempfile.mkstemp(prefix=".win7-tray-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        if path.is_symlink():
            raise ValueError("Tray preferences became a symlink")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
