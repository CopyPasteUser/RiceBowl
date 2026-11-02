"""Simulated XFCE desktop: never touch the test runner's desktop or dconf."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.rice import RiceError, XfceBackend, apply, plan, restore


WALL = "/backdrop/screen0/monitor0/workspace0/last-image"
IMAGE_STYLE = "/backdrop/screen0/monitor0/workspace0/image-style"


class FakeBackend(XfceBackend):
    def __init__(self):
        self.values = {
            ("xfconf", "xsettings", "/Net/ThemeName"): "WhiteSur-Dark",
            ("xfconf", "xsettings", "/Net/IconThemeName"): "WhiteSur-light",
            ("xfconf", "xsettings", "/Gtk/CursorThemeName"): "Bibata-Original-Classic",
            ("xfconf", "xsettings", "/Gtk/CursorThemeSize"): "24",
            ("xfconf", "xsettings", "/Gtk/FontName"): "Inter 10",
            ("xfconf", "xfwm4", "/general/theme"): "WhiteSur-Dark",
            ("xfconf", "xfwm4", "/general/title_font"): "Inter Bold 10",
            ("xfconf", "xfwm4", "/general/button_layout"): "O|HMC",
            ("gsettings", "plank", "theme"): "'WhiteSur'",
            ("gsettings", "plank", "position"): "'bottom'",
            ("gsettings", "plank", "icon-size"): "60",
            ("gsettings", "plank", "hide-mode"): "'intelligent'",
            ("gsettings", "plank", "alignment"): "'center'",
            ("gsettings", "plank", "zoom-enabled"): "true",
            ("xfconf", "xfce4-desktop", WALL): "/path/to/original.jpg",
            ("xfconf", "xfce4-desktop", IMAGE_STYLE): "2",
        }
        self.fail_key = None
        self.available_theme = True
        self.calls = []

    def get(self, kind, channel, key):
        return self.values[(kind, channel, key)]

    def set(self, kind, channel, key, value):
        if key == self.fail_key:
            raise RiceError("Injected write failure")
        self.values[(kind, channel, key)] = value
        self.calls.append((kind, channel, key, value))

    def wallpaper_keys(self):
        return [WALL]

    def available(self, kind, name):
        return self.available_theme


def setup_apps(config):
    for name, filename, theme in (
        ("macmenu", "settings.json", "violet"),
        ("macos-control-center", "config.json", "graphite"),
        ("macbar", "config.json", "dark"),
    ):
        target = config / name / filename
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"theme": theme, "favorites": ["preserve-me"]}))


class RiceTests(unittest.TestCase):
    def test_plan_is_read_only_and_matches_reported_whitesur(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            changes, apps, source, target = plan(
                "night", backend=fake, data_root=root / "data", config_root=root / "config",
            )
            self.assertEqual(apps["MacMenu"], "violet")
            self.assertEqual(next(c["after"] for c in changes if c["key"] == "icon-size"), "60")
            self.assertEqual(next(c["after"] for c in changes if c["key"] == "/general/button_layout"), "CHM|")
            self.assertEqual(next(c["after"] for c in changes if c["key"] == WALL), str(target))
            self.assertTrue(source.exists())
            self.assertFalse((root / "data").exists())
            self.assertEqual(fake.calls, [])

    def test_apply_and_restore_preserve_unrelated_app_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            before = fake.values.copy()
            backup = apply("night", backend=fake, data_root=root / "data",
                           config_root=root / "config")
            self.assertTrue((backup / "manifest.json").is_file())
            self.assertEqual((backup / "manifest.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(fake.get("xfconf", "xfce4-desktop", IMAGE_STYLE), "5")
            wallpaper = Path(fake.get("xfconf", "xfce4-desktop", WALL))
            self.assertTrue(wallpaper.is_file())
            menu = root / "config/macmenu/settings.json"
            settings = json.loads(menu.read_text())
            self.assertEqual(settings["theme"], "dark")
            settings["favorites"].append("added-after-apply")
            menu.write_text(json.dumps(settings))

            restored = restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(restored, backup)
            self.assertEqual(fake.values, before)
            result = json.loads(menu.read_text())
            self.assertEqual(result["theme"], "violet")
            self.assertIn("added-after-apply", result["favorites"])

    def test_missing_theme_preflight_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            fake.available_theme = False
            setup_apps(root / "config")
            with self.assertRaisesRegex(RiceError, "WhiteSur-Light"):
                apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.calls, [])
            self.assertFalse((root / "data").exists())

    def test_failed_external_write_rolls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            fake.fail_key = WALL
            setup_apps(root / "config")
            before = fake.values.copy()
            with self.assertRaisesRegex(RiceError, "rolled back"):
                apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values, before)
            self.assertEqual(json.loads((root / "config/macmenu/settings.json").read_text())["theme"], "violet")

    def test_restore_refuses_to_overwrite_later_customization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            fake.values[("gsettings", "plank", "icon-size")] = "48"
            with self.assertRaisesRegex(RiceError, "changed since applying"):
                restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values[("gsettings", "plank", "icon-size")], "48")

    def test_app_theme_failure_restores_desktop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            before = fake.values.copy()
            with mock.patch("macrice.rice.apply_preset", side_effect=ValueError("broken app preferences")):
                with self.assertRaisesRegex(RiceError, "rolled back"):
                    apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values, before)

    def test_restore_rejects_modified_manifest_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            backup = apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            manifest_file = backup / "manifest.json"
            content = json.loads(manifest_file.read_text())
            content["changes"][0]["key"] = "/unrelated/user-setting"
            manifest_file.write_text(json.dumps(content))
            before = fake.values.copy()
            with self.assertRaisesRegex(RiceError, "Invalid Rice backup"):
                restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values, before)

    def test_missing_wallpaper_properties_prevents_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            fake.wallpaper_keys = lambda: (_ for _ in ()).throw(RiceError("No wallpaper properties"))
            setup_apps(root / "config")
            with self.assertRaisesRegex(RiceError, "No wallpaper properties"):
                apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertFalse(fake.calls)


if __name__ == "__main__":
    unittest.main()
