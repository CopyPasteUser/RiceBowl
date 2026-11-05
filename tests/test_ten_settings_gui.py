"""Real GTK widget state for Windows 10 Settings (exercised under CI Xvfb)."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock


class TenSettingsGtkTests(unittest.TestCase):
    def test_home_search_detail_navigation_and_back(self):
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, GLib, Gtk

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("GTK display unavailable; native Xvfb CI supplies one")

        from macrice.ten_settings import TenSettings
        from macrice.ten_shell import CSS

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        def styled(widget, css_class):
            widget.get_style_context().add_class(css_class)
            return widget

        shell = SimpleNamespace(
            _class=styled,
            _desktop_rect=lambda: SimpleNamespace(x=0, y=0, width=1024, height=768),
            _error=Mock(), _open_tool=Mock(), _toggle_ten_network=Mock(),
        )
        runner = Mock()
        view = TenSettings(shell, Gtk, Gdk, GLib, runner)
        try:
            view.show()
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            self.assertEqual(view.current, "home")
            self.assertFalse(view.sidebar.get_visible())
            self.assertEqual(view.stack.get_visible_child_name(), "home")
            self.assertTrue(view.home_search.get_visible())
            adjustment = view.stack.get_child_by_name("home").get_vadjustment()
            self.assertLessEqual(adjustment.get_upper(), adjustment.get_page_size() + 3,
                                 "Category home must fit on a 1024×768 desktop")

            view.home_search.set_text("volume")
            self.assertEqual(view.current, "results")
            self.assertTrue(view.sidebar.get_visible())
            self.assertEqual(view.search.get_text(), "volume")
            self.assertTrue(view.results_box.get_children())
            # Search remains reachable after home is hidden.
            self.assertTrue(view.search.get_visible())

            view.results_box.get_children()[0].clicked()
            self.assertIn(view.current, ("sound", "system"))
            self.assertFalse(view.search.get_text())
            self.assertTrue(view._category_buttons["system"].get_style_context().has_class(
                "ten-settings-nav-selected"))

            view.navigate("sound")
            self.assertTrue(view._sliders["audio"].get_visible())
            self.assertTrue(view._switches["audio_mute"].get_visible())
            view._go_back()
            self.assertEqual(view.current, "system")
            view.navigate("home")
            self.assertFalse(view.sidebar.get_visible())
            view.home_search.set_text("doesnotexist_012345")
            self.assertEqual(view.current, "results")
            self.assertTrue(view.no_results.get_visible())
            view.search.set_text("")
            self.assertEqual(view.current, "home")
            self.assertFalse(view.sidebar.get_visible())
        finally:
            view.close()
            Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), provider)


if __name__ == "__main__":
    unittest.main()
