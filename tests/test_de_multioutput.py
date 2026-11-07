"""Pixel validator used after real two-output headless Waybar captures."""

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scripts.check_wayland_panel_outputs import validate


class MultioutputCaptureChecks(unittest.TestCase):
    def test_both_screens_must_have_a_real_classic_panel_colored_edge(self):
        with tempfile.TemporaryDirectory() as directory:
            sources = []
            for index in range(2):
                path = Path(directory) / f"output-{index}.png"
                image = Image.new("RGB", (640, 480), (15, 22, 28))
                for y in range(444, 480):
                    for x in range(640):
                        image.putpixel((x, y), (32, 60, 89))
                image.save(path)
                sources.append(path)
            validate(sources)
            Image.new("RGB", (640, 480), (15, 22, 28)).save(sources[1])
            with self.assertRaisesRegex(ValueError, "No classic RiceBowl panel"):
                validate(sources)

    def test_invalid_geometry_and_input_count_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "too-small.png"
            Image.new("RGB", (240, 200), (32, 60, 89)).save(image)
            with self.assertRaises(ValueError):
                validate([image])
            with self.assertRaises(ValueError):
                validate([])
            with self.assertRaises(ValueError):
                validate([image, image, image])


if __name__ == "__main__":
    unittest.main()
