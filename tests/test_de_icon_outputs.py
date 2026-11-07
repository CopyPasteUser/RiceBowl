"""Regression tests for real multi-output desktop icon screenshot checks."""

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts.check_wayland_icon_outputs import validate


class NativeIconOutputChecks(unittest.TestCase):
    def test_every_output_requires_opaque_icon_backplate(self):
        with tempfile.TemporaryDirectory() as root:
            paths = []
            for index in range(2):
                path = Path(root) / f"output-{index}.png"
                image = Image.new("RGB", (640, 480), (10, 20, 30))
                image.putpixel((66, 110), (65, 121, 170))
                image.save(path)
                paths.append(path)
            validate(paths)
            Image.new("RGB", (640, 480)).save(paths[1])
            with self.assertRaisesRegex(ValueError, "Missing native desktop icon"):
                validate(paths)

    def test_empty_and_non_png_fail(self):
        with self.assertRaises(ValueError):
            validate([])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "output.jpg"
            Image.new("RGB", (640, 480)).save(path)
            with self.assertRaises(ValueError):
                validate([path])


if __name__ == "__main__":
    unittest.main()
