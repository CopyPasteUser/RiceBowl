"""Data-only RicePlate panel recipes with a temporary Waybar rendering adapter.

Recipe files are deliberately not executable plugins. The v1 layout vocabulary
is independent of Waybar so a future native RicePlate renderer can consume it.
"""

from __future__ import annotations

import json
import fcntl
import os
import re
import stat
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_RECIPE_BYTES = 64 * 1024
MAX_SELECTION_BYTES = 2048
WIDGETS = frozenset(("launcher", "tasks", "clock", "network", "audio", "battery", "tray"))
SECTIONS = ("start", "center", "end")
COLORS = ("background", "foreground", "active")
BUILTINS = {
    "classic": Path(__file__).resolve().parent / "resources/recipes/classic.json",
    "chrome": Path(__file__).resolve().parent / "resources/recipes/chrome.json",
}


class RecipeError(ValueError):
    """Invalid or unsupported RicePlate recipe; no desktop changes made."""


@dataclass(frozen=True)
class PanelRecipe:
    recipe_id: str
    name: str
    position: str
    height: int
    sections: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]
    colors: tuple[str, str, str]


def _object_without_duplicates(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise RecipeError("Duplicate recipe key")
        result[key] = value
    return result


def _strict_keys(value: Any, keys: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RecipeError(f"{context} must contain exactly: {', '.join(sorted(keys))}")
    return value


def parse(raw: bytes) -> PanelRecipe:
    """Validate a bounded, declarative schema with no commands or asset paths."""
    if len(raw) > MAX_RECIPE_BYTES:
        raise RecipeError("RicePlate recipe exceeds the 64 KiB limit")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_without_duplicates)
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise RecipeError(f"Invalid RicePlate recipe JSON: {exc}") from exc
    data = _strict_keys(data, {"schema_version", "id", "name", "panel", "colors"}, "Recipe")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise RecipeError("Unsupported RicePlate recipe schema version")
    recipe_id = data["id"]
    if not isinstance(recipe_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", recipe_id):
        raise RecipeError("Recipe ID must contain 2-32 lowercase ASCII characters")
    name = data["name"]
    if (not isinstance(name, str) or not 1 <= len(name) <= 60
            or any(unicodedata.category(character) == "Cc" for character in name)):
        raise RecipeError("Recipe name must be 1-60 printable characters")
    panel = _strict_keys(data["panel"], {"position", "height", "sections"}, "Panel")
    if panel["position"] not in ("top", "bottom"):
        raise RecipeError("Panel position must be top or bottom")
    if type(panel["height"]) is not int or not 28 <= panel["height"] <= 64:
        raise RecipeError("Panel height must be an integer between 28 and 64")
    sections = _strict_keys(panel["sections"], set(SECTIONS), "Panel sections")
    selected: list[tuple[str, ...]] = []
    all_widgets: list[str] = []
    for section in SECTIONS:
        widgets = sections[section]
        if (not isinstance(widgets, list) or len(widgets) > 7
                or any(not isinstance(widget, str) or widget not in WIDGETS
                       for widget in widgets)):
            raise RecipeError(f"Invalid widget list in panel section {section}")
        selected.append(tuple(widgets))
        all_widgets.extend(widgets)
    if len(all_widgets) != len(set(all_widgets)):
        raise RecipeError("A panel widget may appear only once")
    if not {"tasks", "launcher"} & set(all_widgets):
        raise RecipeError("Panel must provide tasks or an application launcher")
    colors = _strict_keys(data["colors"], set(COLORS), "Colors")
    for color in COLORS:
        if not isinstance(colors[color], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", colors[color]):
            raise RecipeError(f"Invalid six-digit hexadecimal color: {color}")
    return PanelRecipe(recipe_id, name, panel["position"], panel["height"],
                       (selected[0], selected[1], selected[2]),
                       (colors["background"], colors["foreground"], colors["active"]))


def load(token: str) -> PanelRecipe:
    """Read a bundled recipe or an explicit owner-private absolute JSON file."""
    if token in BUILTINS:
        raw = BUILTINS[token].read_bytes()
        result = parse(raw)
        if result.recipe_id != token:
            raise RecipeError("Bundled recipe ID does not match its name")
        return result
    installed_id = bool(re.fullmatch(r"[a-z][a-z0-9-]{1,31}", token))
    path = _private_recipe_dir(create=False) / f"{token}.json" if installed_id else Path(token)
    if not path.is_absolute():
        raise RecipeError("Use a bundled recipe name or an absolute JSON file path")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as file:
            meta = os.fstat(file.fileno())
            if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                    or meta.st_mode & 0o077):
                raise RecipeError("Custom recipe must be a private owner-only regular file")
            if meta.st_size > MAX_RECIPE_BYTES:
                raise RecipeError("RicePlate recipe exceeds the 64 KiB limit")
            raw = file.read(MAX_RECIPE_BYTES + 1)
    except OSError as exc:
        raise RecipeError("Custom recipe could not be opened safely") from exc
    result = parse(raw)
    if installed_id and result.recipe_id != token:
        raise RecipeError("Imported recipe ID does not match its filename")
    return result


def _read_import_source(source: Path) -> bytes:
    """Read a bounded, owner-controlled data file once, without following links.

    Unlike an active recipe, an offline import may be world-readable (0644).
    Group/world-writable files and files owned by another user are rejected.
    """
    if not source.is_absolute() or source.suffix != ".json":
        raise RecipeError("Import requires an absolute .json file path")
    try:
        fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(fd, "rb") as file:
            meta = os.fstat(file.fileno())
            if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                    or meta.st_mode & 0o022):
                raise RecipeError("Import source must be an owner-controlled regular file")
            if meta.st_size > MAX_RECIPE_BYTES:
                raise RecipeError("RicePlate recipe exceeds the 64 KiB limit")
            return file.read(MAX_RECIPE_BYTES + 1)
    except OSError as exc:
        raise RecipeError("Import source could not be opened safely") from exc


def _write_private_new(destination: Path, payload: bytes) -> None:
    """Publish a complete 0600 file atomically, refusing any existing target."""
    if not destination.is_absolute() or destination.suffix != ".json":
        raise RecipeError("Output must be an absolute .json file path")
    descriptor, temporary = tempfile.mkstemp(prefix=".ricebowl-recipe-",
                                              dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, destination)
    finally:
        os.unlink(temporary)


def _private_recipe_dir(*, create: bool) -> Path:
    """Find the dedicated user-owned collection, never changing its permissions."""
    configured = os.environ.get("XDG_CONFIG_HOME")
    root = Path(configured) if configured else Path.home() / ".config"
    if not root.is_absolute():
        raise RecipeError("XDG_CONFIG_HOME must be an absolute directory")
    directory = root / "ricebowl" / "recipes"
    for path in (root, root / "ricebowl", directory):
        if create and not path.exists() and not path.is_symlink():
            path.mkdir(mode=0o700)
        try:
            meta = path.lstat()
        except FileNotFoundError:
            if not create:
                return directory
            raise RecipeError(f"Recipe directory is unavailable: {path}") from None
        if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.geteuid()
                or meta.st_mode & 0o022):
            raise RecipeError(f"Unsafe recipe configuration directory: {path}")
        # The collection itself must be private. An existing ~/.config/ricebowl
        # (created by older releases) may legitimately be 0755: it is safe as
        # long as others cannot WRITE it and the recipes subdir is 0700.
        if path == directory and meta.st_mode & 0o077:
            raise RecipeError(f"Recipe directory must be owner-only: {path}")
    return directory


