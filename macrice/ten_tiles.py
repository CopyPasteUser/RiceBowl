"""Windows 10 Start tile layout, separate from taskbar pins and XFCE settings.

Only installed Gio application identifiers are rendered. Saved preferences may
retain temporarily unavailable IDs so reinstalling an app restores its tile.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import stat
import tempfile
import unicodedata

from .ten_shell import start_tiles


MAX_GROUPS = 6
MAX_TILES = 48
SIZES = {"small": (1, 1), "medium": (2, 2),
         "wide": (4, 2), "large": (4, 4)}
INITIAL_GROUPS = ("Productivity", "Explore")


def preferences_path() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / (
        "ricehub/windows10-tiles.json")


def _valid_text(value: object, maximum: int) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= maximum and
            value == value.strip() and all(unicodedata.category(ch) != "Cc"
                                            for ch in value))


def validate(layout) -> dict:
    if not isinstance(layout, dict) or set(layout) != {"groups"}:
        raise ValueError("Invalid Windows 10 Start tile layout")
    groups = layout["groups"]
    if not isinstance(groups, list) or not 1 <= len(groups) <= MAX_GROUPS:
        raise ValueError("Invalid tile group count")
    seen = set()
    count = 0
    for group in groups:
        if not isinstance(group, dict) or set(group) != {"name", "tiles"}:
            raise ValueError("Invalid tile group")
        if not _valid_text(group["name"], 36):
            raise ValueError("Invalid tile group name")
        entries = group["tiles"]
        if not isinstance(entries, list):
            raise ValueError("Invalid tile entries")
        for tile in entries:
            if not isinstance(tile, dict) or set(tile) != {"id", "size"}:
                raise ValueError("Invalid tile entry")
            identifier = tile["id"]
            if (not _valid_text(identifier, 256) or "/" in identifier or
                    not identifier.endswith(".desktop") or identifier in seen or
                    not isinstance(tile["size"], str) or tile["size"] not in SIZES):
                raise ValueError("Invalid or duplicate desktop tile")
            seen.add(identifier)
            count += 1
            if count > MAX_TILES:
                raise ValueError("Too many desktop tiles")
    return deepcopy(layout)


def default_layout(apps, taskbar_pins=()) -> dict:
    selected = start_tiles(apps, tuple(taskbar_pins))
    # A recognizably 22H2 mosaic even on first launch; users can change every tile.
    initial_sizes = ("medium", "medium", "wide", "small", "medium", "medium")
    tiles = [{"id": app.get_id(), "size": initial_sizes[index % len(initial_sizes)]}
             for index, app in enumerate(selected)]
    return validate({"groups": [
        {"name": INITIAL_GROUPS[0], "tiles": tiles[:4]},
        {"name": INITIAL_GROUPS[1], "tiles": tiles[4:]},
    ]})


def load(path: Path) -> dict | None:
    """Return None when no custom layout exists; never follow a symlink."""
    if path.parent.is_symlink():
        raise ValueError("Refusing symlinked tile preferences directory")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError("Cannot open Windows 10 tile preferences") from exc
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 16384:
            raise ValueError("Invalid Windows 10 tile preferences file")
        try:
            data = json.load(stream)
        except (json.JSONDecodeError, UnicodeError, OSError) as exc:
            raise ValueError("Cannot decode Windows 10 tile preferences") from exc
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("Unsupported Windows 10 tile schema")
    return validate(data.get("layout"))


def save(path: Path, layout) -> None:
    valid = validate(layout)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("Refusing symlinked Windows 10 tile preferences")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.parent.is_dir() or (path.exists() and not path.is_file()):
        raise ValueError("Invalid Windows 10 tile preferences directory")
    fd, temporary = tempfile.mkstemp(prefix=".ten-tiles-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema": 1, "layout": valid}, stream, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def tile_location(layout, identifier):
    for index, group in enumerate(layout["groups"]):
        for position, tile in enumerate(group["tiles"]):
            if tile["id"] == identifier:
                return index, position
    return None


def pin(layout, identifier, *, group_index=0):
    candidate = validate(layout)
    if not 0 <= group_index < len(candidate["groups"]):
        raise ValueError("Unknown tile group")
    if tile_location(candidate, identifier) is not None:
        return candidate
    candidate["groups"][group_index]["tiles"].append({"id": identifier,
                                                         "size": "medium"})
    return validate(candidate)


def unpin(layout, identifier):
    candidate = validate(layout)
    location = tile_location(candidate, identifier)
    if location is not None:
        group, position = location
        candidate["groups"][group]["tiles"].pop(position)
    return candidate


def resize(layout, identifier, size):
    if size not in SIZES:
        raise ValueError("Unsupported tile size")
    candidate = validate(layout)
    location = tile_location(candidate, identifier)
    if location is None:
        raise ValueError("Application is not pinned to Start")
    group, position = location
    candidate["groups"][group]["tiles"][position]["size"] = size
    return candidate


def move(layout, identifier, *, group_index=None, offset=0):
    candidate = validate(layout)
    location = tile_location(candidate, identifier)
    if location is None:
        raise ValueError("Application is not pinned to Start")
    old_group, position = location
    new_group = old_group if group_index is None else group_index
    if not 0 <= new_group < len(candidate["groups"]):
        raise ValueError("Unknown destination tile group")
    tile = candidate["groups"][old_group]["tiles"].pop(position)
    dest = candidate["groups"][new_group]["tiles"]
    if new_group != old_group:
        dest.append(tile)
    else:
        dest.insert(max(0, min(position + offset, len(dest))), tile)
    return candidate


def move_to(layout, identifier, target, *, after=False):
    """Insert a dragged tile beside another, also across named groups."""
    candidate = validate(layout)
    source_location = tile_location(candidate, identifier)
    target_location = tile_location(candidate, target)
    if source_location is None or target_location is None:
        raise ValueError("The dragged Start tile is not pinned")
    if identifier == target:
        return candidate
    source_group, source_index = source_location
    tile = candidate["groups"][source_group]["tiles"].pop(source_index)
    target_group, _target_index = target_location
    # Re-evaluate after the removal to avoid off-by-one shifts.
    new_index = tile_location(candidate, target)[1]
    candidate["groups"][target_group]["tiles"].insert(
        new_index + int(after), tile)
    return validate(candidate)


def rename_group(layout, group_index, name):
    candidate = validate(layout)
    if not 0 <= group_index < len(candidate["groups"]):
        raise ValueError("Unknown tile group")
    candidate["groups"][group_index]["name"] = name.strip()
    return validate(candidate)


def grid_positions(tiles) -> tuple[tuple[int, int, int, int], ...]:
    """First-fit Windows 10 mosaic in four columns, with zero overlap."""
    occupied = set()
    placements = []
    for tile in tiles:
        width, height = SIZES[tile["size"]]
        row = 0
        while True:
            place = next((col for col in range(5 - width)
                          if all((col + x, row + y) not in occupied
                                 for x in range(width) for y in range(height))), None)
            if place is not None:
                break
            row += 1
        placements.append((place, row, width, height))
        occupied.update((place + x, row + y)
                        for x in range(width) for y in range(height))
    return tuple(placements)
