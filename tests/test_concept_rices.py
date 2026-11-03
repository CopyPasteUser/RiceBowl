"""Legacy read-only concept dialogs remain separate from installable rices."""

import unittest

from macrice.concept_rices import CONCEPTS, CSS, search_apps
from macrice.hub_catalog import AVAILABLE_STYLE_KEYS, FAMILY_BY_KEY
from macrice.rice import STYLES


class ConceptTests(unittest.TestCase):
    def test_all_four_concepts_stay_read_only_even_when_styles_are_installable(self):
        self.assertEqual(set(CONCEPTS), {"winxp", "winclassic", "chromeos", "frutiger"})
        for key, concept in CONCEPTS.items():
            with self.subTest(key=key):
                family = FAMILY_BY_KEY[key]
                self.assertTrue(family.available)
                self.assertEqual(family.styles, (key,))
                self.assertTrue(concept.applications)
                self.assertIn(key, STYLES)
                self.assertIn(key, AVAILABLE_STYLE_KEYS)

    def test_search_is_sample_only_casefolded_and_has_empty_state(self):
        self.assertEqual([name for name, _ in search_apps("winxp", "TERMINAL")], ["Terminal"])
        self.assertEqual(search_apps("winclassic", "    "), CONCEPTS["winclassic"].applications)
        self.assertEqual(search_apps("chromeos", "not installed here"), ())
        with self.assertRaises(KeyError):
            search_apps("nonexistent", "")

    def test_concept_wallpapers_match_their_own_rice_not_windows_seven(self):
        for key in ("winxp", "frutiger"):
            with self.subTest(key=key):
                self.assertEqual(CONCEPTS[key].wallpaper, STYLES[key].wallpaper)
                self.assertNotIn(CONCEPTS[key].wallpaper, (
                    STYLES["aero-meadow"].wallpaper,
                    STYLES["aero-cascade"].wallpaper,
                ))

    def test_gtk_css_is_parsable_without_starting_desktop(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("PyGObject not available")
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)


if __name__ == "__main__":
    unittest.main()