def import_recipe(source: Path) -> tuple[PanelRecipe, Path]:
    """Import validated offline JSON into the user collection, without applying it."""
    payload = _read_import_source(source)
    recipe = parse(payload)
    if recipe.recipe_id in BUILTINS:
        raise RecipeError("Cannot import a recipe with a reserved built-in ID")
    destination = _private_recipe_dir(create=True) / f"{recipe.recipe_id}.json"
    _write_private_new(destination, payload)
    return recipe, destination


def export_recipe(token: str, destination: Path) -> PanelRecipe:
    """Export a validated recipe as owner-private portable JSON; never overwrite."""
    if token in BUILTINS:
        payload = BUILTINS[token].read_bytes()
    else:
        installed_id = bool(re.fullmatch(r"[a-z][a-z0-9-]{1,31}", token))
        source = (_private_recipe_dir(create=False) / f"{token}.json"
                  if installed_id else Path(token))
        payload = _read_import_source(source)
    recipe = parse(payload)
    if token not in BUILTINS and installed_id and recipe.recipe_id != token:
        raise RecipeError("Imported recipe ID does not match its filename")
    _write_private_new(destination, payload)
    return recipe


def imported_recipes() -> list[tuple[PanelRecipe, Path]]:
    """Discover installed private recipes without creating files or directories."""
    directory = _private_recipe_dir(create=False)
    if not directory.exists():
        return []
    entries = sorted(directory.iterdir())
    if len(entries) > 128:
        raise RecipeError("Too many imported recipes (limit 128)")
    found = []
    for path in entries:
        if path.suffix != ".json":
            continue
        recipe = load(str(path))
        if recipe.recipe_id != path.stem or recipe.recipe_id in BUILTINS:
            raise RecipeError(f"Imported recipe ID does not match its filename: {path.name}")
        found.append((recipe, path))
    return found


