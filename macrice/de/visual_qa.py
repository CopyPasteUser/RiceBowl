"""Offline, bounded PNG comparison shared by Runtime tools and the Creator CLI.

Visual metrics do not measure function, perception or interaction fidelity.
Pillow is an optional dependency loaded only when explicitly comparing images.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import recipes, review


def _metrics(diff, *, threshold: int) -> dict:
    """Measure an RGB difference image; scores never imply UI functionality."""
    width, height = diff.size
    histogram = diff.histogram()
    error_sum = sum((index % 256) * count for index, count in enumerate(histogram))
    pixels = (diff.get_flattened_data() if hasattr(diff, "get_flattened_data")
              else diff.getdata())
    changed = sum(1 for rgb in pixels if max(rgb) > threshold)
    return {
        "mean_absolute_rgb_error": round(error_sum / (width * height * 3), 4),
        "changed_pixel_ratio": round(changed / (width * height), 6),
        "identical": error_sum == 0,
    }


def _recipe_regions(diff, recipe_token: str, threshold: int) -> dict:
    """Inspect real pixels occupied by the declared shell; never infer fidelity."""
    try:
        recipe = recipes.load(recipe_token)
    except recipes.RecipeError as exc:
        raise ValueError("Invalid or unsafe recipe") from exc
    width, height = diff.size
    panel_y = 0 if recipe.position == "top" else height - recipe.height
    regions = [
        ("panel", (0, panel_y, width, panel_y + recipe.height)),
        ("desktop", (0, recipe.height if recipe.position == "top" else 0,
                     width, height if recipe.position == "top" else panel_y)),
    ]
    if recipe.height >= height:
        raise ValueError("Capture too small for recipe panel")
    issues = []
    for number, icon in enumerate(recipe.desktop_icons or (), start=1):
        box = (icon.x, icon.y, icon.x + recipes.ICON_WIDTH,
               icon.y + recipes.ICON_HEIGHT)
        regions.append((f"desktop-icon-{number}", box))
    results = []
    for name, box in regions:
        x1, y1, x2, y2 = box
        clipped = (max(0, x1), max(0, y1), min(width, x2), min(height, y2))
        visible_width = max(0, clipped[2] - clipped[0])
        visible_height = max(0, clipped[3] - clipped[1])
        fraction = round((visible_width * visible_height) /
                         ((x2 - x1) * (y2 - y1)), 6)
        region = {"id": name, "expected_rect": {"x": x1, "y": y1,
                   "width": x2 - x1, "height": y2 - y1},
                  "visible_fraction": fraction}
        if visible_width and visible_height:
            region.update(_metrics(diff.crop(clipped), threshold=threshold))
        else:
            region["status"] = "outside_capture"
        if name.startswith("desktop-icon-"):
            if fraction < 1:
                issues.append({"region": name, "code": "icon_outside_output"})
            if (visible_width and visible_height and
                    clipped[1] < panel_y + recipe.height and clipped[3] > panel_y):
                issues.append({"region": name, "code": "icon_overlaps_panel"})
        results.append(region)
    manifest = review._manifest(recipe)
    return {"recipe": {"id": recipe.recipe_id,
                       "schema_version": recipe.schema_version,
                       "semantic_sha256": review._semantic_hash(manifest)},
            "regions": results, "layout_issues": issues}


def _save_private_png(image, path: Path) -> None:
    """Write once (0600), refusing existing files or symlinks."""
    if not path.is_absolute() or path.suffix.lower() != ".png":
        raise ValueError("Diagnostic output must be a new absolute .png path")
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise ValueError("Diagnostic output exists or cannot be created") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            image.save(stream, format="PNG")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def compare(reference: Path, actual: Path, *, threshold: int = 24,
            recipe_token: str | None = None, overlay: Path | None = None,
            heatmap: Path | None = None) -> dict:
    """Compare captures without modifying them; optional diagnostics are new files."""
    try:
        from PIL import Image, ImageChops, UnidentifiedImageError
    except ImportError as exc:
        raise ValueError("Optional Pillow package is required for image comparison") from exc

    if not 0 <= threshold <= 255:
        raise ValueError("Threshold must be between 0 and 255")
    outputs = [path for path in (overlay, heatmap) if path is not None]
    if (len({str(path.resolve()) for path in outputs}) != len(outputs)
            or any(not path.is_absolute() or path.suffix.lower() != ".png"
                   for path in outputs)):
        raise ValueError("Diagnostic outputs must be distinct absolute .png paths")
    try:
        if any(path.stat().st_size > 64 * 1024 * 1024 for path in (reference, actual)):
            raise ValueError("Capture exceeds the 64 MiB offline comparison limit")
    except OSError as exc:
        raise ValueError("Capture file is unavailable") from exc
    try:
        with Image.open(reference) as original, Image.open(actual) as captured:
            if original.format != "PNG" or captured.format != "PNG":
                raise ValueError("Only unmodified PNG captures are supported")
            if original.size != captured.size:
                raise ValueError("Capture dimensions differ")
            if not 1 <= original.width <= 8192 or not 1 <= original.height <= 8192:
                raise ValueError("Capture dimensions are outside the safe range")
            if original.width * original.height > 16_777_216:
                raise ValueError("Capture exceeds the safe 16-megapixel comparison limit")
            before, after = original.convert("RGB"), captured.convert("RGB")
            diff = ImageChops.difference(before, after)
            result = {
                "comparison_version": 2 if recipe_token else 1,
                "size": {"width": original.width, "height": original.height},
                "pixel_threshold": threshold,
                **_metrics(diff, threshold=threshold),
                "perceptual_or_functional_accuracy": "not_measured",
            }
            if recipe_token:
                result.update(_recipe_regions(diff, recipe_token, threshold))
            written: list[Path] = []
            try:
                if overlay is not None:
                    _save_private_png(Image.blend(before, after, 0.5), overlay)
                    written.append(overlay)
                if heatmap is not None:
                    red, green, blue = diff.split()
                    intensity = ImageChops.lighter(ImageChops.lighter(red, green), blue)
                    intensity = intensity.point(lambda value: min(value * 4, 255))
                    empty = Image.new("L", diff.size, 0)
                    _save_private_png(Image.merge("RGB", (intensity, empty, empty)), heatmap)
                    written.append(heatmap)
            except Exception:
                for path in written:
                    path.unlink(missing_ok=True)
                raise
            if overlay is not None:
                result["overlay"] = str(overlay)
            if heatmap is not None:
                result["heatmap"] = str(heatmap)
            return result
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("Capture could not be decoded as a readable PNG") from exc
