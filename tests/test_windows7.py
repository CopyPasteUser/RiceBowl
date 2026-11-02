"""Windows 7 prototype remains a searchable, read-only visual preview."""

import unittest

from macrice.hub_catalog import FAMILY_BY_KEY
from macrice.windows7_proto import CSS, SAMPLE_APPS, matching_apps


class Windows7PrototypeTests(unittest.TestCase):
    def test_catalog_keeps_rice_unavailable(self):
        family = FAMILY_BY_KEY["windows7"]
        self.assertTrue(family.prototype)
        self.assertFalse(family.available)
        self.assertEqual(family.styles, ())

    def test_start_search_uses_only_sample_names(self):
        self.assertEqual(matching_apps(""), SAMPLE_APPS)
        self.assertEqual([name for name, _icon in matching_apps("FILE")], ["File Manager"])
        self.assertEqual([name for name, _icon in matching_apps("term")], ["Terminal"])
        self.assertEqual(matching_apps("nonexistent"), ())

    def test_gtk_styles_parse_without_cairo_conversion(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("PyGObject is unavailable")
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)


if __name__ == "__main__":
    unittest.main()
