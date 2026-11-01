"""Minimal cross-app appearance presets, without touching the XFCE theme."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .environment import DesktopProfile, config_home, data_home, detect


PRESETS = ("System", "Midnight", "Light", "Graphite")
CONFIG_FILES = {
    "MacMenu": Path("macmenu/settings.json"),
    "Control Center": Path("macos-control-center/config.json"),
    "MacBar": Path("macbar/config.json"),
}


def preset_values(preset: str, profile: DesktopProfile | None = None) -> dict[str, str]:
    if preset not in PRESETS:
        raise ValueError(f"Unknown appearance preset: {preset}")
    if preset == "System":
        profile = profile or detect()
        dark = "dark" in (profile.gtk_theme or "").lower()
        return {
            "MacMenu": "system",
            "Control Center": "midnight" if dark else "light",
            "MacBar": "dark" if dark else "light",
        }
    return {
        "Midnight": {"MacMenu": "dark", "Control Center": "midnight", "MacBar": "dark"},
        "Light": {"MacMenu": "light", "Control Center": "light", "MacBar": "light"},
        "Graphite": {"MacMenu": "graphite", "Control Center": "graphite", "MacBar": "dark"},
    }[preset]


def _read_preferences(path: Path) -> dict:
    if not path.exists():
        return {}
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Refusing to change non-regular preferences: {path}")
    if path.stat().st_size > 512 * 1024:
        raise ValueError(f"Preferences are unexpectedly large: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Cannot read {path.name}; original preferences kept") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid settings object at {path}")
    return data


def _stage_json(target: Path, data: dict) -> Path:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".macrice-theme-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        return Path(temporary)
    except Exception:
        Path(temporary).unlink(missing_ok=True)
        raise


def apply_preset(
    preset: str, *, profile: DesktopProfile | None = None,
    config_root: Path | None = None, data_root: Path | None = None,
) -> Path:
    """Atomically stage all three preferences; restore from backup on failure.

    Existing unrelated settings (favorites, devices, notes, etc.) are retained.
    The caller explicitly requested this action; install never invokes it.
    """
    values = preset_values(preset, profile)
    config_root = config_root or config_home()
    data_root = data_root or data_home()
    planned = {}
    for component, relative in CONFIG_FILES.items():
        target = config_root / relative
        current = _read_preferences(target)
        planned[target] = {**current, "theme": values[component]}

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = data_root / "macrice" / "backups" / "themes" / stamp
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    snapshot = {}
    staged = {}
    completed = []
    try:
        for target, value in planned.items():
            if target.exists():
                before = backup / target.parent.name / target.name
                before.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                shutil.copy2(target, before, follow_symlinks=False)
                os.chmod(before, 0o600)
                snapshot[target] = before
            else:
                snapshot[target] = None
            staged[target] = _stage_json(target, value)
        for target, temp in staged.items():
            os.replace(temp, target)
            completed.append(target)
    except Exception:
        for target in reversed(completed):
            saved = snapshot[target]
            if saved:
                shutil.copy2(saved, target)
                os.chmod(target, 0o600)
            else:
                target.unlink(missing_ok=True)
        raise
    finally:
        for temp in staged.values():
            temp.unlink(missing_ok=True)
    return backup
