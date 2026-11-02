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
    def test_liquid_glass_has_distinct_dock_assets(self):
        from macrice.rice import STYLES
        from macrice.installer import project_root
        for glass, standard in (("glass-night", "night"), ("glass-day", "day")):
            with self.subTest(glass=glass):
                self.assertNotEqual(STYLES[glass].plank_theme, STYLES[standard].plank_theme)
                glass_file = project_root() / "assets/plank-themes" / STYLES[glass].plank_theme / "dock.theme"
                standard_file = project_root() / "assets/plank-themes" / STYLES[standard].plank_theme / "dock.theme"
                self.assertTrue(glass_file.is_file())
                self.assertNotEqual(glass_file.read_bytes(), standard_file.read_bytes())

    def test_additional_full_rice_themes_switch_and_restore(self):
        from macrice.rice import STYLES
        for style in ("glass-night", "glass-day", "aqua"):
            with self.subTest(style=style), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fake = FakeBackend()
                setup_apps(root / "config")
                old = fake.values.copy()
                backup = apply(style, backend=fake, data_root=root / "data", config_root=root / "config")
                self.assertEqual(fake.values[("gsettings", "plank", "theme")], f"'{STYLES[style].plank_theme}'")
                self.assertEqual(json.loads((root / "config/macbar/config.json").read_text())["theme"], STYLES[style].bar_theme)
                self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), backup)
                self.assertEqual(fake.values, old)

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
            self.assertEqual(next(c["after"] for c in changes if c["key"] == "theme"), "'MacRice-Frost-Glass'")
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
            self.assertEqual(fake.get("gsettings", "plank", "theme"), "'MacRice-Frost-Glass'")
            self.assertEqual(fake.get("xfconf", "thunar", "/last-location-bar"), "ThunarLocationButtons")
            self.assertTrue((root / "data/plank/themes/MacRice-Frost-Glass/dock.theme").is_file())
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

    def test_restore_keeps_later_customization_but_recovers_other_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            before = fake.values.copy()
            backup = apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            fake.values[("gsettings", "plank", "icon-size")] = "48"
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), backup)
            self.assertEqual(fake.values[("gsettings", "plank", "icon-size")], "48")
            self.assertEqual(fake.values[("xfconf", "xsettings", "/Net/ThemeName")], before[("xfconf", "xsettings", "/Net/ThemeName")])
            self.assertEqual(fake.values[("gsettings", "plank", "theme")], before[("gsettings", "plank", "theme")])
            self.assertIn("plank:icon-size", json.loads((backup / "skipped.json").read_text()))

    def test_thunar_view_change_no_longer_blocks_day_to_night_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            original_night = fake.values.copy()
            day = apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            fake.values[("xfconf", "thunar", "/last-view")] = "ThunarDetailsView"
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.get("xfconf", "xsettings", "/Net/ThemeName"), "WhiteSur-Dark")
            self.assertEqual(fake.get("gsettings", "plank", "theme"), "'MacRice-Frost-Glass'")
            self.assertEqual(fake.get("xfconf", "thunar", "/last-view"), "ThunarDetailsView")
            self.assertEqual(fake.get("xfconf", "xfce4-desktop", WALL), original_night[("xfconf", "xfce4-desktop", WALL)])
            self.assertIn("thunar:/last-view", json.loads((day / "skipped.json").read_text()))

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
            self.assertEqual(fake.values[("gsettings", "plank", "theme")], "'MacRice-Obsidian-Glass'")
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

    def test_thunar_css_external_edits_are_preserved_during_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            css = root / "config/gtk-3.0/gtk.css"
            css.write_text(css.read_text() + "\n/* changed manually */\n")
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertIn("/* changed manually */", css.read_text())
            self.assertNotIn("MacRice Thunar: begin", css.read_text())
            self.assertEqual(fake.values[("xfconf", "xsettings", "/Net/ThemeName")], "WhiteSur-Dark")

    def test_modified_macrice_css_block_skipped_without_locking_desktop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            backup = apply("day", backend=fake, data_root=root / "data", config_root=root / "config")
            css = root / "config/gtk-3.0/gtk.css"
            css.write_text(css.read_text().replace("#e9edf3", "#ccddee"))
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertIn("#ccddee", css.read_text())
            self.assertEqual(fake.values[("xfconf", "xsettings", "/Net/ThemeName")], "WhiteSur-Dark")
            self.assertIn("Thunar CSS", " ".join(json.loads((backup / "skipped.json").read_text())))

    def test_plank_theme_from_older_release_does_not_block_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            target = root / "data/plank/themes/MacRice-Frost-Glass/dock.theme"
            target.parent.mkdir(parents=True)
            target.write_text("older or customized Plank artwork")
            old = fake.values.copy()
            backup = apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            chosen = fake.get("gsettings", "plank", "theme").strip("'")
            self.assertRegex(chosen, r"^MacRice-Frost-Glass-[0-9a-f]{12}$")
            from macrice.installer import project_root
            source = project_root() / "assets/plank-themes/MacRice-Frost-Glass/dock.theme"
            self.assertEqual((root / "data/plank/themes" / chosen / "dock.theme").read_bytes(), source.read_bytes())
            self.assertEqual(target.read_text(), "older or customized Plank artwork")
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), backup)
            self.assertEqual(fake.values, old)
            self.assertEqual(target.read_text(), "older or customized Plank artwork")
            repeated = apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.get("gsettings", "plank", "theme"), f"'{chosen}'")
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertTrue((repeated / "restored").is_file())

    def test_repeated_plank_collisions_preserve_all_old_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            base = root / "data/plank/themes/RiceHub-Aero-Glass/dock.theme"
            base.parent.mkdir(parents=True)
            base.write_text("old")
            from macrice.installer import project_root
            import hashlib
            source = project_root() / "assets/plank-themes/RiceHub-Aero-Glass/dock.theme"
            name = f"RiceHub-Aero-Glass-{hashlib.sha256(source.read_bytes()).hexdigest()[:12]}"
            versioned = base.parent.parent / name / "dock.theme"
            versioned.parent.mkdir()
            versioned.write_text("user edited even the versioned name")
            expected = base.parent.parent / (name + "-1") / "dock.theme"
            changes, _, _, _ = plan("aero-meadow", backend=fake, data_root=root / "data", config_root=root / "config")
            selected = next(c["after"] for c in changes if c["kind"] == "gsettings" and c["key"] == "theme")
            self.assertEqual(selected, f"'{name}-1'")
            self.assertFalse(expected.exists())
            backup = apply("aero-meadow", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.get("gsettings", "plank", "theme"), f"'{name}-1'")
            self.assertEqual(expected.read_bytes(), source.read_bytes())
            self.assertEqual(base.read_text(), "old")
            self.assertEqual(versioned.read_text(), "user edited even the versioned name")
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertTrue((backup / "restored").exists())
            self.assertEqual(base.read_text(), "old")
            self.assertEqual(versioned.read_text(), "user edited even the versioned name")

    def test_plank_existing_empty_theme_folder_is_not_claimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            existing = root / "data/plank/themes/MacRice-Frost-Glass"
            existing.mkdir(parents=True)
            (existing / "user-note").write_text("keep me")
            backup = apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertRegex(fake.get("gsettings", "plank", "theme"), r"^'MacRice-Frost-Glass-[a-f0-9]{12}'$")
            self.assertFalse((existing / "dock.theme").exists())
            self.assertEqual((existing / "user-note").read_text(), "keep me")
            restore(backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertTrue((backup / "restored").exists())

    def test_exhausted_plank_names_fail_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            from macrice.installer import project_root
            import hashlib
            source = project_root() / "assets/plank-themes/RiceHub-Aero-Glass/dock.theme"
            digest = hashlib.sha256(source.read_bytes()).hexdigest()[:12]
            theme_root = root / "data/plank/themes"
            names = ["RiceHub-Aero-Glass", f"RiceHub-Aero-Glass-{digest}"]
            names.extend(f"RiceHub-Aero-Glass-{digest}-{i}" for i in range(1, 33))
            for name in names:
                folder = theme_root / name
                folder.mkdir(parents=True)
                (folder / "dock.theme").write_text("preserve existing copy")
            with self.assertRaisesRegex(RiceError, "No free Plank theme name"):
                apply("aero-meadow", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.calls, [])
            self.assertFalse((root / "data/macrice-state").exists())

    def test_plank_symlinked_theme_is_preserved_and_not_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            outside = root / "personal-theme"
            outside.mkdir()
            (outside / "dock.theme").write_text("personal")
            parent = root / "data/plank/themes"
            parent.mkdir(parents=True)
            (parent / "RiceHub-Aero-Glass").symlink_to(outside, target_is_directory=True)
            apply("aero-meadow", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertRegex(fake.get("gsettings", "plank", "theme"), r"^'RiceHub-Aero-Glass-[a-f0-9]{12}'$")
            self.assertEqual((outside / "dock.theme").read_text(), "personal")

    def test_plank_shared_symlinked_parent_still_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            (root / "data/plank").mkdir(parents=True)
            (root / "data/plank/themes").symlink_to(root / "outside", target_is_directory=True)
            with self.assertRaisesRegex(RiceError, "Unmanaged Plank theme directory"):
                apply("aero-meadow", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.calls, [])

    def test_switch_all_families_preserves_plank_pins_and_restore_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            config = root / "config"
            data = root / "data"
            setup_apps(config)
            pin = config / "plank/dock1/launchers/personal-app.dockitem"
            pin.parent.mkdir(parents=True)
            pin.write_text("[PlankDockItemPreferences]\nLauncher=file:///my/app.desktop\n")
            original = fake.values.copy()
            snapshots = []
            for name, shell, position in (("night", None, "'bottom'"),
                                          ("aero-meadow", "aero", "'left'"),
                                          ("ten-light", "ten", "'left'"),
                                          ("glass-day", None, "'bottom'")):
                before = fake.values.copy()
                backup = apply(name, backend=fake, data_root=data, config_root=config)
                snapshots.append((backup, before))
                self.assertEqual(fake.get("gsettings", "plank", "position"), position)
                manifest = json.loads((backup / "manifest.json").read_text())
                for family in ("aero", "ten"):
                    content = manifest["shell_autostarts"][family]["after"]
                    self.assertEqual(content is not None, family == shell)
                self.assertIn("/my/app.desktop", pin.read_text())
            for backup, previous in reversed(snapshots):
                self.assertEqual(restore(backend=fake, data_root=data, config_root=config), backup)
                self.assertEqual(fake.values, previous)
            self.assertEqual(fake.values, original)
            self.assertIn("/my/app.desktop", pin.read_text())

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
            self.assertEqual(fake.values[("gsettings", "plank", "theme")], "'MacRice-Obsidian-Glass'")
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), day)
            self.assertEqual((root / "config/gtk-3.0/gtk.css").read_text(), night_css)
            self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), night)
            self.assertEqual(fake.values, original)
            self.assertFalse((root / "config/gtk-3.0/gtk.css").exists())

    def test_upgrade_from_original_plank_themes_does_not_block_switch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            old = root / "data/plank/themes/MacRice-Obsidian/dock.theme"
            old.parent.mkdir(parents=True)
            old.write_text("Older MacRice dock theme left untouched")
            fake.values[("gsettings", "plank", "theme")] = "'MacRice-Obsidian'"
            apply("night", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.values[("gsettings", "plank", "theme")], "'MacRice-Frost-Glass'")
            self.assertEqual(old.read_text(), "Older MacRice dock theme left untouched")

    def test_glass_docks_use_subtle_alpha_below_old_opaque_levels(self):
        from macrice.installer import project_root
        for name in ("MacRice-Frost-Glass", "MacRice-Obsidian-Glass"):
            contents = (project_root() / "assets/plank-themes" / name / "dock.theme").read_text()
            for row in contents.splitlines():
                if row.startswith(("FillStartColor=", "FillEndColor=")):
                    alpha = int(row.split(";;")[-1])
                    self.assertGreaterEqual(alpha, 180)
                    self.assertLessEqual(alpha, 210)

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
