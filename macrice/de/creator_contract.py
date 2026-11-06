"""Pure, versioned AI/human authoring contract for real panel components.

Kept separate from file IO, live Wayland state and the renderer. Agents can
discover the exact vocabulary before producing any draft edit data.
"""

from __future__ import annotations

from . import recipes

EDIT_VERSION = 1
MAX_EDIT_BYTES = 16 * 1024
MAX_OPERATIONS = 16

EDITABLE_PATHS = frozenset((
    "/name", "/panel/position", "/panel/height",
    *(f"/panel/sections/{name}" for name in recipes.SECTIONS),
    *(f"/panel/layout/{name}" for name in recipes.SECTIONS),
    *(f"/panel/metrics/{name}" for name in recipes.METRIC_FIELDS),
    *(f"/colors/{name}" for name in recipes.COLORS),
))


def describe() -> dict[str, object]:
    """Tool-neutral JSON guidance derived from one allowlisted vocabulary."""
    return {
        "edit_version": EDIT_VERSION,
        "command": "de draft-edit",
        "scope": "panel-only",
        "operation": "set",
        "editable_paths": sorted(EDITABLE_PATHS),
        "max_edit_bytes": MAX_EDIT_BYTES,
        "max_operations": MAX_OPERATIONS,
        "source": "bundled/imported recipe ID or private absolute .json path",
        "edit_input": "owner-controlled absolute .json file",
        "output": "new owner-private absolute .json file, never overwrite",
        "mutates_active_desktop": False,
        "mutates_next_session_selection": False,
        "edits_id_or_schema_version": False,
        "arbitrary_actions_or_scripts": False,
        "example_source_recipe": "classic",
        "example": {
            "edit_version": EDIT_VERSION,
            "operations": [
                {"op": "set", "path": "/panel/height", "value": 44},
                {"op": "set", "path": "/panel/sections/start", "value": ["launcher"]},
                {"op": "set", "path": "/panel/sections/center", "value": ["tasks"]},
            ],
        },
    }
