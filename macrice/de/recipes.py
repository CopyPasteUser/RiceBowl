"""Data-only RicePlate panel recipes with a temporary Waybar rendering adapter.

Recipe files are deliberately not executable plugins. The v1 layout vocabulary
is independent of Waybar so a future native RicePlate renderer can consume it.
"""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_RECIPE_BYTES = 64 * 1024
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
            or any(ord(character) < 32 for character in name)):
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
    path = Path(token)
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
    return parse(raw)


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
