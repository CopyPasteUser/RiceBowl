"""Brand assets stay portable, accessible and genuinely monochrome."""

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"
SVG = "{http://www.w3.org/2000/svg}"


class BrandTests(unittest.TestCase):
    def test_svg_artwork_is_self_contained_and_monochrome(self):
        expected = {
            "macmenu-penguin.svg": {"#ffffff"},
            "macmenu-penguin-ink.svg": {"#1a2435"},
            "macmenu-app.svg": {"#ffffff", "#151b25"},
        }
        for name, colors in expected.items():
            with self.subTest(name=name):
                root = ET.parse(ASSETS / name).getroot()
                self.assertEqual(root.tag, f"{SVG}svg")
                self.assertEqual(root.attrib.get("viewBox"), "0 0 128 128")
                self.assertTrue(root.find(f"{SVG}title") is not None)
                self.assertTrue(root.findall(f".//{SVG}path"))
                actual = {element.attrib["fill"] for element in root.iter() if "fill" in element.attrib}
                self.assertEqual(actual, colors)
                self.assertNotIn("http:", (ASSETS / name).read_text().replace("http://www.w3.org/2000/svg", ""))


if __name__ == "__main__":
    unittest.main()
