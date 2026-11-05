"""Small, independent Windows 10 taskbar preferences; no XFCE global writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


SEARCH_MODES = ("hidden", "icon", "box")
DEFAULTS = {"search_mode": "box", "task_view": True}


def preferences_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "ricehub" / "windows10-taskbar.json"


def validate(options) -> dict:
    if (not isinstance(options, dict) or set(options) != set(DEFAULTS) or
            options["search_mode"] not in SEARCH_MODES or
            type(options["task_view"]) is not bool):
        raise ValueError("Invalid Windows 10 taskbar preferences")
    return dict(options)


def load(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("Refusing symlinked taskbar preferences")
    if not path.exists():
        return dict(DEFAULTS)
    if not path.is_file() or path.stat().st_size > 2048:
        raise ValueError("Unexpected taskbar preferences file")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Cannot read Windows 10 taskbar preferences") from exc
    if not isinstance(data, dict) or data.get("schema") not in (1, 2):
        raise ValueError("Unknown taskbar preferences schema")
    if data["schema"] == 1:
        legacy = data.get("options")
        if (not isinstance(legacy, dict) or set(legacy) != {"search", "task_view"}
                or any(type(value) is not bool for value in legacy.values())):
            raise ValueError("Invalid legacy taskbar preferences")
        return {"search_mode": "icon" if legacy["search"] else "hidden",
                "task_view": legacy["task_view"]}
    return validate(data.get("options"))


def save(path: Path, options) -> None:
    settings = validate(options)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing symlinked taskbar preferences")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists() and not path.is_file():
        raise ValueError("Taskbar preferences are not a regular file")
    fd, temporary = tempfile.mkstemp(prefix=".ten-taskbar-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema": 2, "options": settings}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
