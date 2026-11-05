"""ChromeOS visual identity, honest hardware actions and historical upgrades."""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from macrice.chrome_shell import CSS, launcher_favorites
from macrice.chrome_quick_settings import QUICK_ACTIONS, calendar_today
from macrice.chrome_settings import ACTIONS


ROOT = Path(__file__).resolve().parents[1]


class App:
    def __init__(self, identifier, name):
        self.identifier = identifier
        self.name = name

    def get_id(self):
        return self.identifier

    def get_display_name(self):
        return self.name

    def get_name(self):
        return self.name


class ChromeOSFidelityTests(unittest.TestCase):
    def test_favorites_only_choose_real_installed_apps(self):
        apps = (App("files.desktop", "Files"), App("edit.desktop", "Editor"),
                App("terminal.desktop", "Terminal"))
        result = launcher_favorites(apps, ("missing.desktop", "edit.desktop"))
        self.assertEqual([app.get_id() for app in result],
                         ["edit.desktop", "files.desktop", "terminal.desktop"])
        self.assertEqual(launcher_favorites((), ("fake.desktop",)), ())
        self.assertEqual(len(launcher_favorites(apps, (), limit=2)), 2)

    def test_launcher_and_quick_settings_are_separate_native_windows(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertIn("def _create_chrome_launcher(self):", source)
        self.assertIn("from .chrome_quick_settings import build", source)
        self.assertIn("self._populate_chrome_apps(query)", source)
        self.assertIn('"chromeos": (610, 628)', source)
        self.assertIn('396 if profile == "chromeos"', source)
        self.assertIn("apply_rounded_window_shape", source)
        shape_source = (ROOT / "macrice/chrome_shell.py").read_text()
        self.assertIn('gi.require_foreign("cairo")', shape_source)
        for token in (b"chrome-quick-root", b"chrome-app-card",
                      b"chrome-status-pill", b"chrome-clock-button"):
            self.assertIn(token, CSS)

    def test_quick_tiles_navigate_to_real_linux_settings(self):
        self.assertEqual(len(QUICK_ACTIONS), 6)
        for label, icon, destination, explanation in QUICK_ACTIONS:
            self.assertTrue(all((label, icon, destination, explanation)))
            self.assertIn(destination, {action.name for action in ACTIONS})
        source = (ROOT / "macrice/chrome_quick_settings.py").read_text()
        self.assertIn("actions.add(root)", source)
        self.assertIn("shutil.which(command)", source)
        self.assertIn("shell._queue_volume_change", source)
        self.assertIn("shell._toggle_output_mute", source)
        self.assertIn('Gtk.Label(label="›"), "chrome-quick-chevron"', source)
        self.assertIn("shell.chrome_quick_show_page = show_page", source)
        self.assertIn("shell._open_chrome_settings(action=item)", source)
        self.assertIn(b".chrome-quick-chevron", CSS)
        self.assertNotIn("sudo", source)

    def test_shelf_network_icon_opens_owned_network_page(self):
        shell = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertTrue('if profile == "chromeos" and name == "network":' in shell,
                        "The Wi-Fi status button must route into native Quick Settings")
        self.assertIn('self._toggle_chrome_quick_page("Network")', shell)

    def test_calendar_tracks_local_month_without_fake_cloud_events(self):
        self.assertEqual(calendar_today(date(2024, 2, 29)), (2024, 1, 29))
        self.assertEqual(calendar_today(date(2027, 1, 1)), (2027, 0, 1))
        source = (ROOT / "macrice/chrome_quick_settings.py").read_text()
        self.assertIn('stack.add_named(calendar_page, "Calendar")', source)
        self.assertIn("calendar.select_month(month, year)", source)
        self.assertIn("Online events are not connected", source)
        self.assertIn(b".chrome-quick-calendar", CSS)

    def test_generated_art_and_safe_prior_hashes(self):
        theme = ROOT / "assets/themes/RiceHub-Chrome"
        stylesheet = (theme / "gtk-3.0/gtk.css").read_text()
        for token in ("window.thunar .sidebar", "window.thunar menubar",
                      "window.thunar statusbar", "button:focus"):
            self.assertIn(token, stylesheet)
        for name in ("hide", "close", "maximize", "menu", "stick", "shade"):
            for state in ("active", "inactive", "prelight", "pressed"):
                self.assertTrue((theme / "xfwm4" / f"{name}-{state}.png").is_file())
        manifest = json.loads((ROOT / "assets/trusted-ricebowl-chrome-before-fidelity.json").read_text())
        self.assertEqual(manifest["schema"], 1)
        self.assertIn("assets/wallpapers/chrome-pastel.jpg", manifest["files"])
        self.assertIn("assets/themes/RiceHub-Chrome/gtk-3.0/gtk.css", manifest["files"])


if __name__ == "__main__":
    unittest.main()
