"""XP Luna 2001 layout, installed-app, artwork and safe-upgrade contracts."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from macrice.aero_layout import actual_popup_y, bottom_strut, menu_geometry
from macrice.aero_shell import LAUNCHABLE_TOOLS, luna_program_groups, luna_programs
from macrice.asset_upgrade import AssetConflict, git_blob_sha, inspect_bundle, install_bundle, trusted_assets
from macrice.installer import project_root
from macrice.luna_control_panel import (
    LUNA_CATEGORIES, LUNA_TASKS, available_program, matching_tasks, task_art,
)


class App:
    def __init__(self, identifier, name, categories=None):
        self.identifier, self.name, self.categories = identifier, name, categories

    def get_id(self):
        return self.identifier

    def get_display_name(self):
        return self.name

    def get_name(self):
        return self.name

    def get_categories(self):
        return self.categories


class LunaProgramsTests(unittest.TestCase):
    def test_all_programs_cascade_covers_every_app_once_including_uncategorized(self):
        apps = (App("browser.desktop", "Browser", "Network;WebBrowser;"),
                App("editor.desktop", "Editor", "Utility;Office;"),
                App("mystery.desktop", "Mystery", "Unlisted;"),
                App("other.desktop", "Other"))
        groups = luna_program_groups(apps)
        assigned = [app for _name, _icon, members in groups for app in members]
        self.assertCountEqual(assigned, apps)
        self.assertEqual(len(assigned), len(set(assigned)))
        self.assertIn("Other Programs", [name for name, _, _ in groups])

    def test_featured_are_real_browser_and_mail_apps_with_no_duplicates(self):
        apps = (App("xfce4-terminal.desktop", "Terminal", "System;"),
                App("icefox.desktop", "Icefox", "Network;WebBrowser;"),
                App("mail.desktop", "Mail", "Email;Network;"),
                App("files.desktop", "Files", "FileManager;"))
        featured, regular = luna_programs(apps, ("files.desktop",), "", limit=6)
        self.assertEqual([app.name for app in featured], ["Icefox", "Mail"])
        self.assertEqual([app.name for app in regular], ["Terminal", "Files"])
        self.assertFalse(set(featured) & set(regular))

    def test_pins_fallback_without_browser_or_mail_and_search_is_complete(self):
        apps = (App("alpha.desktop", "Alpha"), App("beta.desktop", "Beta"),
                App("gamma.desktop", "Gamma"))
        featured, regular = luna_programs(apps, ("beta.desktop", "gamma.desktop"), "")
        self.assertEqual(featured, (apps[1], apps[2]))
        self.assertEqual(regular, (apps[0],))
        self.assertEqual(luna_programs(apps, (), "alP", 6), ((), (apps[0],)))

    def test_app_info_without_categories_is_supported(self):
        class NoCategories:
            def get_id(self): return "bare.desktop"
            def get_display_name(self): return "Bare"
            def get_name(self): return "Bare"

        app = NoCategories()
        self.assertEqual(luna_programs((app,), ("bare.desktop",), ""), ((app,), ()))

    def test_user_start_favorites_and_last_launched_apps(self):
        apps = (App("browser.desktop", "Browser", "Network;WebBrowser;"),
                App("mail.desktop", "Mail", "Email;"),
                App("paint.desktop", "Paint"), App("terminal.desktop", "Terminal"))
        featured, recent = luna_programs(apps, (), "", start_favorites=("terminal.desktop",),
                                         history={"paint.desktop": (2, 500),
                                                  "mail.desktop": (10, 100)})
        self.assertEqual(featured, (apps[3],))
        self.assertEqual(recent, (apps[2], apps[1], apps[0]))


class LunaGeometryTests(unittest.TestCase):
    def test_control_panel_has_a_dedicated_monitor_constrained_window(self):
        shell = (project_root() / "macrice/aero_shell.py").read_text()
        self.assertIn('"winclassic": 570', shell)
        self.assertIn('self._assert_control_footer_visible()', shell)
        self.assertIn('action_heights.get(profile, 430)', shell)
        self.assertIn('from .luna_control_panel import build', shell)
        self.assertIn('width = min(746, max(0, rect.width - 24))', shell)
        self.assertIn('height = min(536, max(0, rect.height - panel_height - 24))', shell)

    def test_control_panel_caption_uses_input_window_and_keeps_close_outside_drag(self):
        panel = (project_root() / "macrice/luna_control_panel.py").read_text()
        self.assertIn("draggable_caption(window, title, Gtk, Gdk)", panel)
        self.assertIn("caption.pack_end(close, False, False, 0)", panel)

    def test_control_panel_categories_never_launch_fake_or_unavailable_applets(self):
        self.assertEqual(len(LUNA_CATEGORIES), 9)
        self.assertEqual(available_program(("missing", "installed"),
                                           lambda program: "/usr/bin/" + program
                                           if program == "installed" else None), "installed")
        self.assertIsNone(available_program(("absent",), lambda _program: None))
        self.assertTrue(all(len(row) == 4 for row in LUNA_CATEGORIES))

    def test_control_panel_tasks_are_searchable_and_launchable(self):
        self.assertEqual(set(LUNA_TASKS), {category[0] for category in LUNA_CATEGORIES})
        for tasks in LUNA_TASKS.values():
            self.assertGreater(len(tasks), 1)
            for name, icon, programs, explanation in tasks:
                self.assertTrue(name and icon and programs and explanation)
                self.assertTrue(set(programs) <= LAUNCHABLE_TOOLS, (name, programs))
        results = matching_tasks("keyboard")
        self.assertTrue(any("Keyboard" in task[0] for _category, task in results))
        self.assertFalse(matching_tasks("not-a-real-setting-123"))

    def test_luna_user_folders_use_xdg_and_ask_before_creation(self):
        shell = (project_root() / "macrice/aero_shell.py").read_text()
        self.assertIn("GLib.get_user_special_dir(kind)", shell)
        self.assertIn("Gtk.ButtonsType.YES_NO", shell)
        self.assertIn("folder.mkdir(parents=True, exist_ok=True)", shell)
        self.assertIn('"Control Panel", "preferences-system", callback=self._toggle_actions', shell)

    def test_40px_taskbar_menu_above_panel_on_common_screens(self):
        for x, y, width, height in ((0, 0, 1600, 900), (0, 0, 1024, 768),
                                     (1600, 90, 1024, 768), (-1280, 0, 1280, 800)):
            with self.subTest(screen=(x, y, width, height)):
                mx, my, mw, mh = menu_geometry(x, y, width, height,
                                               preferred_width=480, preferred_height=540,
                                               panel_height=40)
                self.assertGreaterEqual(mx, x)
                self.assertGreaterEqual(my, y)
                self.assertLessEqual(mx + mw, x + width)
                self.assertLessEqual(my + mh, y + height - 40 - 8)
                self.assertEqual(actual_popup_y(y, height, mh, panel_height=40), my)
                self.assertEqual(bottom_strut(0, height - 40, width, 40, height,
                                               panel_height=40)[0][-1], 40)


class LunaArtworkTests(unittest.TestCase):
    def test_every_category_and_leaf_uses_a_distinct_luna_asset(self):
        directory = project_root() / "assets/icons/RiceHub-Luna-Icons/scalable/apps"
        for name, icon, _cmds, _summary in LUNA_CATEGORIES:
            with self.subTest(category=name):
                self.assertTrue((directory / (icon + ".svg")).is_file())
                self.assertIn("ricehub-luna-cp-", icon)
            for _title, task_icon, _commands, _detail in LUNA_TASKS[name]:
                with self.subTest(task=task_icon):
                    resolved = task_art(name, task_icon)
                    self.assertEqual(resolved, "ricehub-luna-task-" + task_icon)
                    source = directory / (resolved + ".svg")
                    self.assertEqual(ElementTree.parse(source).getroot().tag,
                                     "{http://www.w3.org/2000/svg}svg")

    def test_category_icons_render_at_xp_control_panel_sizes(self):
        try:
            import gi
            gi.require_version("GdkPixbuf", "2.0")
            from gi.repository import GdkPixbuf
        except (ImportError, ValueError):
            self.skipTest("GTK Pixbuf is optional without the desktop runtime")
        directory = project_root() / "assets/icons/RiceHub-Luna-Icons/scalable/apps"
        for _name, icon, _commands, _description in LUNA_CATEGORIES:
            for size in (16, 24, 32, 48):
                with self.subTest(icon=icon, size=size):
                    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(directory / (icon + ".svg")), size, size, True)
                    self.assertEqual((image.get_width(), image.get_height()), (size, size))

    def test_nested_program_group_icons_are_original_luna_assets(self):
        icons = project_root() / "assets/icons/RiceHub-Luna-Icons/scalable"
        for name, directory in (("accessories-text-editor", "apps"),
                                ("web-browser", "apps"),
                                ("preferences-system", "apps"),
                                ("folder-documents", "places"),
                                ("applications-other", "apps")):
            self.assertTrue((icons / directory / (name + ".svg")).is_file())

    def test_bespoke_user_avatar_and_xp_system_glyphs_are_valid_svg(self):
        root = project_root()
        icons = root / "assets/icons/RiceHub-Luna-Icons/scalable/apps"
        for icon in (root / "assets/ricebowl-xp-user.svg",
                     *(icons / (name + ".svg") for name in
                       ("help-browser", "system-run", "system-search", "printer",
                        "system-log-out", "system-shutdown"))):
            with self.subTest(icon=icon.name):
                self.assertEqual(ElementTree.parse(icon).getroot().tag,
                                 "{http://www.w3.org/2000/svg}svg")

    def test_window_chrome_has_real_rounded_corner_and_separate_close(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is a dev-only asset-generation dependency")
        frame = project_root() / "assets/themes/RiceHub-Luna/xfwm4"
        with Image.open(frame / "close-active.png") as close:
            self.assertEqual(close.size, (27, 27))
        with Image.open(frame / "top-left-active.png") as corner:
            self.assertEqual(corner.size, (6, 32))
            self.assertEqual(corner.convert("RGBA").getpixel((0, 0))[3], 0)


class LunaUpgradeTests(unittest.TestCase):
    # Exact file shipped on main in RiceBowl v0.9.1; no git checkout needed.
    OLD_XFWM_RC = (
        "active_text_color=#123c79\ninactive_text_color=#5075a3\n"
        "button_offset=0\nbutton_spacing=0\nfull_width_title=true\n"
        "frame_border_top=0\nmaximized_offset=0\nshow_app_icon=false\n"
        "title_horizontal_offset=12\ntitle_vertical_offset_active=1\n"
        "title_vertical_offset_inactive=1\ntitle_shadow_active=false\n"
        "title_shadow_inactive=false\n"
    )

    def test_v091_exact_theme_upgrade_keeps_backup_and_rejects_edits(self):
        key = "assets/themes/RiceHub-Luna/xfwm4/themerc"
        self.assertIn(git_blob_sha(self.OLD_XFWM_RC.encode()), trusted_assets()[key])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "assets/themes/RiceHub-Luna"
            target = root / "data/themes/RiceHub-Luna"
            for path in (source, target):
                (path / "xfwm4").mkdir(parents=True)
            (source / "xfwm4/themerc").write_bytes(
                (project_root() / key).read_bytes())
            (target / "xfwm4/themerc").write_text(self.OLD_XFWM_RC)
            inspect_bundle(source, target)
            backup = install_bundle(source, target)
            self.assertIsNotNone(backup)
            self.assertEqual((backup / "xfwm4/themerc").read_text(), self.OLD_XFWM_RC)
            self.assertEqual((target / "xfwm4/themerc").read_bytes(),
                             (source / "xfwm4/themerc").read_bytes())
            (target / "xfwm4/themerc").write_text("my private modified theme")
            with self.assertRaises(AssetConflict):
                inspect_bundle(source, target)


if __name__ == "__main__":
    unittest.main()
