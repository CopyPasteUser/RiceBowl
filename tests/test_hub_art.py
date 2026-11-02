"""Pixels used in the native gallery can be sized without cairo.Context."""

import unittest

from macrice.hub_art import aspect_fill


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


if __name__ == "__main__":
    unittest.main()
