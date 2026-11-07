"""Versioned, read-only shell component discovery for humans and agents.

The catalog reports only behavior supported by the actual preview backends.
It grants no ability to execute actions or change a running desktop.
"""

from __future__ import annotations

from .creator_contract import (describe as draft_edit_contract, describe_capture,
                               describe_creator_api, describe_render, describe_staging,
                               describe_ricepack, describe_visual_qa)
from .recipes import (ICON_ACTIONS, ICON_HEIGHT, ICON_WIDTH, MAX_DESKTOP_ICONS,
                      MENU_ACTIONS, WALLPAPERS, MAX_LAYOUT_CHILDREN, MAX_LAYOUT_DEPTH, MAX_LAYOUT_LABELS,
                      MAX_LAYOUT_NODES, MAX_LAYOUT_ROOTS, MAX_RECIPE_BYTES,
                      METRIC_DEFAULTS, METRIC_FIELDS, METRIC_LIMITS, WIDGETS)


def describe() -> dict[str, object]:
    """Describe exactly which panel and early shell primitives are implemented."""
    return {
        "catalog_version": 6,
        "scope": "wayland-shell-preview",
        "complete_desktop_environment": False,
        "recipe": {
            "schema_versions": [1, 2, 3, 4, 5],
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
            "nested_layout": {
                "since_schema": 3,
                "replaces_sections": True,
                "panel_regions": ["start", "center", "end"],
                "max_nodes": MAX_LAYOUT_NODES,
                "max_depth": MAX_LAYOUT_DEPTH,
                "max_roots_per_region": MAX_LAYOUT_ROOTS,
                "max_children_per_group": MAX_LAYOUT_CHILDREN,
                "max_labels": MAX_LAYOUT_LABELS,
                "node_types": {
                    "widget": {"fields": ["type", "id"], "known_ids": sorted(WIDGETS)},
                    "group": {"fields": ["type", "gap", "children"],
                              "gap": {"min": 0, "max": 32, "unit": "logical-px"}},
                    "gap": {"fields": ["type", "width"],
                            "width": {"min": 4, "max": 64, "unit": "logical-px"}},
                    "label": {"fields": ["type", "text"], "safe_ascii": True,
                              "max_characters": 24, "interactive": False},
                },
            },
            "shell_extensions": {
                "since_schema": 4,
                "menu": {"native": "output-bound-layer-shell-popup",
                         "waybar": "labwc-root-menu", "actions": sorted(MENU_ACTIONS),
                         "max_groups": 4, "max_actions_per_group": 4,
                         "search": False, "pins": False},
                "desktop": {"rendered": ["wallpaper"],
                            "wallpapers": sorted(WALLPAPERS),
                            "icons": {"since_schema": 5,
                                      "native": "interactive-layer-surfaces",
                                      "waybar": "not_available",
                                      "actions": sorted(ICON_ACTIONS),
                                      "max_count": MAX_DESKTOP_ICONS,
                                      "hit_width": ICON_WIDTH, "hit_height": ICON_HEIGHT,
                                      "coordinate_max": 4096,
                                      "native_placement": "single-output-logical-bounds-reflow",
                                      "keyboard_navigation": True,
                                      "keyboard_focus_entry": "pointer-or-compositor-focus",
                                      "pointer_drag": True,
                                      "keyboard_arrow_movement_px": 16,
                                      "position_storage": "private-per-rice-not-source-recipe",
                                      "nested_render_overrides": False},
                            "widgets": "not_implemented"},
                "tokens": {"label_padding": [0, 16], "task_radius": [0, 12]},
                "responsive": {"compact_max_width": [480, 1440],
                               "native": "live-panel-layout-switch",
                               "waybar": "offline-width-specific-compilation-only"},
            },
            "custom_commands": False,
            "custom_actions": False,
            "external_assets": False,
        },
        "backends": {
            "native": "experimental-rust-layer-shell",
            "waybar": "fallback-adapter",
        },
        "authoring": {"draft_edit": draft_edit_contract(),
                      "visual_compare": describe_visual_qa(),
                      "capture": describe_capture(),
                      "render": describe_render(),
                      "ricepack": describe_ricepack(),
                      "staging": describe_staging(),
                      "creator_api": {"api_version": describe_creator_api()["api_version"],
                                      "discovery": "ricebowl de creator-api --json"}},
        "components": [
            {"id": "launcher", "native": "interactive", "waybar": "interactive",
             "behavior": "native-menu-if-schema-4-else-fuzzel",
             "keyboard_navigation": True, "output_ownership": "per-output",
             "width_property": "launcher_width"},
            {"id": "tasks", "native": "interactive", "waybar": "interactive",
             "behavior": "activate-minimize-windows", "keyboard_navigation": True,
             "output_ownership": "per-output",
             "width_property": "task_width",
             "native_details": ["group-by-app-id", "cycle-group-windows",
                                "page-overflow", "independent-output-paging",
                                "focus-on-demand"]},
            {"id": "clock", "native": "interactive", "waybar": "indicator",
             "behavior": "show-local-time", "keyboard_navigation": False,
             "width_property": "clock_width", "calendar_popup": True,
             "popup_keyboard_navigation": True, "output_ownership": "per-output",
             "keyboard_focus_entry": "pointer-required"},
            {"id": "network", "native": "unavailable", "waybar": "indicator",
             "behavior": "show-network-status", "keyboard_navigation": False},
            {"id": "audio", "native": "unavailable", "waybar": "indicator",
             "behavior": "show-audio-status", "keyboard_navigation": False},
            {"id": "battery", "native": "indicator", "waybar": "indicator",
             "behavior": "show-kernel-battery-percent-or-unavailable",
             "status_backend": "read-only-linux-sysfs-power-supply",
             "status_refresh": "minute-boundary", "interactive": False,
             "keyboard_navigation": False},
            {"id": "tray", "native": "unavailable", "waybar": "host-tray",
             "behavior": "host-status-notifier-items", "keyboard_navigation": False},
        ],
        "shell_components": [
            {"id": "native-menu", "since_schema": 4,
             "recipe_pointer": "/menu", "native": "interactive-output-local",
             "waybar": "compiled-labwc-root-menu",
             "actions": sorted(MENU_ACTIONS),
             "input": ["pointer", "Left/Right", "Up/Down/Tab", "Enter/Space", "Escape"],
             "focus": "on-demand", "search": False, "pins": False,
             "close_on_output_removal": True},
            {"id": "calendar-popup", "trigger_widget": "clock",
             "native": "interactive-output-local", "waybar": "not-owned-by-riceplate",
             "input": ["pointer", "arrow-keys", "PageUp/PageDown", "Home", "Escape"],
             "date_source": "offline-local-clock", "events": False,
             "localized_month_labels": False, "close_on_output_removal": True,
             "focus": "on-demand-after-pointer"},
            {"id": "desktop-shortcut", "since_schema": 5,
             "recipe_pointer": "/desktop/icons", "native": "interactive-primary-output",
             "waybar": "not_available", "actions": sorted(ICON_ACTIONS),
             "input": ["pointer-click", "pointer-drag", "arrows-after-focus", "Enter/Space"],
             "focus": "pointer-or-compositor-focus", "keyboard_move_px": 16,
             "saved_positions": "private-per-rice", "hotplug_across_outputs": False,
             "arbitrary_commands": False},
        ],
        "layout_primitives": [
            {"id": "group", "native": "horizontal-layout", "waybar": "flattened-modules",
             "interactive": False},
            {"id": "gap", "native": "fixed-width", "waybar": "css-min-width",
             "interactive": False},
            {"id": "label", "native": "static-text", "waybar": "static-text",
             "interactive": False},
        ],
        "limits": [
            "Schema-v5 desktop icons are native-only; no Waybar icon layer yet",
            "Native icons can move and persist per rice but remain primary-output-only; no cross-output drag/hotplug lifecycle",
            "Desktop widgets are not implemented",
            "Native panel handles responsive compact layout live; Waybar requires width-specific generation",
            "Schema-v3 groups are horizontal panel-only; no full desktop composition yet",
            "Panel-only recipes; no arbitrary OS or screenshot conversion",
            "No runtime configurable action bindings or custom scripts",
            "Native battery widget is read-only and refreshes once per minute; no power controls or UPower event subscription",
            "Native panel still lacks tray and live network/audio hardware controls",
            "Native calendar has no events or locale-specific labels; clock cannot be reached from panel keyboard navigation",
            "Keyboard focus and assistive technology on real devices are not signed off",
            "Waybar CSS widths are minima; content can grow",
            "Available status indicators depend on host services and devices",
            "No active desktop configuration is read or changed",
        ],
    }


def validate_catalog_contract() -> None:
    """Protect the discoverability contract from drifting off the recipe parser."""
    result = describe()
    ids = [component["id"] for component in result["components"]]
    shell = {component["id"]: component for component in result["shell_components"]}
    metrics = tuple(result["recipe"]["metrics"]["fields"])
    if (len(ids) != len(set(ids)) or set(ids) != WIDGETS
            or metrics != METRIC_FIELDS
            or len(shell) != len(result["shell_components"])
            or set(shell) != {"native-menu", "calendar-popup", "desktop-shortcut"}
            or shell["native-menu"]["actions"] != sorted(MENU_ACTIONS)
            or shell["desktop-shortcut"]["actions"] != sorted(ICON_ACTIONS)):
        raise ValueError("RiceBowl component catalog is out of sync with panel recipes")
