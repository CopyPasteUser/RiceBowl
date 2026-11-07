"""Unit-test the inspector; real labwc/grim pixels are verified in native CI."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.check_wayland_menu_outputs import active_menu_output, menu_matches


class MenuOutputCheckTests(unittest.TestCase):
    def test_exactly_one_output_owns_the_menu(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory, f"{index}.png") for index in range(2)]

            def capture(active):
                for index, path in enumerate(paths):
                    image = Image.new("RGB", (1024, 768), (0x20, 0x3C, 0x59))
                    if index == active:
                        image.putpixel((20, 50), (0x41, 0x79, 0xAA))
                    image.save(path)

            for active in (0, 1):
                capture(active)
                self.assertEqual(active_menu_output(paths), active)
            capture(None)
            self.assertEqual(menu_matches(paths), [])
            with self.assertRaisesRegex(ValueError, "found 0"):
                active_menu_output(paths)
            capture(0)
            with Image.open(paths[1]) as image:
                duplicate = image.copy()
            duplicate.putpixel((20, 50), (0x41, 0x79, 0xAA))
            duplicate.save(paths[1])
            with self.assertRaisesRegex(ValueError, "found 2"):
                active_menu_output(paths)


if __name__ == "__main__":
    unittest.main()
