"""Aero rice tests run entirely against a simulated XFCE backend and temp homes."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.aero import (AeroAssetError, autostart_file, preflight, read_autostart)
from macrice.aero_shell import CSS, app_catalog, matching_apps
from macrice.installer import project_root
from macrice.rice import RiceError, STYLES, apply, plan, restore
from tests.test_rice import FakeBackend, setup_apps


class AeroTests(unittest.TestCase):
    def test_both_original_aero_styles_have_all_required_assets(self):
        source = project_root()
        for key in ("aero-meadow", "aero-cascade"):
            self.assertTrue((source / "assets/wallpapers" / STYLES[key].wallpaper).is_file())
            self.assertEqual(STYLES[key].gtk, "RiceHub-Aero")
            self.assertEqual(STYLES[key].icon_theme, "RiceHub-Aero")
        chrome = source / "assets/themes/RiceHub-Aero/xfwm4"
        for state in ("active", "inactive"):
            for part in ("top-left", "top-right", "title-1", "title-5", "bottom", "left", "right"):
                self.assertTrue((chrome / f"{part}-{state}.png").is_file())
        for button in ("close", "maximize", "hide"):
            for state in ("active", "inactive", "prelight", "pressed"):
                self.assertTrue((chrome / f"{button}-{state}.png").is_file())

    def test_aero_plan_is_read_only_and_enables_original_artwork(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            changes, _previous, _, target = plan("aero-meadow", backend=fake,
                                                  data_root=root / "data", config_root=root / "config")
            converted = {entry["key"]: entry["after"] for entry in changes}
            self.assertEqual(converted["/Net/ThemeName"], "RiceHub-Aero")
            self.assertEqual(converted["/general/theme"], "RiceHub-Aero")
            self.assertEqual(converted["/Net/IconThemeName"], "RiceHub-Aero")
            self.assertEqual(converted["/Gtk/CursorThemeName"], "Adwaita")
            self.assertEqual(converted["icon-size"], "48")
            self.assertEqual(converted["alignment"], "'center'")
            self.assertEqual(converted["position"], "'left'")
            self.assertEqual(converted["hide-mode"], "'auto'")
            # The stable selection key is still aero-meadow; the user-facing
            # style name now yields the new managed wallpaper target prefix.
            self.assertTrue(target.name.startswith("aero-seven-blue-"))
            self.assertFalse((root / "data").exists())
            self.assertEqual(fake.calls, [])

    def test_apply_and_restore_own_assets_and_autostart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            original = fake.values.copy()
            backup = apply("aero-cascade", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.get("xfconf", "xsettings", "/Net/IconThemeName"), "RiceHub-Aero")
            self.assertTrue((root / "data/themes/RiceHub-Aero/gtk-3.0/gtk.css").is_file())
            self.assertTrue((root / "data/themes/RiceHub-Aero/xfwm4/close-active.png").is_file())
            self.assertTrue((root / "data/icons/RiceHub-Aero/scalable/apps/start-here.svg").is_file())
            self.assertTrue((root / "data/plank/themes/RiceHub-Aero-Glass/dock.theme").is_file())
            self.assertIn("aero-shell", read_autostart(root / "config"))
            self.assertEqual(json.loads((backup / "manifest.json").read_text())["schema"], 5)
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), backup)
            self.assertEqual(fake.values, original)
            self.assertFalse(autostart_file(root / "config").exists())
            # Shared user-local theme assets remain for a later switch; original desktop selection is restored.
            self.assertTrue((root / "data/themes/RiceHub-Aero/gtk-3.0/gtk.css").exists())

    def test_existing_user_modified_theme_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "data/themes/RiceHub-Aero/gtk-3.0/gtk.css"
            target.parent.mkdir(parents=True)
            target.write_text("user changed my theme")
            with self.assertRaisesRegex(AeroAssetError, "conflicts"):
                preflight(project_root(), root / "data")
            self.assertEqual(target.read_text(), "user changed my theme")

    def test_user_modified_autostart_blocks_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = autostart_file(root / "config")
            target.parent.mkdir(parents=True)
            target.write_text("[Desktop Entry]\nExec=someone-elses-app\n")
            fake = FakeBackend()
            setup_apps(root / "config")
            with self.assertRaisesRegex(RiceError, "not managed"):
                apply("aero-meadow", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.calls, [])

    def test_icon_theme_and_aero_shell_css_parse(self):
        try:
            import gi
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("GTK3 unavailable")
        for contents in (CSS, (project_root() / "assets/themes/RiceHub-Aero/gtk-3.0/gtk.css").read_bytes()):
            provider = Gtk.CssProvider()
            provider.load_from_data(contents)

    def test_start_search_is_case_insensitive_and_unpaginated(self):
        class App:
            def __init__(self, name):
                self.name = name
            def get_display_name(self):
                return self.name
            def get_name(self):
                return self.name
        apps = tuple(App("Browser " + str(i)) for i in range(100))
        self.assertEqual(len(matching_apps(apps, "BROWSER")), 100)
        self.assertEqual([a.name for a in matching_apps(apps, "browser 9")],
                         ["Browser 9", "Browser 90", "Browser 91", "Browser 92",
                          "Browser 93", "Browser 94", "Browser 95", "Browser 96",
                          "Browser 97", "Browser 98", "Browser 99"])

    def test_program_catalog_filters_hidden_apps_and_deduplicates_names(self):
        class App:
            def __init__(self, name, visible):
                self.name, self.visible = name, visible
            def should_show(self):
                return self.visible
            def get_display_name(self):
                return self.name
        fake_gio = mock.Mock()
        fake_gio.AppInfo.get_all.return_value = [App("Browser", True), App("browser", True), App("Hidden", False)]
        self.assertEqual([app.get_display_name() for app in app_catalog(fake_gio)], ["Browser"])


if __name__ == "__main__":
    unittest.main()