def native_token(token: str) -> str:
    """Resolve an imported ID for native Rust, which accepts private abs paths."""
    if token in BUILTINS:
        return token
    if re.fullmatch(r"[a-z][a-z0-9-]{1,31}", token):
        return str(_private_recipe_dir(create=False) / f"{token}.json")
    return token


def _read_selection(directory: Path) -> dict[str, Any] | None:
    path = directory / ".active-recipe"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise RecipeError("Cannot safely read the selected RicePlate recipe") from exc
    with os.fdopen(fd, "rb") as stream:
        meta = os.fstat(stream.fileno())
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                or meta.st_mode & 0o077 or meta.st_size > MAX_SELECTION_BYTES):
            raise RecipeError("Selected recipe state is not an owner-private bounded file")
        raw = stream.read(MAX_SELECTION_BYTES + 1)
    try:
        data = json.loads(raw, object_pairs_hook=_object_without_duplicates)
        _strict_keys(data, {"schema_version", "active", "previous"}, "Selection")
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        raise RecipeError("Invalid selected recipe state") from exc
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise RecipeError("Unsupported recipe selection version")
    for field in ("active", "previous"):
        if (not isinstance(data[field], str)
                or not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", data[field])):
            raise RecipeError("Recipe selection must contain only built-in/imported IDs")
    return data


def current_selection() -> tuple[str, str | None]:
    """Read the next Wayland session's preference without any filesystem writes."""
    directory = _private_recipe_dir(create=False)
    if not directory.exists():
        return "classic", None
    state = _read_selection(directory)
    return (state["active"], state["previous"]) if state else ("classic", None)


def selected_recipe() -> str | None:
    """Return None for the unchanged default session, or a saved recipe ID."""
    active, previous = current_selection()
    return active if previous is not None else None


def change_selection(token: str | None = None, *, restore: bool = False) -> tuple[str, str]:
    """Change only the *next* Wayland session's recipe, with one-level undo.

    The active compositor and every XFCE setting remain untouched. The
    collection lock serializes concurrent authors before reading/writing.
    """
    if (restore and token is not None) or (not restore and token is None):
        raise RecipeError("Provide exactly one of a recipe ID or restore")
    directory = _private_recipe_dir(create=True)
    lock = directory / ".active-recipe.lock"
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    with os.fdopen(descriptor, "wb") as locked:
        meta = os.fstat(locked.fileno())
        if (not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.geteuid()
                or meta.st_mode & 0o077):
            raise RecipeError("Selected recipe lock is not owner-private")
        fcntl.flock(locked.fileno(), fcntl.LOCK_EX)
        state = _read_selection(directory)
        active = state["active"] if state else "classic"
        if restore:
            if not state:
                raise RecipeError("No previous RicePlate recipe selection to restore")
            target = state["previous"]
        else:
            assert token is not None
            target = token
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", target):
            raise RecipeError("Select a built-in or imported recipe ID, not a file path")
        load(target)  # Refuse a missing or corrupted recipe before changing state.
        if target == active:
            return target, active
        new_state = {"schema_version": 1, "active": target, "previous": active}
        payload = (json.dumps(new_state, separators=(",", ":")) + "\n").encode("utf-8")
        descriptor, temporary = tempfile.mkstemp(prefix=".ricebowl-selection-", dir=directory)
        try:
            with os.fdopen(descriptor, "wb") as output:
                os.fchmod(output.fileno(), 0o600)
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, directory / ".active-recipe")
            dirfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.fsync(dirfd)
            finally:
                os.close(dirfd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return target, active


def create_from_template(
    *, source: str, destination: Path, recipe_id: str, name: str,
) -> PanelRecipe:
    """Create one private editable recipe atomically, never replacing a file.

    Templates can change layout, but cannot inject commands, executable assets
    or unknown keys. Both native RicePlate and the Waybar adapter validate the
    same schema before using an authored recipe.
    """
    if source not in BUILTINS:
        raise RecipeError("Choose a bundled classic or chrome template")
    if not destination.is_absolute() or destination.suffix != ".json":
        raise RecipeError("New recipe output must be an absolute .json file path")
    data = json.loads(BUILTINS[source].read_text(encoding="utf-8"))
    data["id"] = recipe_id
    data["name"] = name
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    result = parse(payload)  # Validate *before* any filesystem mutation.

    # The temp file and destination share a directory/filesystem; os.link()
    # publishes a fully written file only when its final name is still free.
    # This does not overwrite existing files or follow a destination symlink.
    _write_private_new(destination, payload)
    return result


def waybar_config(recipe: PanelRecipe) -> tuple[str, str]:
    """Translate safe UI structure into Waybar's temporary JSON/CSS backend."""
    module_names = {
        "launcher": "custom/rice-launcher", "tasks": "wlr/taskbar",
        "clock": "clock", "network": "network", "audio": "pulseaudio",
        "battery": "battery", "tray": "tray",
    }
    config: dict[str, Any] = {
        "layer": "top", "position": recipe.position, "height": recipe.height,
        "spacing": 8,
        **{f"modules-{side}": [module_names[widget] for widget in widgets]
           for side, widgets in zip(("left", "center", "right"), recipe.sections)},
        "wlr/taskbar": {"format": "{icon}", "icon-size": 22,
                        "on-click": "minimize-raise", "tooltip-format": "{title}"},
        "custom/rice-launcher": {"format": "◈", "on-click": "fuzzel",
                                 "tooltip": True, "tooltip-format": "Applications"},
        "clock": {"format": "{:%a %d %b  %H:%M}"},
    }
    background, foreground, active = recipe.colors
    css = (
        "* { font-family: sans-serif; font-size: 12px; }\n"
        f"window#waybar {{ background: {background}; color: {foreground}; }}\n"
        "#taskbar button { border-radius: 4px; padding: 2px 7px; }\n"
        f"#taskbar button.active {{ background: {active}; }}\n"
        "#clock, #network, #pulseaudio, #battery, #tray, #custom-rice-launcher "
        "{ padding: 0 8px; }\n"
    )
    return json.dumps(config, ensure_ascii=False, indent=2), css
