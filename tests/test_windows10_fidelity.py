"""Windows 10 native shell fidelity, live targets and safe upgrades."""
from __future__ import annotations

import json
import unittest
from xml.etree import ElementTree

from PIL import Image

from macrice.asset_upgrade import git_blob_sha, trusted_assets
from macrice.installer import project_root
from macrice.ten_action_center import QUICK_ACTIONS
from macrice.ten_shell import CSS, start_tiles


ROOT = project_root()


class App:
    def __init__(self, name: str, identifier: str):
        self.name = name
        self.identifier = identifier

    def get_id(self):
        return self.identifier

    def get_display_name(self):
        return self.name

    def get_name(self):
        return self.name


class Windows10FidelityTests(unittest.TestCase):
    def test_start_tiles_are_genuine_deduplicated_apps_and_respect_pins(self):
        apps = (App("Calculator", "calc.desktop"), App("Text Editor", "edit.desktop"),
                App("File Manager", "files.desktop"), App("Web Browser", "web.desktop"),
                App("Terminal", "term.desktop"), App("Settings", "settings.desktop"),
                App("Music", "music.desktop"))
        selection = start_tiles(apps, ("web.desktop", "web.desktop", "unknown.desktop"))
        self.assertEqual(selection[0].get_id(), "web.desktop")
        self.assertEqual(len(selection), 6)
        self.assertEqual(len({app.get_id() for app in selection}), 6)
        self.assertTrue(all(app in apps for app in selection))
        self.assertEqual(start_tiles((), ("missing.desktop",)), ())

    def test_blue_four_pane_wallpaper_and_independent_midnight(self):
        blue = ROOT / "assets/wallpapers/ten-blue.jpg"
        night = ROOT / "assets/wallpapers/ten-midnight.jpg"
        for path in (blue, night):
            with Image.open(path) as image:
                self.assertEqual(image.size, (1920, 1080))
                self.assertEqual(image.format, "JPEG")
                sky = image.getpixel((300, 400))
                pane = image.getpixel((1270, 410))
                self.assertGreater(pane[1], sky[1] + 50)
                self.assertGreater(pane[2], sky[2] + 50)
        self.assertNotEqual(blue.read_bytes(), night.read_bytes())

    def test_start_logo_is_original_flat_four_pane_linux_glyph(self):
        mark = (ROOT / "assets/ten-start.svg").read_bytes()
        ElementTree.fromstring(mark)
        self.assertIn(b"RiceBowl Ten Penguin", mark)
        self.assertIn(b"four-panel", mark)
        icon_root = ROOT / "assets/icons/RiceHub-Ten-Penguin/scalable/apps"
        for name in ("start-here", "xfce4-menu", "ricehub-ten"):
            self.assertEqual((icon_root / (name + ".svg")).read_bytes(), mark)

    def test_windows10_design_is_isolated_and_actions_are_real(self):
        for selector in (b".ten-rail-button", b".ten-letter", b".ten-tiles-panel",
                         b".ten-action-notifications", b".ten-action-bottom",
                         b".ten-mute:checked", b"@define-color ten-blue #0078d7"):
            self.assertIn(selector, CSS)
        shell = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertIn('"windows10": (690, 560)', shell)
        self.assertIn('self._populate_windows10(query)', shell)
        self.assertIn('self._render_ten_tiles()', shell)
        self.assertIn("from .ten_action_center import build", shell)
        self.assertIn("if profile in (\"chromeos\", \"aero\", \"windows10\")", shell)
        self.assertIn("self._toggle_actions()", shell)
        for _name, _icon, executable in QUICK_ACTIONS:
            self.assertIn(executable, shell)
        action_code = (ROOT / "macrice/ten_action_center.py").read_text(encoding="utf-8")
        self.assertIn("set_sensitive(available)", action_code)
        self.assertIn("Other desktop notifications", action_code)
        self.assertIn("Gtk.Scale.new_with_range", action_code)

    def test_win10_chrome_and_thunar_are_square_and_light_dark_distinct(self):
        for variant in ("Dark", "Light"):
            frame = ROOT / "assets/themes" / f"RiceHub-Ten-{variant}" / "xfwm4"
            style = frame.parent / "gtk-3.0/gtk.css"
            stylesheet = style.read_text(encoding="utf-8")
            for rule in ("placessidebar row", "treeview.view:selected",
                         "button:focus", "menuitem:hover"):
                self.assertIn(rule, stylesheet)
            for button in ("close", "maximize", "hide"):
                for state in ("active", "inactive", "prelight", "pressed"):
                    with Image.open(frame / f"{button}-{state}.png") as picture:
                        self.assertEqual(picture.size, (46, 31))
            with Image.open(frame / "close-prelight.png") as picture:
                self.assertEqual(picture.getpixel((2, 2))[:3], (232, 17, 35))
        self.assertNotEqual(
            (ROOT / "assets/themes/RiceHub-Ten-Dark/gtk-3.0/gtk.css").read_bytes(),
            (ROOT / "assets/themes/RiceHub-Ten-Light/gtk-3.0/gtk.css").read_bytes())

    def test_only_exact_previous_managed_assets_are_trusted(self):
        entries = json.loads((ROOT / "assets/trusted-ricebowl-ten-before-fidelity.json").read_text())
        self.assertEqual(entries["schema"], 1)
        previous = trusted_assets()
        for path in ("assets/themes/RiceHub-Ten-Dark/gtk-3.0/gtk.css",
                     "assets/themes/RiceHub-Ten-Light/xfwm4/close-prelight.png",
                     "assets/icons/RiceHub-Ten-Penguin/scalable/apps/start-here.svg"):
            self.assertIn(path, previous)
            self.assertEqual(len(entries["files"][path]), 1)
            self.assertNotIn(git_blob_sha((ROOT / path).read_bytes()), previous[path])


if __name__ == "__main__":
    unittest.main()
