#!/usr/bin/env python3
"""Check real schema-v5 desktop shortcut pixels on each labwc output.

The first shortcut sits at (32, 96), with an opaque, original #4179aa glyph
backplate at (56..112, 100..148). A screen without a rendered native icon
must not pass just because its panel was visible.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def validate(paths: list[Path]) -> None:
    if not 1 <= len(paths) <= 2:
        raise ValueError("Expected one or two genuine output captures")
    for path in paths:
        with Image.open(path) as image:
            if image.format != "PNG" or image.width < 480 or image.height < 480:
                raise ValueError("Invalid native desktop PNG")
            sample = image.convert("RGB").getpixel((66, 110))
        if any(abs(channel - target) > 3 for channel, target in
               zip(sample, (0x41, 0x79, 0xAA))):
            raise ValueError(f"Missing native desktop icon on {path.name}: {sample}")


if __name__ == "__main__":
    validate([Path(value) for value in sys.argv[1:]])
    print("Verified original native desktop icons on compositor outputs")
