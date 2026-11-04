"""Centered Win98 Control Panel must be validated where XFWM renders it."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw
from screenshots.validate_gallery import changed_area


class Classic98GalleryRegionTests(unittest.TestCase):
    def test_classic98_centered_panel_changes_checked_area(self):
        with tempfile.TemporaryDirectory() as directory:
            start, controls = Path(directory) / "start.png", Path(directory) / "controls.png"
            first = Image.new("RGB", (1600, 900), (0, 128, 128))
            first.save(start)
            second = first.copy()
            ImageDraw.Draw(second).rectangle((490, 225, 1110, 710), fill=(192, 192, 192))
            second.save(controls)
            changed, area = changed_area(start, controls, "winclassic")
            self.assertGreater(changed, 32000)
            self.assertGreater(area, 350000)


if __name__ == "__main__":
    unittest.main()
