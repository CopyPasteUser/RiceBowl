"""Windows 7 Aero fidelity contracts without needing an X11 desktop."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from macrice.aero_layout import actual_popup_y, bottom_strut, menu_geometry, task_capacity
from macrice.aero_shell import CSS, win7_programs
from macrice.asset_upgrade import AssetConflict, git_blob_sha, inspect_bundle, trusted_assets
from macrice.installer import project_root
from macrice.rice import STYLES


class App:
    def __init__(self, identifier, title):
        self.identifier, self.title = identifier, title

    def get_id(self):
        return self.identifier

    def get_display_name(self):
        return self.title

    def get_name(self):
        return self.title


class Win7MenuTests(unittest.TestCase):
    def test_favorites_first_and_all_programs_are_real_and_stable(self):
        apps = (App("terminal.desktop", "Terminal"), App("browser.desktop", "Browser"),
                App("files.desktop", "Files"), App("editor.desktop", "Editor"))
        self.assertEqual(win7_programs(apps, ("files.desktop", "browser.desktop"), ""),
                         (apps[2], apps[1], apps[0], apps[3]))
        self.assertEqual(win7_programs(apps, ("files.desktop",), "", all_programs=True), apps)
        self.assertEqual(win7_programs(apps, (), "tERm"), (apps[0],))
        self.assertEqual(win7_programs(apps, ("missing.desktop",), "", limit=2), apps[:2])

    def test_42px_superbar_and_start_fit_low_resolution(self):
        for x, y, w, h in ((0, 0, 1600, 900), (0, 0, 1024, 768),
                            (1024, 80, 1024, 768), (-1280, 0, 1280, 800)):
            with self.subTest(monitor=(x, y, w, h)):
                mx, my, mw, mh = menu_geometry(x, y, w, h, preferred_width=525,
                                                preferred_height=535, panel_height=42)
                self.assertGreaterEqual(mx, x)
                self.assertGreaterEqual(my, y)
                self.assertLessEqual(mx + mw, x + w)
                self.assertEqual(my + mh, y + h - 42 - 8)
                self.assertEqual(actual_popup_y(y, h, mh, panel_height=42), my)
        self.assertEqual(bottom_strut(0, 0, 1024, 768, 768, panel_height=42)[0][-1], 42)
        self.assertGreater(task_capacity(1024, 3, 345, compact=True),
                           task_capacity(1024, 3, 345))
        self.assertEqual(task_capacity(320, 6, 345, compact=True), 0)

    def test_only_aero_has_superbar_and_menu_design_tokens(self):
        for name in (b"win7-taskbar", b"win7-start", b"win7-task", b"win7-menu-root",
                     b"win7-program", b"win7-side", b"win7-power"):
            self.assertIn(name, CSS)
        self.assertIn(b".aero-taskbar.win7-taskbar", CSS)


class Win7ArtworkTests(unittest.TestCase):
    def test_blue_aero_wallpapers_have_linux_identity_without_frutiger_reuse(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is only required for validating desktop artwork")
        root = project_root()
        wallpapers = []
        for key, name in (("aero-meadow", "Aero Seven Blue"),
                          ("aero-cascade", "Aero Seven Night")):
            with self.subTest(key=key):
                style = STYLES[key]
                self.assertEqual(style.name, name)
                self.assertTrue(style.wallpaper.startswith("aero-seven-"))
                source = root / "assets/wallpapers" / style.wallpaper
                with Image.open(source) as picture:
                    self.assertEqual(picture.format, "JPEG")
                    self.assertGreaterEqual(picture.width, 1600)
                    self.assertGreaterEqual(picture.height, 900)
                    # Original cobalt-blue Aero: keep green/nature palette
                    # for the entirely separate Frutiger Aero profile.
                    center = picture.getpixel((picture.width // 3, picture.height // 3))
                    self.assertGreater(center[2], center[1])
                    self.assertGreater(center[2], center[0])
                wallpapers.append(source.read_bytes())
        self.assertNotEqual(*wallpapers)

    def test_original_folders_are_valid_individual_svg_assets(self):
        source = project_root() / "assets/icons/RiceHub-Aero/scalable/places"
        icons = []
        for name in ("folder-documents", "folder-pictures", "folder-music", "folder-download"):
            path = source / (name + ".svg")
            icons.append(path.read_bytes())
            self.assertEqual(ElementTree.parse(path).getroot().tag,
                             "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(len(set(icons)), 4)

    def test_xfwm4_rounded_corners_and_hover_states(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is only required for building artwork")
        chrome = project_root() / "assets/themes/RiceHub-Aero/xfwm4"
        with Image.open(chrome / "top-left-active.png") as corner:
            self.assertEqual(corner.size, (9, 33))
            self.assertEqual(corner.getpixel((0, 0))[3], 0)
        with Image.open(chrome / "close-active.png") as close:
            self.assertEqual(close.size, (29, 23))
        self.assertNotEqual((chrome / "close-active.png").read_bytes(),
                            (chrome / "close-prelight.png").read_bytes())


class Win7UpgradeTests(unittest.TestCase):
    def test_previous_blue_folders_are_accepted_but_unknown_edits_are_not(self):
        root = project_root()
        previous = {
            "folder.svg": "7af0aa5d6b668414a4c2b1d975025dfb9aea9e87",
            "folder-documents.svg": "134cde567bddcfb1da7249a55d26f2485da86f86",
            "folder-download.svg": "ed258c073dfc16777f748b347ffb4c0407c45922",
            "folder-music.svg": "6f0d523138eb5f775688a26b8b70a60c4b791e87",
            "folder-pictures.svg": "3ef08a512de5340fa320a5e5cb56036f12fbf5fd",
        }
        for name, blob in previous.items():
            path = f"assets/icons/RiceHub-Aero/scalable/places/{name}"
            self.assertIn(blob, trusted_assets()[path])
        with tempfile.TemporaryDirectory() as temp:
            installed = Path(temp) / "icons/RiceHub-Aero"
            icon = installed / "scalable/places/folder.svg"
            icon.parent.mkdir(parents=True)
            source = root / "assets/icons/RiceHub-Aero"
            icon.write_bytes((source / "scalable/places/folder.svg").read_bytes())
            inspect_bundle(source, installed)
            icon.write_bytes(icon.read_bytes() + b"<!-- local customization -->")
            with self.assertRaisesRegex(AssetConflict, "conflicts"):
                inspect_bundle(source, installed)

    OLD_THEMERC = (
        "active_text_color=#143954\ninactive_text_color=#5c7387\n"
        "active_text_shadow_color=#f6fcff\ninactive_text_shadow_color=#edf4f9\n"
        "button_offset=3\nbutton_spacing=1\nfull_width_title=true\n"
        "frame_border_top=2\nmaximized_offset=0\nshow_app_icon=true\n"
        "title_horizontal_offset=8\ntitle_vertical_offset_active=1\n"
        "title_vertical_offset_inactive=1\ntitle_shadow_active=true\n"
        "title_shadow_inactive=false\n"
    )

    def test_exact_prior_managed_assets_migrate_but_customizations_fail(self):
        path = "assets/themes/RiceHub-Aero/xfwm4/themerc"
        self.assertIn(git_blob_sha(self.OLD_THEMERC.encode()), trusted_assets()[path])
        with tempfile.TemporaryDirectory() as temp:
            installed = Path(temp) / "themes/RiceHub-Aero"
            theme = installed / "xfwm4/themerc"
            theme.parent.mkdir(parents=True)
            theme.write_text(self.OLD_THEMERC)
            source = project_root() / "assets/themes/RiceHub-Aero"
            inspect_bundle(source, installed)
            theme.write_text(self.OLD_THEMERC + "# my personal override\n")
            with self.assertRaisesRegex(AssetConflict, "conflicts"):
                inspect_bundle(source, installed)


if __name__ == "__main__":
    unittest.main()
