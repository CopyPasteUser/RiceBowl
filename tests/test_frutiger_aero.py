"""Aqua World visual identity, real status, native asset and upgrade contracts."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from PIL import Image

from macrice.aero_shell import default_pins, frutiger_apps, frutiger_status_summary
from macrice.asset_upgrade import trusted_assets
from macrice.hardware_status import BatteryState, DesktopStatus, SoundState
from macrice.heritage_shell import CSS
from macrice.installer import project_root


ROOT = project_root()
FRUTIGER_THEME = ROOT / "assets/themes/RiceHub-Frutiger"


class FrutigerAeroContractTests(unittest.TestCase):
    def test_fresh_default_files_pin_opens_files_not_file_manager_settings(self):
        def app(title, identifier):
            return SimpleNamespace(get_display_name=lambda: title, get_name=lambda: title,
                                   get_id=lambda: identifier)
        apps = (app("File Manager Settings", "thunar-settings.desktop"),
                app("Firefox Web Browser", "firefox.desktop"),
                app("Terminal", "terminal.desktop"),
                app("Thunar File Manager", "thunar.desktop"))
        self.assertEqual(default_pins(apps),
                         ("thunar.desktop", "firefox.desktop", "terminal.desktop"))

    def test_home_grid_prioritizes_real_pins_but_searches_every_app(self):
        def app(name, identifier, categories=""):
            return SimpleNamespace(get_display_name=lambda: name, get_name=lambda: name,
                                   get_id=lambda: identifier,
                                   get_categories=lambda: categories)

        apps = (app("Bulk Rename", "rename.desktop"),
                app("Code Editor", "editor.desktop"),
                app("File Manager", "files.desktop", "FileManager;"),
                app("Firefox", "browser.desktop", "WebBrowser;"),
                app("Terminal", "term.desktop", "TerminalEmulator;"))
        result = frutiger_apps(apps, ("editor.desktop", "browser.desktop"), "")
        self.assertEqual([entry.get_id() for entry in result],
                         ["editor.desktop", "browser.desktop", "files.desktop",
                          "term.desktop", "rename.desktop"])
        self.assertEqual(frutiger_apps(apps, (), "rename"), (apps[0],))
        self.assertEqual(frutiger_apps(apps, (), "BROWSER"), ())
        self.assertEqual(len(set(map(id, result))), len(apps))

    def test_live_header_honestly_represents_devices(self):
        self.assertIn("Checking", frutiger_status_summary(None))
        connected = DesktopStatus(
            network="wifi", sound=SoundState(percent=72, muted=False),
            battery=BatteryState(percent=83, charging=True, label="Charging"),
        )
        self.assertEqual(frutiger_status_summary(connected),
                         "Wi-Fi  •  Volume 72%  •  Battery 83%")
        offline = DesktopStatus(network="offline", sound=SoundState(None, None), battery=None)
        self.assertEqual(frutiger_status_summary(offline),
                         "Offline  •  Audio unavailable  •  No battery")
        muted = DesktopStatus(network="ethernet", sound=SoundState(0, True), battery=None)
        self.assertIn("Muted", frutiger_status_summary(muted))

    def test_native_launcher_owns_its_widgets_and_search(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        aqua = source[source.index("def _create_frutiger_menu(self):"):
                      source.index("def _create_ten_menu(self):")]
        for key in ("aqua-dashboard", "aqua-hero", "aqua-shortcut", "aqua-app-grid",
                    "Gtk.FlowBox", "aqua-footer", "Places", "Settings",
                    "self._populate(\"\")", "self.frutiger_status_label"):
            with self.subTest(key=key):
                self.assertIn(key, aqua)
        grid = source[source.index("def _populate_frutiger(self, query):"):
                      source.index("def _populate_win7(self, query):")]
        self.assertIn("frutiger_apps(self.apps, self._pinned_ids, query)", grid)
        self.assertIn("matching_apps(apps, query)", source)
        self.assertIn("Gtk.Image.new_from_gicon", grid)
        self.assertIn("self._launch(selected)", grid)
        self.assertIn("self._pin_context", grid)
        self.assertIn("picture.set_pixel_size(48)", grid)
        self.assertIn('profile in ("winxp", "aero", "frutiger", "winclassic", "windows10", "chromeos")', source)

    def test_application_pins_do_not_silently_accept_failed_gio_launches(self):
        from unittest.mock import Mock
        from macrice.aero_shell import launch_app_checked

        success = Mock()
        success.launch.return_value = True
        launch_app_checked(success)
        success.launch.assert_called_once_with([], None)
        failed = Mock()
        failed.launch.return_value = False
        with self.assertRaisesRegex(RuntimeError, "reported failure"):
            launch_app_checked(failed)

    def test_aqua_glass_css_is_profile_scoped(self):
        css = CSS["frutiger"]
        for selector in (b"frutiger-taskbar", b"frutiger-start", b"frutiger-tray",
                         b"aqua-dashboard", b"aqua-hero", b"aqua-app-tile",
                         b"aqua-tab:checked", b"aqua-footer", b"aqua-shortcut:hover"):
            with self.subTest(selector=selector):
                self.assertIn(selector, css)
        for other in ("winxp", "winclassic", "chromeos"):
            self.assertNotIn(b"aqua-dashboard", CSS[other], msg=other)
        self.assertIn(b"aqua-control-root", css)
        for selector in (b".aqua-section-title", b".aqua-control-hero",
                         b".aqua-app-tile:active"):
            self.assertIn(selector, css)

    def test_places_use_actual_xdg_paths_and_confirm_missing_directories(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        frutiger = source[source.index("def _create_frutiger_menu(self):"):
                          source.index("def _create_ten_menu(self):")]
        for target in ("DIRECTORY_DOCUMENTS", "DIRECTORY_DOWNLOAD", "DIRECTORY_MUSIC",
                       "DIRECTORY_PICTURES", "DIRECTORY_VIDEOS"):
            self.assertIn(target, frutiger)
        self.assertIn("offer_create=True", frutiger)
        self.assertIn("self._open_luna_user_folder(folder)", frutiger)

    def test_uncomposited_x11_popup_corners_are_rounded_if_supported(self):
        source = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        self.assertIn("GLib.idle_add(apply_rounded_window_shape, self.menu, 27)", source)
        self.assertIn("GLib.idle_add(apply_rounded_window_shape, self.actions, 22)", source)

    def test_native_gtk_gloss_and_window_frame_assets(self):
        css = (FRUTIGER_THEME / "gtk-3.0/gtk.css").read_text(encoding="utf-8")
        for token in ("RiceBowl Aqua World", "linear-gradient", "button:focus",
                      "window.thunar", "scrollbar slider", "selection"):
            self.assertIn(token, css)
        frame = FRUTIGER_THEME / "xfwm4"
        for button in ("close", "hide", "maximize", "menu", "shade", "stick"):
            for state in ("active", "inactive", "prelight", "pressed"):
                path = frame / f"{button}-{state}.png"
                with self.subTest(path=path.name), Image.open(path) as icon:
                    self.assertEqual(icon.size, (27, 27))
                    self.assertEqual(icon.mode, "RGBA")
        for name in ("title-1-active.png", "title-3-inactive.png"):
            with Image.open(frame / name) as image:
                self.assertEqual(image.size, (15, 32))

    def test_previous_unmodified_frutiger_assets_can_auto_upgrade(self):
        manifest = trusted_assets()
        key = "assets/themes/RiceHub-Frutiger/gtk-3.0/gtk.css"
        self.assertIn("d6eb5885a551baf36e8f8048b22dbac8f6cf2efb", manifest[key])
        self.assertIn("bb76b91cd14948884fab6c10ba5c26f0282f2a1b", manifest[key])
        for name in ("close-active.png", "maximize-prelight.png", "title-1-active.png"):
            self.assertTrue(manifest[f"assets/themes/RiceHub-Frutiger/xfwm4/{name}"])

    def test_organic_glass_start_orb_is_shared_across_launchers(self):
        source = (ROOT / "assets/ricebowl-frutiger-start.svg").read_bytes()
        manifest = trusted_assets()
        self.assertIn(b"radialGradient", source)
        self.assertIn(b"leaf", source)
        for name in ("start-here", "xfce4-menu", "ricehub-start", "ricebowl-start"):
            path = f"assets/icons/RiceHub-Frutiger-Icons/scalable/apps/{name}.svg"
            with self.subTest(icon=name):
                self.assertEqual((ROOT / path).read_bytes(), source)
                self.assertIn("cdd1978f263d46dee98b370171aac83970e78080",
                              manifest[path])

    def test_thunar_desktop_entry_resolves_to_real_aqua_file_manager_icon(self):
        icons = ROOT / "assets/icons/RiceHub-Frutiger-Icons/scalable/apps"
        base = (icons / "system-file-manager.svg").read_text(encoding="utf-8")
        thunar = (icons / "org.xfce.thunar.svg").read_text(encoding="utf-8")
        self.assertEqual(thunar,
                         base.replace("system-file-manager</title>",
                                      "org.xfce.thunar</title>"))


if __name__ == "__main__":
    unittest.main()
