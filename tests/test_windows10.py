"""Windows 10 live rice and separate read-only concept contracts."""

import unittest
from pathlib import Path
from xml.etree import ElementTree

from macrice.hub_catalog import FAMILY_BY_KEY
from macrice.windows10_proto import CSS, SAMPLE_APPS, matching_apps


class Windows10PrototypeTests(unittest.TestCase):
    def test_search_is_case_insensitive_and_empty_search_shows_all(self):
        self.assertEqual(matching_apps(""), SAMPLE_APPS)
        self.assertEqual(matching_apps("  broWSER  "), (SAMPLE_APPS[1],))
        self.assertEqual(matching_apps("not-installed"), ())

    def test_profile_has_installable_styles_and_separate_preview(self):
        profile = FAMILY_BY_KEY["windows10"]
        self.assertTrue(profile.prototype)
        self.assertTrue(profile.available)
        self.assertEqual(profile.styles, ("ten-dark", "ten-light"))

    def test_gtk_css_and_original_wallpaper_are_present(self):
        self.assertIn(b"w10-taskbar", CSS)
        self.assertIn(b"w10-action-center", CSS)
        wallpaper = Path(__file__).resolve().parents[1] / "assets/windows10-bloom.svg"
        root = ElementTree.parse(wallpaper).getroot()
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")


if __name__ == "__main__":
    unittest.main()
