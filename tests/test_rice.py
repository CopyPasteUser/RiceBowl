"""Simulated XFCE desktop: never touch the test runner's desktop or dconf."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.rice import RiceError, XfceBackend, apply, plan, restore
from macrice.thunar import plan_css


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

    def get_optional(self, kind, channel, key):
        return self.values.get((kind, channel, key))

    def set(self, kind, channel, key, value, *, create=False):
        if key == self.fail_key:
            raise RiceError("Injected write failure")
        if not create and (kind, channel, key) not in self.values:
            raise RiceError("Missing property; should have been created")
        self.values[(kind, channel, key)] = value
        self.calls.append((kind, channel, key, value))

    def reset(self, kind, channel, key):
        del self.values[(kind, channel, key)]
        self.calls.append((kind, channel, key, None))

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
            self.assertEqual(next(c["after"] for c in changes if c["key"] == "/general/button_layout"), "O|HMC")
            self.assertEqual(next(c["after"] for c in changes if c["key"] == "theme"), "'MacRice-Frost'")
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
            self.assertEqual(fake.get("gsettings", "plank", "theme"), "'MacRice-Frost'")
            self.assertEqual(fake.get("xfconf", "thunar", "/last-location-bar"), "ThunarLocationButtons")
            self.assertTrue((root / "data/plank/themes/MacRice-Frost/dock.theme").is_file())
            self.assertIn("MacRice Thunar: begin", (root / "config/gtk-3.0/gtk.css").read_text())
            wallpaper = Path(fake.get("xfconf", "xfce4-desktop", WALL))
            self.assertTrue(wallpaper.is_file())
            menu = root / "config/macmenu/settings.json"
            settings = json.loads(menu.read_text())
            self.assertEqual(settings["theme"], "dark")
            self.assertEqual(json.loads((root / "config/macbar/config.json").read_text())["theme"], "light")
            settings["favorites"].append("added-after-apply")
            menu.write_text(json.dumps(settings))

            restored = restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(restored, backup)
            self.assertEqual(fake.values, before)
            self.assertFalse((root / "config/gtk-3.0/gtk.css").exists())
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
            with mock.patch("macrice.rice.set_theme_values", side_effect=ValueError("broken app preferences")):
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

    def test_day_uses_dark_top_bar_dark_plank_and_light_thunar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values[("gsettings", "plank", "theme")], "'MacRice-Obsidian'")
            self.assertEqual(json.loads((root / "config/macbar/config.json").read_text())["theme"], "dark")
            self.assertIn("#e9edf3", (root / "config/gtk-3.0/gtk.css").read_text())

    def test_thunar_css_keeps_existing_custom_rules_and_restores_exact_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            css = root / "config/gtk-3.0/gtk.css"
            css.parent.mkdir(parents=True)
            original = "/* my personal rules */\nbutton { border-radius: 3px; }\n"
            css.write_text(original)
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertTrue(css.read_text().startswith(original))
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(css.read_text(), original)

    def test_thunar_css_conflict_protects_user_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            css = root / "config/gtk-3.0/gtk.css"
            css.write_text(css.read_text() + "\n/* changed manually */\n")
            before = fake.values.copy()
            with self.assertRaisesRegex(RiceError, "Thunar CSS changed"):
                restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values, before)

    def test_plank_theme_collision_preflight_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            target = root / "data/plank/themes/MacRice-Frost/dock.theme"
            target.parent.mkdir(parents=True)
            target.write_text("someone else's theme")
            with self.assertRaisesRegex(RiceError, "conflicts"):
                apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(target.read_text(), "someone else's theme")
            self.assertEqual(fake.calls, [])

    def test_thunar_absent_preferences_are_removed_on_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            before = fake.values.copy()
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertIn(("xfconf", "thunar", "/last-view"), fake.values)
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values, before)

    def test_night_day_night_roundtrip_keeps_single_thunar_css_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            original = fake.values.copy()
            night = apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            night_css = (root / "config/gtk-3.0/gtk.css").read_text()
            day = apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            day_css = (root / "config/gtk-3.0/gtk.css").read_text()
            self.assertEqual(day_css.count("MacRice Thunar: begin"), 1)
            self.assertEqual(plan_css("day", root / "config")["after"], day_css)
            self.assertEqual(fake.values[("gsettings", "plank", "theme")], "'MacRice-Obsidian'")
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), day)
            self.assertEqual((root / "config/gtk-3.0/gtk.css").read_text(), night_css)
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), night)
            self.assertEqual(fake.values, original)
            self.assertFalse((root / "config/gtk-3.0/gtk.css").exists())

    def test_malformed_css_marker_stops_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            css = root / "config/gtk-3.0/gtk.css"
            css.parent.mkdir(parents=True)
            css.write_text("/* MacRice Thunar: begin */\n")
            with self.assertRaisesRegex(RiceError, "incomplete"):
                apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.calls, [])

    def test_failed_second_apply_cannot_mask_valid_first_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            original = fake.values.copy()
            night = apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            fake.fail_key = WALL
            with self.assertRaisesRegex(RiceError, "rolled back"):
                apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            fake.fail_key = None
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), night)
            self.assertEqual(fake.values, original)

    def test_reapplying_refuses_modified_managed_thunar_css(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            css = root / "config/gtk-3.0/gtk.css"
            css.write_text(css.read_text().replace("#19212d", "#123456"))
            state = fake.values.copy()
            with self.assertRaisesRegex(RiceError, "customized"):
                apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values, state)


if __name__ == "__main__":
    unittest.main()
