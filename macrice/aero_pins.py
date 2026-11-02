"""Safe, tiny user-local pinned launcher preferences for the Aero taskbar."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

PIN_LIMIT = 6
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+@-]{0,127}\.desktop\Z")


class PinConfigError(ValueError):
    pass


def pin_file(profile: str = "aero") -> Path:
    if profile not in ("aero", "windows10"):
        raise PinConfigError("Unknown taskbar profile")
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "ricehub" / f"{profile}-pins.json"


def validate_ids(ids) -> tuple[str, ...]:
    if not isinstance(ids, (list, tuple)) or len(ids) > PIN_LIMIT:
        raise PinConfigError("Too many pinned applications")
    result = []
    for identifier in ids:
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise PinConfigError("Invalid desktop launcher identifier")
        if identifier in result:
            raise PinConfigError("Duplicate pinned application")
        result.append(identifier)
    return tuple(result)


def load_pins(path: Path) -> tuple[str, ...] | None:
    """None means use built-in defaults; () is an intentional empty taskbar."""
    if path.is_symlink():
        raise PinConfigError("Refusing symlinked pins file")
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 8192:
        raise PinConfigError("Unexpected pin configuration")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PinConfigError("Cannot read pinned applications") from exc
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise PinConfigError("Unknown pin configuration schema")
    return validate_ids(data.get("pinned"))


def save_pins(path: Path, identifiers) -> None:
    items = validate_ids(identifiers)
    if path.is_symlink() or path.parent.is_symlink():
        raise PinConfigError("Refusing symlinked pin configuration")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists() and not path.is_file():
        raise PinConfigError("Pin configuration is not a regular file")
    fd, temp = tempfile.mkstemp(prefix=".aero-pins-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema": 1, "pinned": list(items)}, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)
