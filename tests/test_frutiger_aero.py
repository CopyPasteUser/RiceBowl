"""Aqua World visual identity, real status, native asset and upgrade contracts."""
from __future__ import annotations

import unittest

from PIL import Image

from macrice.aero_shell import frutiger_status_summary
from macrice.asset_upgrade import trusted_assets
from macrice.hardware_status import BatteryState, DesktopStatus, SoundState
from macrice.heritage_shell import CSS
from macrice.installer import project_root


ROOT = project_root()
FRUTIGER_THEME = ROOT / "assets/themes/RiceHub-Frutiger"


class FrutigerAeroContractTests(unittest.TestCase):
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
        self.assertIn("matching_apps(self.apps, query)", grid)
        self.assertIn("Gtk.Image.new_from_gicon", grid)
        self.assertIn("self._launch(selected)", grid)
        self.assertIn("self._pin_context", grid)
        self.assertIn("picture.set_pixel_size(48)", grid)
        self.assertIn('profile in ("winxp", "aero", "frutiger", "winclassic", "windows10", "chromeos")', source)

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


if __name__ == "__main__":
    unittest.main()
