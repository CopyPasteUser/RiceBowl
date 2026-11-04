"""Windows 7 Aero fidelity contracts without needing an X11 desktop."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from macrice.aero_layout import actual_popup_y, bottom_strut, menu_geometry, task_capacity
from macrice.aero_shell import CSS, win7_explorer_command, win7_programs
from macrice.asset_upgrade import (AssetConflict, git_blob_sha, inspect_bundle,
                                   install_bundle, trusted_assets)
from macrice.installer import project_root
from macrice.rice import STYLES
from macrice.luna_tray import LunaTray
from macrice.win7_control_panel import CATEGORIES, Task, installed_command, matching_categories
from macrice.win7_tray import Win7Tray


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

    def test_48px_superbar_and_start_fit_low_resolution(self):
        for x, y, w, h in ((0, 0, 1600, 900), (0, 0, 1024, 768),
                            (1024, 80, 1024, 768), (-1280, 0, 1280, 800)):
            with self.subTest(monitor=(x, y, w, h)):
                mx, my, mw, mh = menu_geometry(x, y, w, h, preferred_width=525,
                                                preferred_height=535, panel_height=48)
                self.assertGreaterEqual(mx, x)
                self.assertGreaterEqual(my, y)
                self.assertLessEqual(mx + mw, x + w)
                self.assertEqual(my + mh, y + h - 48 - 8)
                self.assertEqual(actual_popup_y(y, h, mh, panel_height=48), my)
        self.assertEqual(bottom_strut(0, 0, 1024, 768, 768, panel_height=48)[0][-1], 48)
        self.assertGreater(task_capacity(1024, 3, 345, compact=True),
                           task_capacity(1024, 3, 345))
        self.assertEqual(task_capacity(320, 6, 345, compact=True), 0)

    def test_only_aero_has_superbar_and_menu_design_tokens(self):
        for name in (b"win7-taskbar", b"win7-start", b"win7-task", b"win7-menu-root",
                     b"win7-program", b"win7-side", b"win7-power"):
            self.assertIn(name, CSS)
        self.assertIn(b".aero-taskbar.win7-taskbar", CSS)
        self.assertIn(b".win7-control-search", CSS)
        shell = (project_root() / "macrice/aero_shell.py").read_text()
        self.assertIn('48 if profile == "aero"', shell)
        panel = (project_root() / "macrice/win7_control_panel.py").read_text()
        self.assertIn('search.set_placeholder_text("Search Control Panel")', panel)
        self.assertIn('window.set_skip_taskbar_hint(False)', panel)

    def test_win7_device_flyouts_have_distinct_gtk_skin_and_shared_safe_backends(self):
        for name in (b"win7-tray-popup", b"win7-tray-heading",
                     b"win7-tray-volume-row", b"win7-clock-button"):
            self.assertIn(name, CSS)
        self.assertIsNot(Win7Tray._audio, LunaTray._audio)
        for action in ("refresh_network", "_join_wifi", "_switch_output",
                       "_toggle_bluetooth", "_commit_brightness", "_switch_profile"):
            self.assertIs(getattr(Win7Tray, action), getattr(LunaTray, action))
        self.assertTrue(issubclass(Win7Tray, LunaTray))

    def test_optional_explorer_uses_its_structural_win7_skin_without_mime_changes(self):
        self.assertEqual(
            win7_explorer_command("/usr/bin/rice-explorer", Path("/tmp/folder with spaces")),
            ("/usr/bin/rice-explorer", "--theme", "win7", "/tmp/folder with spaces"))


class Win7ControlPanelTests(unittest.TestCase):
    def test_eight_historical_categories_have_only_real_linux_tasks(self):
        self.assertEqual(tuple(category.name for category in CATEGORIES), (
            "System and Security", "Network and Internet", "Hardware and Sound",
            "Programs", "User Accounts and Family Safety",
            "Appearance and Personalization", "Clock, Language, and Region",
            "Ease of Access"))
        for category in CATEGORIES:
            self.assertGreaterEqual(len(category.tasks), 2)
            self.assertTrue(category.icon)
            for task in category.tasks:
                self.assertTrue(task.name)
                self.assertTrue(all(" " not in command and "/" not in command
                                    for command in task.commands))

    def test_search_matches_categories_and_nested_tasks(self):
        self.assertEqual(len(matching_categories("")), 8)
        self.assertEqual([c.name for c in matching_categories("SOuNd")],
                         ["Hardware and Sound"])
        self.assertEqual([c.name for c in matching_categories("Theme")],
                         ["Appearance and Personalization"])
        self.assertEqual(matching_categories("no-matching-tool-39083"), ())

    def test_unavailable_tool_does_not_create_fake_click_target(self):
        task = Task("Choose a tool", ("first", "second"))
        self.assertIsNone(installed_command(task, lambda _: None))
        self.assertEqual(installed_command(task, lambda cmd: "/usr/bin/" + cmd
                                           if cmd == "second" else None), "second")

    def test_all_eight_categories_have_original_readable_aero_icons(self):
        source = project_root() / "assets/icons/RiceHub-Aero/scalable/apps"
        icons = []
        for category in CATEGORIES:
            self.assertTrue(category.icon.startswith("ricehub-cp-"))
            icon = source / (category.icon + ".svg")
            root = ElementTree.parse(icon).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertEqual(root.get("viewBox"), "0 0 64 64")
            self.assertTrue(root.find("{http://www.w3.org/2000/svg}title") is not None)
            icons.append(icon.read_bytes())
        self.assertEqual(len(set(icons)), 8)


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

    def test_explorer_has_original_files_navigation_and_disk_icons(self):
        root = project_root() / "assets/icons/RiceHub-Aero"
        index = (root / "index.theme").read_text()
        self.assertIn("scalable/mimetypes", index)
        for group, names in {
            "places": ("folder-open", "folder-desktop", "folder-videos",
                       "folder-templates", "folder-publicshare", "folder-recent",
                       "network-server", "network-workgroup", "drive-harddisk",
                       "drive-removable-media"),
            "mimetypes": ("text-x-generic", "application-x-generic",
                          "image-x-generic", "audio-x-generic", "video-x-generic",
                          "application-pdf", "application-x-archive",
                          "application-x-executable"),
        }.items():
            for name in names:
                with self.subTest(group=group, icon=name):
                    svg = root / "scalable" / group / (name + ".svg")
                    doc = ElementTree.parse(svg).getroot()
                    self.assertEqual(doc.tag, "{http://www.w3.org/2000/svg}svg")
                    self.assertEqual(doc.get("viewBox"), "0 0 64 64")
                    self.assertIsNotNone(doc.find("{http://www.w3.org/2000/svg}title"))

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
    def test_previous_icon_theme_index_is_safe_to_upgrade(self):
        old = b"[Icon Theme]\nName=RiceBowl Aero\nComment=Original Aqua-blue XFCE icons with Adwaita fallback\nInherits=Adwaita,hicolor\nDirectories=scalable/apps,scalable/places\n\n[scalable/apps]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=256\nContext=Applications\n\n[scalable/places]\nSize=48\nType=Scalable\nMinSize=16\nMaxSize=256\nContext=Places\n"
        self.assertIn(git_blob_sha(old), trusted_assets()["assets/icons/RiceHub-Aero/index.theme"])
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "icons/RiceHub-Aero"
            destination.mkdir(parents=True)
            (destination / "index.theme").write_bytes(old)
            source = project_root() / "assets/icons/RiceHub-Aero"
            inspect_bundle(source, destination)
            backup = install_bundle(source, destination)
            self.assertIsNotNone(backup)
            self.assertEqual((destination / "index.theme").read_bytes(),
                             (source / "index.theme").read_bytes())
            self.assertTrue((destination / "scalable/mimetypes/text-x-generic.svg").exists())

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
