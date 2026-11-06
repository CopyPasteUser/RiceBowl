"""Versioned, data-only bridge from a RicePlate panel recipe to Taskotto.

The desktop recipe itself is JSON and must not be passed to Taskotto's TOML
loader. Export a small, validated appearance-only file instead; Taskotto is
optional and does not need to be installed to create the file.
"""

from __future__ import annotations

import json
from pathlib import Path

from .recipes import PanelRecipe, _write_private_new, load


FORMAT_VERSION = 1

# Only explicit, supported background identifiers may select a visual family.
# Generic/custom panel-only recipes stay on Taskotto's independent base UI.
WALLPAPER_THEME = {
    "aero-seven-blue": "windows7",
    "aero-seven-night": "windows7",
    "luna-hills": "xp-luna",
    "classic-teal": "windows98",
    "ten-blue": "windows10",
    "ten-midnight": "windows10",
    "chrome-pastel": "chromeos",
    "frutiger-future": "frutiger-aero",
    "aurora-day": "macos",
    "aurora-night": "macos",
}


def render(recipe: PanelRecipe) -> bytes:
    """Return a deterministic Taskotto v1 TOML handoff; never embed commands."""
    base = WALLPAPER_THEME.get(recipe.wallpaper, "chromeos" if recipe.recipe_id == "chrome" else "system")
    name = f"RiceBowl: {recipe.name}"
    # The validated RicePlate name is intentionally bounded by its own schema.
    if len(name) > 64 or any(ord(char) < 32 for char in name):
        raise ValueError("RicePlate recipe name cannot fit in Taskotto's 64-char field")
    background, foreground, active = recipe.colors
    lines = [
        f"format_version = {FORMAT_VERSION}",
        f"name = {json.dumps(name, ensure_ascii=True)}",
        f"base_theme = {json.dumps(base)}",
        "",
        "[appearance]",
        f"accent = {json.dumps(active)}",
        f"surface = {json.dumps(background)}",
        f"text = {json.dumps(foreground)}",
        "navigation = \"auto\"",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def export(token: str, destination: Path) -> PanelRecipe:
    """Validate RicePlate input and atomically create a new owner-only TOML."""
    recipe = load(token)
    _write_private_new(destination, render(recipe), suffix=".toml")
    return recipe
