"""Pure, versioned AI/human authoring contract for real panel components.

Kept separate from file IO, live Wayland state and the renderer. Agents can
discover the exact vocabulary before producing any draft edit data.
"""

from __future__ import annotations

from . import recipes

EDIT_VERSION = 1
MAX_EDIT_BYTES = 16 * 1024
MAX_OPERATIONS = 16


def describe_visual_qa() -> dict[str, object]:
    """Published on-demand Creator CLI contract, never a resident process."""
    return {
        "contract_version": 1,
        "command": "de visual-compare",
        "mode": "offline-real-capture-comparison",
        "required_options": ["--reference", "--actual"],
        "optional_options": ["--recipe", "--threshold", "--overlay", "--heatmap", "--json"],
        "capture_format": "PNG",
        "image_limit_megapixels": 16,
        "pixel_threshold": {"default": 24, "min": 0, "max": 255},
        "regions": ["panel", "desktop", "desktop-icon-*"],
        "region_semantics": "recipe-coordinates, may be clipped or unavailable",
        "artifact_behavior": "new absolute owner-private PNGs, never overwrite",
        "success_exit_code": 0,
        "invalid_input_exit_code": 2,
        "invalid_options_exit_code": 1,
        "error_code": "invalid_visual_input",
        "requires_running_wayland_session": False,
        "captures_live_desktop": False,
        "mutates_active_desktop": False,
        "perceptual_or_functional_accuracy": "not_measured",
    }


EDITABLE_PATHS = frozenset((
    "/name", "/panel/position", "/panel/height",
    *(f"/panel/sections/{name}" for name in recipes.SECTIONS),
    *(f"/panel/layout/{name}" for name in recipes.SECTIONS),
    "/menu/title", "/menu/groups", "/desktop/wallpaper",
    "/desktop/icons",
    "/tokens/label_padding", "/tokens/task_radius",
    "/responsive/compact_max_width",
    *(f"/responsive/compact_layout/{name}" for name in recipes.SECTIONS),
    *(f"/panel/metrics/{name}" for name in recipes.METRIC_FIELDS),
    *(f"/colors/{name}" for name in recipes.COLORS),
))


def describe() -> dict[str, object]:
    """Tool-neutral JSON guidance derived from one allowlisted vocabulary."""
    return {
        "edit_version": EDIT_VERSION,
        "command": "de draft-edit",
        "scope": "wayland-shell-preview",
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
