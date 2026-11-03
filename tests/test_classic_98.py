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
        classic = shell.split("def _create_classic_menu(self):", 1)[1].split(
            "def _create_frutiger_menu(self):", 1)[0]
        for name in ("Programs", "Favorites", "Documents", "Settings", "Find",
                     "Help", "Run…", "Shut Down…", "Gtk.MenuButton", "set_direction",
                     "_programs_cascade", "_open_tool", "folder_menu", "_reanchor_luna_menu"):
            with self.subTest(name=name):
                self.assertIn(name, classic)
        self.assertIn('34 if profile == "winclassic"', shell)
        self.assertIn('"winclassic": (262, 332)', shell)
        self.assertIn('"winclassic", "windows10")', shell)
        self.assertIn('and os.environ.get("RICEBOWL_CAPTURE_SIZE") == "1024"', shell)
        self.assertIn("xfce4-appfinder", shell)
        self.assertIn("xfce4-keyboard-settings", shell)
        self.assertIn("classic-control-caption", shell)
        self.assertIn("classic-control-grid", shell)
        self.assertIn("grid.attach(button, index % 3", shell)
        self.assertIn("Gtk.Orientation.VERTICAL if classic_icon", shell)
        self.assertIn("Gtk.Justification.CENTER", shell)
        self.assertIn("Close Control Panel", shell)
        self.assertEqual(PROFILES["winclassic"].wallpaper, "classic-teal.jpg")

    def test_gtk_and_live_shell_use_90s_widget_grammar(self):
        css = CSS["winclassic"]
        for token in (b".classic-chevron", b".classic-menu-list", b".classic-brand-label",
                      b".classic-control-caption", b".classic-control-close",
                      b".classic-control-grid",
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
