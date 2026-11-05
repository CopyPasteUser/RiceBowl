"""Small, independent Windows 10 taskbar preferences; no XFCE global writes."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


DEFAULTS = {"search": True, "task_view": True}


def preferences_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "ricehub" / "windows10-taskbar.json"


def validate(options) -> dict[str, bool]:
    if (not isinstance(options, dict) or set(options) != set(DEFAULTS) or
            any(type(value) is not bool for value in options.values())):
        raise ValueError("Invalid Windows 10 taskbar preferences")
    return dict(options)


def load(path: Path) -> dict[str, bool]:
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
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("Unknown taskbar preferences schema")
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
            json.dump({"schema": 1, "options": settings}, stream)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
