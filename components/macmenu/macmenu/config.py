"""Small, user-scoped and atomic preferences store."""

import json
import os
import tempfile
from pathlib import Path


DEFAULTS = {
    "theme": "dark",
    "position": "top-left",
    "icon_size": "normal",
    "instant_toggle": True,
    "history_enabled": True,
    "favorites": [],
    "recent": [],
}

BACKUP_FORMAT = "macmenu-settings-v1"


def _valid_app_id(value: object) -> bool:
    if not isinstance(value, str) or not 0 < len(value) <= 256:
        return False
    if any(ord(char) < 32 for char in value):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "macmenu" / "settings.json"


def sanitize(value: object) -> dict:
    """Accept only explicitly supported settings; discard unknown or invalid values."""
    if not isinstance(value, dict):
        value = {}
    result = {**DEFAULTS, "favorites": [], "recent": []}
    for key, choices in (
        ("theme", ("dark", "light", "graphite", "ocean", "violet", "system", "glass-dark", "glass-light", "aqua")),
        ("position", ("top-left", "bottom-left", "panel")),
        ("icon_size", ("small", "normal", "large")),
    ):
        if value.get(key) in choices:
            result[key] = value[key]
    for key in ("instant_toggle", "history_enabled"):
        if isinstance(value.get(key), bool):
            result[key] = value[key]
    for key in ("favorites", "recent"):
        items = value.get(key, [])
        if isinstance(items, list):
            result[key] = list(dict.fromkeys(x for x in items if _valid_app_id(x)))[:100 if key == "favorites" else 20]
    if not result["history_enabled"]:
        result["recent"] = []
    return result


def load(path: Path | None = None) -> dict:
    target = path or config_path()
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        value = {}
    return sanitize(value)


def parse_backup(contents: str) -> dict:
    """Reject unrelated/corrupt imports instead of silently resetting user data."""
    if len(contents.encode("utf-8")) > 128 * 1024:
        raise ValueError("Backup file is too large (128 KiB maximum).")
    try:
        raw = json.loads(contents)
    except ValueError as exc:
        raise ValueError("The file does not contain valid JSON.") from exc
    if not isinstance(raw, dict):
        raise ValueError("The backup must contain a JSON object.")
    if raw.get("backup_format", BACKUP_FORMAT) != BACKUP_FORMAT:
        raise ValueError("Unknown backup format.")
    if not any(key in raw for key in (*DEFAULTS, "view", "keep_running", "show_descriptions")):
        raise ValueError("This file contains no MacMenu preferences.")
    return sanitize(raw)


def serialize_backup(settings: dict) -> str:
    return json.dumps({"backup_format": BACKUP_FORMAT, **sanitize(settings)}, ensure_ascii=False, indent=2) + "\n"


def _atomic_write(contents: str, target: Path) -> None:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".settings-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(contents)
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def save(settings: dict, path: Path | None = None) -> None:
    target = path or config_path()
    contents = json.dumps(sanitize(settings), ensure_ascii=False, indent=2) + "\n"
    _atomic_write(contents, target)


def save_backup(settings: dict, path: Path) -> None:
    _atomic_write(serialize_backup(settings), path)
