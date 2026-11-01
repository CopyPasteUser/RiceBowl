"""Native GTK performance, tile-reuse and single-layout smoke test on XFCE/X11."""

from time import perf_counter
from unittest.mock import patch

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from macmenu.config import sanitize
from macmenu.model import AppEntry
from macmenu.ui import LauncherWindow


def main() -> int:
    application = Gtk.Application(application_id="io.github.xfce.MacMenuSmoke")
    assert application.register(), "GTK application registration failed"
    entries = [AppEntry(f"fake-{i:03}.desktop", f"App {i:03}", "Test", "Utilities") for i in range(515)]
    with patch("macmenu.ui.installed_apps", return_value=entries), patch("macmenu.ui.load", return_value=sanitize({})):
        window = LauncherWindow(application)
    try:
        window.show_launcher()
        assert len(window.grid.get_children()) == 30
        assert len(window._tile_pool) == 30
        assert window.mac_rail.get_visible()
        assert len(window.mac_rail.get_children()) == 1, "Only the category scroller belongs in the rail"
        assert window.brand_image.get_pixbuf() is not None
        assert window.get_icon() is not None
        assert window.brand_image.get_pixbuf().get_width() == 26
        original_brand = window.brand_image.get_pixbuf()
        window.settings["theme"] = "light"
        window.apply_theme()
        assert window.brand_image.get_pixbuf() is not original_brand
        window.settings["theme"] = "dark"
        window.apply_theme()
        assert window.brand_image.get_pixbuf() is original_brand
        assert "All Apps" in window.rail_buttons
        assert window.more_button.get_visible()
        assert window.stack.get_visible_child_name() == "apps"

        first_tile = window._tile_pool[0]
        first_icon = first_tile.tile_icon
        for _ in range(10):
            window.render()
        assert window._tile_pool[0] is first_tile
        assert window._tile_pool[0].tile_icon is first_icon

        window.show_more(None)
        assert len(window._tile_pool) == 60
        assert sum(child.get_visible() for child in window._tile_pool) == 60
        window.show_more(None)
        assert len(window._tile_pool) == 90

        start = perf_counter()
        for index in range(50):
            window.search.set_text(f"App {index:03}")
            window.render()
        elapsed = (perf_counter() - start) * 1000
        assert len(window._tile_pool) == 60, "Search must recycle at most two pages of tiles"
        assert sum(child.get_visible() for child in window._tile_pool) == 1
        assert not window.more_button.get_visible()
        assert len(window._tile_pool) == 60, "Search should shed excess cached tiles"

        window.select_category("Favorites")
        assert window.category == "Favorites"
        assert window.rail_buttons["Favorites"].get_style_context().has_class("selected")
        header = window.get_child().get_children()[0]
        menu_button = header.get_children()[-1]
        window.show_system_menu(menu_button)
        menus = Gtk.Menu.get_for_attach_widget(window)
        assert len(menus) == 1
        labels = [child.get_label() for child in menus[0].get_children() if isinstance(child, Gtk.MenuItem)]
        assert not {"Lock Screen", "Switch User", "Log Out…"}.intersection(labels)
        assert "Preferences…" in labels and "Open Files" in labels
        menus[0].popdown()
        print(f"GUI smoke: 515 apps; 30-tile initial cap; 50 recycled searches in {elapsed:.1f} ms")
    finally:
        window.destroy()

    with patch("macmenu.ui.installed_apps", return_value=entries[:32]), patch("macmenu.ui.load", return_value=sanitize({})):
        small = LauncherWindow(application)
    try:
        small.show_launcher()
        assert len(small._tile_pool) == 32
        assert not small.more_button.get_visible()
        small.dismiss()
        small.show_launcher()
        assert len(small._tile_pool) == 32
        print("GUI smoke: 32 apps shown without paging; reopen reuses widgets")
    finally:
        small.destroy()

    application.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
