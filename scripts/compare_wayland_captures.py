#!/usr/bin/env python3
"""Offline, pixel-based diagnostics for REAL captured Wayland shell screenshots.

Not a perceptual fidelity score: font rendering, wallpaper and clock changes
affect the metrics. A visual/functional review is still required before 1.0.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def compare(reference: Path, actual: Path, *, threshold: int = 24) -> dict:
    """Return stable, transparent per-pixel metrics without writing either image."""
    from PIL import Image, ImageChops, UnidentifiedImageError

    if not 0 <= threshold <= 255:
        raise ValueError("Threshold must be between 0 and 255")
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
            diff = ImageChops.difference(original.convert("RGB"), captured.convert("RGB"))
            total = original.width * original.height
            histogram = diff.histogram()
            error_sum = sum((index % 256) * count
                            for index, count in enumerate(histogram))
            changed = sum(1 for red, green, blue in diff.getdata()
                          if max(red, green, blue) > threshold)
            return {
                "comparison_version": 1,
                "size": {"width": original.width, "height": original.height},
                "pixel_threshold": threshold,
                "mean_absolute_rgb_error": round(error_sum / (total * 3), 4),
                "changed_pixel_ratio": round(changed / total, 6),
                "identical": error_sum == 0,
                "perceptual_or_functional_accuracy": "not_measured",
            }
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError("Capture could not be decoded as a readable PNG") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--threshold", type=int, default=24)
    args = parser.parse_args(argv)
    try:
        result = {"ok": True, **compare(args.reference, args.actual,
                                          threshold=args.threshold)}
    except ValueError as exc:
        result = {"ok": False, "error": {"code": "invalid_capture", "message": str(exc)}}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
