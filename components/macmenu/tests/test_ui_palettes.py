"""GTK3 parses every theme without requiring a graphical session."""

import unittest

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    from macmenu.ui import PALETTES, STYLESHEET, THEMES
except (ImportError, ValueError):
    Gtk = None


@unittest.skipIf(Gtk is None, "PyGObject GTK3 is not installed")
class GtkPaletteTests(unittest.TestCase):
    def test_every_theme_is_supported_and_parses(self):
        self.assertEqual({name for name, _ in THEMES} - {"system"}, set(PALETTES))
        for name, palette in PALETTES.items():
            with self.subTest(theme=name):
                provider = Gtk.CssProvider()
                errors = []
                provider.connect("parsing-error", lambda _provider, _section, error: errors.append(error.message))
                provider.load_from_data(STYLESHEET.format(**palette).encode())
                self.assertFalse(errors, errors)


if __name__ == "__main__":
    unittest.main()
