"""Data-only Rice packs and on-demand capability discovery.

User packs are named presets of *existing, transactionally supported* RiceBowl
styles. A JSON document cannot execute code, introduce a session process or
silently replace system themes. New renderer/asset formats require a separately
reviewed contract; do not interpret arbitrary manifest paths or commands.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from ..environment import bin_home, data_home
from .profiles import PROFILE_FAMILIES

SCHEMA_VERSION = 1
MAX_PACK_BYTES = 16 * 1024
MAX_PACK_FILES = 128
_IDENTIFIER = re.compile(r"[a-z][a-z0-9-]{1,47}\Z")
_FIELDS = frozenset(("schema_version", "id", "name", "base_style", "description"))

# This is also the single mapping used by XFCE session reconciliation.
FAMILY_SHELL = {
    "macos": None, "win7": "aero", "win10": "ten",
    "winxp": "winxp", "win98": "winclassic", "chromeos": "chromeos",
    "frutiger": "frutiger",
}


@dataclass(frozen=True)
class RicePack:
    id: str
    name: str
    base_style: str
    description: str = ""
    source: str = "built-in"

    def manifest(self) -> dict[str, object]:
        from ..rice import STYLES

        style = STYLES[self.base_style]
        family = PROFILE_FAMILIES[self.base_style]
        return {
            "schema_version": SCHEMA_VERSION,
            **asdict(self),
            "family": family,
            "shell": FAMILY_SHELL[family],
            "appearance": {
                "gtk": style.gtk, "xfwm": style.xfwm,
                "icons": style.icon_theme, "cursor": style.cursor_theme,
                "wallpaper": style.wallpaper,
            },
        }


def builtins() -> tuple[RicePack, ...]:
    from ..rice import STYLES

    if set(STYLES) != set(PROFILE_FAMILIES):
        raise ValueError("Rice style and renderer catalogs disagree")
    return tuple(RicePack(key, style.name, key) for key, style in STYLES.items())


def shell_for_theme(theme: str) -> tuple[str | None, bool]:
    """Resolve a live GTK theme to a shell and macOS flag, without I/O.

    Multiple wallpaper/color variants can share a GTK theme. They must agree
    on their shell family or the theme cannot safely identify a session.
    """
    from ..rice import STYLES

    families = {PROFILE_FAMILIES[key] for key, style in STYLES.items()
                if style.gtk == theme}
    if len(families) != 1:
        return None, False
    family = families.pop()
    return FAMILY_SHELL[family], family == "macos"


def _name(value: object, maximum: int) -> bool:
    return (isinstance(value, str) and 1 <= len(value.strip()) <= maximum
            and value == value.strip() and value.isprintable())


def _read_user_pack(path: Path) -> RicePack:
    # Open with O_NOFOLLOW: racing a symlink into the directory cannot cause
    # the manifest loader to read an unrelated private file.
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o022 or info.st_size > MAX_PACK_BYTES):
            raise ValueError("unsafe ownership, permissions or size")
        raw = stream.read(MAX_PACK_BYTES + 1)
    if len(raw) > MAX_PACK_BYTES:
        raise ValueError("manifest is too large")
    try:
        values = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 JSON") from exc
    if (not isinstance(values, dict) or not set(values) <= _FIELDS
            or not (_FIELDS - {"description"}) <= set(values)
            or type(values["schema_version"]) is not int
            or values["schema_version"] != SCHEMA_VERSION):
        raise ValueError("unsupported manifest schema")
    key = values["id"]
    if not isinstance(key, str) or not _IDENTIFIER.fullmatch(key) or path.name != key + ".json":
        raise ValueError("pack ID must match its safe filename")
    if not _name(values["name"], 80):
        raise ValueError("invalid pack name")
    description = values.get("description", "")
    if not isinstance(description, str) or (description and not _name(description, 240)):
        raise ValueError("invalid pack description")
    if values["base_style"] not in PROFILE_FAMILIES:
        raise ValueError("unknown built-in base style")
    return RicePack(key, values["name"], values["base_style"], description, "user")


def discover(directory: Path | None = None) -> tuple[tuple[RicePack, ...], tuple[str, ...]]:
    """Read only user-owned JSON files; report invalid entries without paths."""
    packs = {item.id: item for item in builtins()}
    root = directory if directory is not None else data_home() / "ricebowl/packs"
    try:
        unsafe = (root.is_symlink() or (root.exists() and
                  (not root.is_dir() or root.stat().st_uid != os.getuid())))
    except OSError:
        return tuple(packs.values()), ("User rice pack directory cannot be inspected",)
    if unsafe:
        return tuple(packs.values()), ("User rice pack directory is not a safe directory",)
    if not root.exists():
        return tuple(packs.values()), ()
    try:
        paths = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError:
        return tuple(packs.values()), ("User rice pack directory is unreadable",)
    warnings = []
    candidates = [path for path in paths if path.suffix == ".json"]
    if len(candidates) > MAX_PACK_FILES:
        warnings.append("Too many user rice packs; only the first 128 were inspected")
    for path in candidates[:MAX_PACK_FILES]:
        try:
            pack = _read_user_pack(path)
            if pack.id in packs:
                raise ValueError("pack ID already exists")
            packs[pack.id] = pack
        except (OSError, ValueError, TypeError, KeyError) as exc:
            # Filename only after strict character filtering, never leak file
            # contents or a user's private absolute path into JSON/Hub output.
            label = path.name if _IDENTIFIER.fullmatch(path.stem) else "unrecognized file"
            reason = "unreadable or unsafe file" if isinstance(exc, OSError) else str(exc)
            warnings.append(f"Rejected {label}: {reason}")
    return tuple(packs.values()), tuple(warnings)


def resolve(pack_id: str, directory: Path | None = None) -> RicePack:
    packs, warnings = discover(directory)
    for pack in packs:
        if pack.id == pack_id:
            return pack
    detail = "; ".join(warnings) if warnings else "not installed"
    raise ValueError(f"Unknown Rice pack: {pack_id} ({detail})")


def capabilities(pack: RicePack, *, which=None, binaries: Path | None = None,
                 environment: Mapping[str, str] | None = None) -> dict[str, object]:
    """Read-only executable/session inventory; no actual hardware probing."""
    find = shutil.which if which is None else which
    root = bin_home() if binaries is None else binaries
    env = os.environ if environment is None else environment

    def installed(command: str) -> bool:
        local = root / command
        return (local.is_file() and os.access(local, os.X_OK)) or bool(find(command))

    session = bool(env.get("DISPLAY")) and env.get("XDG_SESSION_TYPE", "x11").lower() != "wayland"
    required = {
        "xfce-x11": session,
        "xfconf-query": installed("xfconf-query"),
        "gsettings": installed("gsettings"),
        "xfwm4": installed("xfwm4"),
    }
    optional = {
        "riceExplorer": installed("rice-explorer"),
        "NetworkManager": installed("nmcli"),
        "Bluetooth": installed("bluetoothctl"),
        "audio": installed("pactl") or installed("wpctl"),
    }
    if PROFILE_FAMILIES[pack.base_style] == "macos":
        required.update({"macbar": installed("macbar"), "plank": installed("plank")})
        optional.update({"macmenu": installed("macmenu"),
                         "control-center": installed("macos-control-center-toggle")})
    return {"pack": pack.id, "base_style": pack.base_style,
            "ready": all(required.values()), "required": required,
            "optional": optional}
