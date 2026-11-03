"""Current desktop previews fit without cairo.Context or WebP loaders."""

import unittest
from pathlib import Path

from macrice.hub_art import PREVIEW_FILES, aspect_contain, aspect_fill


class PreviewArtTests(unittest.TestCase):
    def test_aspect_fill_preserves_exact_allocation(self):
        try:
            import gi
            gi.require_version("GdkPixbuf", "2.0")
            from gi.repository import GdkPixbuf
        except (ImportError, ValueError):
            self.skipTest("PyGObject not installed")
        original = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 500, 200)
        original.fill(0x344a67ff)
        for width, height in ((640, 190), (320, 190), (900, 180), (110, 400)):
            result = aspect_fill(original, width, height, GdkPixbuf.InterpType.BILINEAR)
            self.assertEqual((result.get_width(), result.get_height()), (width, height))
        for size in ((0, 10), (40, -1)):
            with self.assertRaises(ValueError):
                aspect_fill(original, *size, GdkPixbuf.InterpType.BILINEAR)

    def test_captured_desktops_are_shipped_in_gtk_compatible_format(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(len(PREVIEW_FILES), 6)
        for name in PREVIEW_FILES.values():
            path = root / "assets/hub-previews" / name
            self.assertTrue(path.is_file(), name)
            self.assertGreater(path.stat().st_size, 10_000)
            self.assertEqual(path.suffix, ".jpg")

    def test_aspect_contain_does_not_crop_desktop_controls(self):
        try:
            import gi
            gi.require_version("GdkPixbuf", "2.0")
            from gi.repository import GdkPixbuf
        except (ImportError, ValueError):
            self.skipTest("PyGObject not installed")
        source = Path(__file__).resolve().parents[1] / "assets/hub-previews/frutiger.jpg"
        image = GdkPixbuf.Pixbuf.new_from_file(str(source))
        for width, height in ((640, 245), (310, 245), (940, 470)):
            fitted = aspect_contain(image, width, height, GdkPixbuf.InterpType.BILINEAR)
            self.assertLessEqual(fitted.get_width(), width)
            self.assertLessEqual(fitted.get_height(), height)
            self.assertAlmostEqual(fitted.get_width() / fitted.get_height(),
                                   image.get_width() / image.get_height(), delta=0.015)
        with self.assertRaises(ValueError):
            aspect_contain(image, 0, 500, GdkPixbuf.InterpType.BILINEAR)


if __name__ == "__main__":
    unittest.main()
