"""Deterministic screenshot comparisons, never invented preview screenshots."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.compare_wayland_captures import compare, main


class WaylandVisualQaTests(unittest.TestCase):
    def test_identical_real_pngs_are_reported_as_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.png"
            Image.new("RGB", (32, 24), "#1357ab").save(path)
            result = compare(path, path)
            self.assertTrue(result["identical"])
            self.assertEqual(result["changed_pixel_ratio"], 0)
            self.assertEqual(result["size"], {"width": 32, "height": 24})
            self.assertEqual(result["perceptual_or_functional_accuracy"], "not_measured")

    def test_changes_are_measured_not_reported_as_fake_accuracy(self):
        with tempfile.TemporaryDirectory() as folder:
            reference = Path(folder) / "reference.png"
            actual = Path(folder) / "actual.png"
            Image.new("RGB", (10, 10), "#000000").save(reference)
            image = Image.new("RGB", (10, 10), "#000000")
            for x in range(5):
                for y in range(10):
                    image.putpixel((x, y), (255, 255, 255))
            image.save(actual)
            result = compare(reference, actual, threshold=24)
            self.assertEqual(result["changed_pixel_ratio"], .5)
            self.assertEqual(result["mean_absolute_rgb_error"], 127.5)
            self.assertFalse(result["identical"])

    def test_dimension_mismatch_and_corrupt_images_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder) / "a.png"
            b = Path(folder) / "b.png"
            Image.new("RGB", (10, 10)).save(a)
            Image.new("RGB", (11, 10)).save(b)
            with self.assertRaisesRegex(ValueError, "dimensions differ"):
                compare(a, b)
            b.write_text("not a screenshot")
            self.assertEqual(main([str(a), str(b)]), 2)
            with self.assertRaisesRegex(ValueError, "Threshold"):
                compare(a, a, threshold=256)


if __name__ == "__main__":
    unittest.main()
