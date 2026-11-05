"""Native Windows 98 Classic fidelity, safety and responsive capture contract."""
from __future__ import annotations

import unittest
from xml.etree import ElementTree

from PIL import Image

from macrice.asset_upgrade import git_blob_sha, trusted_assets
from macrice.heritage import PROFILES
from macrice.heritage_shell import CSS
from macrice.installer import project_root


ROOT = project_root()
THEME = ROOT / "assets/themes/RiceHub-Classic"
ICONS = ROOT / "assets/icons/RiceHub-Classic-Icons/scalable/apps"


class Win98FidelityTests(unittest.TestCase):
    def test_faithful_teal_wallpaper_and_original_start_icon(self):
        with Image.open(ROOT / "assets/wallpapers/classic-teal.jpg") as img:
            self.assertEqual(img.size, (1920, 1080))
            for position in ((0, 0), (900, 600), (1900, 1000)):
                r, g, b = img.getpixel(position)
                self.assertLessEqual(abs(r - 0), 4)
                self.assertLessEqual(abs(g - 128), 4)
                self.assertLessEqual(abs(b - 128), 4)
        artwork = (ROOT / "assets/ricebowl-classic-start.svg").read_bytes()
        self.assertIn(b"Linux pixel penguin", artwork)
        for name in ("start-here", "xfce4-menu", "ricehub-start", "ricebowl-start"):
            self.assertEqual((ICONS / f"{name}.svg").read_bytes(), artwork)
        for name in ("classic-control-panel", "applications-other", "edit-find",
                     "help-browser", "system-run", "system-shutdown"):
            ElementTree.parse(ICONS / f"{name}.svg")

    def test_chrome_is_square_and_unambiguously_win98(self):
        frame = THEME / "xfwm4"
        config = (frame / "themerc").read_text(encoding="utf-8")
        self.assertIn("active_text_color=#ffffff", config)
        self.assertIn("show_app_icon=true", config)
        for name in ("close", "hide", "maximize", "menu", "shade", "stick"):
            for state in ("active", "inactive", "prelight", "pressed"):
                with self.subTest(name=name, state=state), Image.open(frame / f"{name}-{state}.png") as icon:
                    self.assertEqual(icon.size, (22, 22))
                    self.assertEqual(icon.mode, "RGBA")
        for state in ("active", "inactive"):
            with Image.open(frame / f"title-1-{state}.png") as image:
                self.assertEqual(image.size, (12, 27))
                self.assertEqual(image.getpixel((6, 12)),
                                 (0, 0, 128, 255) if state == "active" else (128, 128, 128, 255))

    def test_native_menu_is_dense_with_real_flyouts_and_actions(self):
        shell = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        classic = (ROOT / "macrice/classic98_menu.py").read_text(encoding="utf-8")
        control = (ROOT / "macrice/classic98_control_panel.py").read_text(encoding="utf-8")
        tray = (ROOT / "macrice/classic98_tray.py").read_text(encoding="utf-8")
        taskbar_options = (ROOT / "macrice/classic98_taskbar_settings.py").read_text(encoding="utf-8")
        for name in ("Programs", "Favorites", "Documents", "Settings", "Find",
                     "Help", "Run…", "Shut Down…", "Gtk.MenuButton", "set_direction",
                     "show_run", "show_file_search", "gtk_bookmarks", "get_items",
                     "classic_refresh_submenus", "classic_menus"):
            with self.subTest(name=name):
                self.assertIn(name, classic)
        for name in ("APPLETS", "Gtk.FlowBox", "child-activated",
                     "set_resizable", "View", "Close"):
            with self.subTest(name=name):
                self.assertIn(name, control)
        for name in ("Volume Control", "Power Meter", "Network Connections",
                     "Date and Time", "volume_scale", "mute_button"):
            with self.subTest(name=name):
                self.assertIn(name, tray)
        self.assertIn('34 if profile == "winclassic"', shell)
        self.assertIn('"winclassic": (262, 332)', shell)
        self.assertIn('"winclassic", "windows10")', shell)
        self.assertIn('and os.environ.get("RICEBOWL_CAPTURE_SIZE") == "1024"', shell)
        self.assertIn("from .classic98_menu import build", shell)
        self.assertIn("from .classic98_control_panel import build", shell)
        self.assertIn("classic98_tray_show", shell)
        self.assertIn("classic98-quicklaunch", shell)
        self.assertIn("classic98_open_taskbar_properties", shell)
        self.assertIn("taskbar_spacer = Gtk.EventBox()", shell)
        self.assertIn("classic98_open_taskbar_properties", classic)
        self.assertIn("classic98_open_taskbar_properties", control)
        self.assertIn("Gtk.ResponseType.APPLY", taskbar_options)
        self.assertEqual(PROFILES["winclassic"].wallpaper, "classic-teal.jpg")

    def test_classic_cascades_hold_start_open_during_gtk_pointer_grabs(self):
        classic = (ROOT / "macrice/classic98_menu.py").read_text(encoding="utf-8")
        shell = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertTrue("shell._track_start_popup(Gtk.Menu())" in classic,
                        "Classic GTK flyouts must register with the shared focus guard")
        self.assertTrue('if name == "menu" and self._start_open_menus:' in shell,
                        "Focus timeout must not hide Start while a cascade is mapped")

    def test_gtk_and_live_shell_use_90s_widget_grammar(self):
        css = CSS["winclassic"]
        for token in (b".classic-chevron", b".classic-menu-list", b".classic-brand-label",
                      b".classic-control-caption", b".classic-control-close",
                      b".classic-control-grid", b".classic98-taskbar-properties",
                      b".classic-menu-item:focus", b"min-height: 34px", b"#000080"):
            self.assertIn(token, css)
        self.assertNotIn(b".classic-chevron", CSS["winxp"])
        self.assertNotIn(b".classic-chevron", CSS["frutiger"])
        gtk = (THEME / "gtk-3.0/gtk.css").read_text(encoding="utf-8")
        for token in ("Windows 98 Classic fidelity", "button:focus", "entry:focus",
                      "headerbar:backdrop", "window.thunar", "scrollbar slider"):
            self.assertIn(token, gtk)
        self.assertNotIn("border-radius: 16px", gtk.split("Windows 98 Classic fidelity", 1)[1])

    def test_safe_upgrade_accepts_only_identical_pre_redesign_assets(self):
        trust = trusted_assets()
        for path in ("assets/themes/RiceHub-Classic/gtk-3.0/gtk.css",
                     "assets/themes/RiceHub-Classic/xfwm4/close-active.png",
                     "assets/themes/RiceHub-Classic/xfwm4/title-1-active.png",
                     "assets/icons/RiceHub-Classic-Icons/scalable/apps/start-here.svg"):
            self.assertIn(path, trust)
            self.assertTrue(trust[path])
            self.assertNotIn(git_blob_sha((ROOT / path).read_bytes()), trust[path])


if __name__ == "__main__":
    unittest.main()

