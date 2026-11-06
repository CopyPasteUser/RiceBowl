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


def describe_capture() -> dict[str, object]:
    """Explicit capture of the user's current Wayland display, not a renderer."""
    return {
        "contract_version": 1,
        "command": "de capture",
        "required_options": ["--output"],
        "optional_options": ["--json"],
        "requires_running_wayland_session": True,
        "requires_binary": "grim",
        "capture_source": "current-wayland-compositor",
        "output": "new absolute owner-private PNG, never overwrite",
        "max_bytes": 64 * 1024 * 1024,
        "max_pixels": 16_777_216,
        "timeout_seconds": 30,
        "success_exit_code": 0,
        "capture_error_exit_code": 2,
        "error_codes": ["invalid_capture_request", "capture_unavailable", "capture_failed"],
        "creates_nested_session": False,
        "captures_live_desktop": True,
        "requires_explicit_invocation": True,
        "mutates_active_desktop": False,
        "screenshot_may_contain_private_data": True,
    }


def describe_render() -> dict[str, object]:
    """Offline optional headless renderer for one validated native recipe."""
    return {
        "contract_version": 1,
        "command": "de render",
        "required_options": ["--recipe", "--output"],
        "optional_options": ["--width", "--height", "--scale", "--json"],
        "default_geometry": {"width": 1366, "height": 768, "scale": 1.0},
        "width_range": [640, 4096],
        "height_range": [480, 2160],
        "max_pixels": 16_777_216,
        "scales": [1.0, 1.25, 1.5, 2.0],
        "requires_binaries": ["labwc", "wlr-randr", "grim", "riceplate-native", "swaybg"],
        "requires_running_wayland_session": False,
        "requires_unprivileged_user": True,
        "source": "validated bundled/imported/owner-private recipe",
        "backend": "headless-labwc-native-riceplate",
        "output": "new owner-private PNG, never overwrite",
        "creates_temporary_compositor": True,
        "keeps_processes_after_exit": False,
        "mutates_active_desktop": False,
        "functional_or_perceptual_fidelity": "not_measured",
        "error_codes": ["invalid_render_request", "render_unavailable", "render_failed"],
        "error_exit_code": 2,
    }


def describe_ricepack() -> dict[str, object]:
    """Portable v1 recipe-only archive: no executable or external assets."""
    return {
        "pack_version": 1,
        "format": "org.ricebowl.ricepack",
        "extension": ".ricepack",
        "entries": ["ricepack.json", "recipe.json"],
        "maximum_archive_bytes": 256 * 1024,
        "recipe_schema_versions": [1, 2, 3, 4, 5],
        "asset_support": "bundled-wallpapers-only",
        "third_party_assets": False,
        "arbitrary_code_or_scripts": False,
        "deterministic_export": True,
        "provenance": {
            "metadata_version": "fields-v1",
            "fields": ["author", "license", "origin", "source_reference"],
            "licenses": ["unspecified", "CC0-1.0", "CC-BY-4.0", "MIT", "custom"],
            "origins": ["unspecified", "original", "ai-assisted", "adapted"],
            "user_declared_not_verified": True,
        },
        "commands": [
            {"command": "de pack-export", "required_options": ["--recipe", "--output"],
             "optional_options": ["--metadata", "--json"], "creates_archive": True},
            {"command": "de pack-inspect", "required_options": ["--package"],
             "optional_options": ["--json"], "read_only": True},
            {"command": "de pack-import", "required_options": ["--package"],
             "optional_options": ["--json"], "installs_recipe_only": True},
        ],
        "import": "no-overwrite private user recipe collection; never activates",
        "failure_exit_code": 2,
        "success_exit_code": 0,
        "mutates_active_desktop": False,
    }


def describe_creator_api() -> dict[str, object]:
    """Stable, tool-neutral inventory, including explicit side-effect limits."""
    return {
        "api_version": 1,
        "scope": "experimental-wayland-shell-authoring",
        "transport": "CLI JSON; no resident socket or AI inference",
        "discovery": "ricebowl de creator-api --json",
        "success_exit_code": 0,
        "invalid_options_exit_code": 1,
        "operation_error_exit_code": 2,
        "active_session_mutation": "none of the Creator commands changes the active desktop",
        "commands": [
            {"command": "catalog", "effect": "read-only component discovery",
             "cli": "de catalog --json", "contract_version": 5},
            {"command": "review", "effect": "validate recipe and compare semantic diffs",
             "cli": "de review --recipe ID [--compare ID] --json", "contract_version": 1},
            {"command": "draft-edit", "effect": "create private reviewed JSON draft",
             "cli": "de draft-edit --recipe ID --edit FILE --output NEW.json --json",
             "contract_version": EDIT_VERSION},
            {"command": "render", "effect": "isolated real native headless screenshot",
             "cli": "de render --recipe ID --output NEW.png --json", "contract_version": 1},
            {"command": "visual-compare", "effect": "read-only screenshot analysis; optional new artifacts",
             "cli": "de visual-compare --reference FILE --actual FILE --json",
             "contract_version": 1},
            {"command": "capture", "effect": "explicit live Wayland screen capture (private data)",
             "cli": "de capture --output NEW.png --json", "contract_version": 1},
            {"command": "pack-export", "effect": "create portable validated recipe archive",
             "cli": "de pack-export --recipe ID --output NEW.ricepack --json",
             "contract_version": 1},
            {"command": "pack-inspect", "effect": "verify archive, schema and fingerprints",
             "cli": "de pack-inspect --package FILE.ricepack --json", "contract_version": 1},
            {"command": "pack-import", "effect": "install private recipe without selecting it",
             "cli": "de pack-import --package FILE.ricepack --json", "contract_version": 1},
        ],
        "ricepack": describe_ricepack(),
        "limitations": [
            "Not a screenshot-to-rice converter or editable GUI",
            "Only schema-v1..v5 panel/shell preview and bundled wallpapers",
            "No automatic apply; Wayland session remains experimental",
            "Keyboard, tray, native device controls and multi-monitor acceptance remain open",
        ],
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
