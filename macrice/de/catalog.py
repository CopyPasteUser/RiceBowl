"""Versioned, read-only panel component discovery for humans and authoring agents.

The catalog reports only behavior supported by the actual preview backends.
It grants no ability to execute actions or change a running desktop.
"""

from __future__ import annotations

from .creator_contract import describe as draft_edit_contract
from .recipes import MAX_RECIPE_BYTES, METRIC_DEFAULTS, METRIC_FIELDS, METRIC_LIMITS, WIDGETS


def describe() -> dict[str, object]:
    """Describe the currently supported *panel-only* recipe contract."""
    return {
        "catalog_version": 1,
        "scope": "wayland-panel-preview",
        "complete_desktop_environment": False,
        "recipe": {
            "schema_versions": [1, 2],
            "maximum_bytes": MAX_RECIPE_BYTES,
            "sections": ["start", "center", "end"],
            "unique_widgets": True,
            "max_widgets_per_section": 7,
            "panel_positions": ["top", "bottom"],
            "panel_height": {"type": "integer", "min": 28, "max": 64, "unit": "logical-px"},
            "colors": {"fields": ["background", "foreground", "active"],
                       "format": "#RRGGBB"},
            "metrics": {
                "since_schema": 2,
                "required_in_schema_2": True,
                "forbidden_in_schema_1": True,
                "fields": {field: {"type": "integer", "min": lower,
                                   "max": upper, "default": METRIC_DEFAULTS[index],
                                   "unit": "logical-px"}
                           for index, (field, (lower, upper)) in
                           enumerate(zip(METRIC_FIELDS, METRIC_LIMITS))},
            },
            "custom_commands": False,
            "custom_actions": False,
            "external_assets": False,
        },
        "backends": {
            "native": "experimental-rust-layer-shell",
            "waybar": "fallback-adapter",
        },
        "authoring": {"draft_edit": draft_edit_contract()},
        "components": [
            {"id": "launcher", "native": "interactive", "waybar": "interactive",
             "behavior": "open-fuzzel", "keyboard_navigation": False,
             "width_property": "launcher_width"},
            {"id": "tasks", "native": "interactive", "waybar": "interactive",
             "behavior": "activate-minimize-windows", "keyboard_navigation": False,
             "width_property": "task_width",
             "native_details": ["group-by-app-id", "cycle-group-windows", "page-overflow"]},
            {"id": "clock", "native": "indicator", "waybar": "indicator",
             "behavior": "show-local-time", "keyboard_navigation": False,
             "width_property": "clock_width", "calendar_popup": False},
            {"id": "network", "native": "unavailable", "waybar": "indicator",
             "behavior": "show-network-status", "keyboard_navigation": False},
            {"id": "audio", "native": "unavailable", "waybar": "indicator",
             "behavior": "show-audio-status", "keyboard_navigation": False},
            {"id": "battery", "native": "unavailable", "waybar": "indicator",
             "behavior": "show-power-status", "keyboard_navigation": False},
            {"id": "tray", "native": "unavailable", "waybar": "host-tray",
             "behavior": "host-status-notifier-items", "keyboard_navigation": False},
        ],
        "limits": [
            "Panel-only recipes; no arbitrary OS or screenshot conversion",
            "No runtime configurable action bindings or custom scripts",
            "Native panel lacks tray, hardware controls, keyboard task navigation and popovers",
            "Waybar CSS widths are minima; content can grow",
            "Available status indicators depend on host services and devices",
            "No active desktop configuration is read or changed",
        ],
    }


def validate_catalog_contract() -> None:
    """Protect the discoverability contract from drifting off the recipe parser."""
    result = describe()
    ids = [component["id"] for component in result["components"]]
    metrics = tuple(result["recipe"]["metrics"]["fields"])
    if (len(ids) != len(set(ids)) or set(ids) != WIDGETS
            or metrics != METRIC_FIELDS):
        raise ValueError("RiceBowl component catalog is out of sync with panel recipes")
