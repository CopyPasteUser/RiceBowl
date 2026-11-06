"""Deterministic, read-only reviews of the implemented panel recipe schema.

Creator agents can inspect a recipe and compare it to a known-good base before
asking a human to start a nested preview. No untrusted fields are executed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from . import catalog, recipes

REVIEW_VERSION = 1


def _manifest(recipe: recipes.PanelRecipe) -> dict[str, Any]:
    """Stable semantic representation, independent of JSON whitespace/order."""
    panel: dict[str, Any] = {
        "position": recipe.position,
        "height": recipe.height,
        "sections": dict(zip(recipes.SECTIONS, (list(part) for part in recipe.sections))),
    }
    if recipe.metrics is not None:
        panel["metrics"] = dict(zip(recipes.METRIC_FIELDS, recipe.metrics))
    return {
        "schema_version": 2 if recipe.metrics is not None else 1,
        "id": recipe.recipe_id,
        "name": recipe.name,
        "panel": panel,
        "colors": dict(zip(recipes.COLORS, recipe.colors)),
    }


def _semantic_hash(manifest: dict[str, Any]) -> str:
    payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _fields(manifest: dict[str, Any]) -> dict[str, Any]:
    """Small, fixed vocabulary of reviewable JSON Pointer paths."""
    panel = manifest["panel"]
    result = {
        "/schema_version": manifest["schema_version"],
        "/id": manifest["id"],
        "/name": manifest["name"],
        "/panel/position": panel["position"],
        "/panel/height": panel["height"],
    }
    for section in recipes.SECTIONS:
        result[f"/panel/sections/{section}"] = panel["sections"][section]
    for field in recipes.METRIC_FIELDS:
        # An absent v1 metric differs from a v2 metric at its default.
        result[f"/panel/metrics/{field}"] = panel.get("metrics", {}).get(field)
    for color in recipes.COLORS:
        result[f"/colors/{color}"] = manifest["colors"][color]
    return result


def _snapshot(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _manifest(recipes.load(token))
    component_support = {item["id"]: item for item in catalog.describe()["components"]}
    ordered = [widget for section in recipes.SECTIONS
               for widget in manifest["panel"]["sections"][section]]
    unavailable = [widget for widget in ordered
                   if component_support[widget]["native"] == "unavailable"]
    summary = {
        "id": manifest["id"],
        "schema_version": manifest["schema_version"],
        "semantic_sha256": _semantic_hash(manifest),
        "widgets": ordered,
        "native_unavailable_widgets": unavailable,
        "native_panel_complete": False,
        "requires_waybar_fallback_for_all_widgets": bool(unavailable),
    }
    return manifest, summary


def review(recipe_token: str, compare_token: str | None = None) -> dict[str, Any]:
    """Validate a source/base and report semantic changes without side effects."""
    catalog.validate_catalog_contract()
    target, target_summary = _snapshot(recipe_token)
    result: dict[str, Any] = {
        "review_version": REVIEW_VERSION,
        "scope": "wayland-panel-preview",
        "ok": True,
        "applied": False,
        "recipe": target,
        "summary": target_summary,
        "comparison": None,
    }
    if compare_token is not None:
        base, base_summary = _snapshot(compare_token)
        old_fields = _fields(base)
        new_fields = _fields(target)
        changes = [{"path": key, "before": old_fields[key], "after": new_fields[key]}
                   for key in old_fields if old_fields[key] != new_fields[key]]
        result["comparison"] = {
            "base_id": base["id"],
            "base_semantic_sha256": base_summary["semantic_sha256"],
            "changed": bool(changes),
            "changes": changes,
        }
    return result


def invalid_review() -> dict[str, Any]:
    """Stable, path-free machine response for inaccessible/invalid recipes."""
    return {
        "review_version": REVIEW_VERSION,
        "scope": "wayland-panel-preview",
        "ok": False,
        "applied": False,
        "error": {"code": "invalid_recipe", "message": "Invalid or unsafe panel recipe input"},
    }
