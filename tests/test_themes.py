import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from macrice.environment import DesktopProfile
from macrice.themes import PRESETS, apply_preset, preset_values


class ThemesTests(unittest.TestCase):
    def test_new_presets_have_consistent_three_app_values(self):
        for preset in ("Liquid Glass", "Liquid Glass Dark", "Classic Aqua"):
            self.assertIn(preset, PRESETS)
            values = preset_values(preset)
            self.assertEqual(set(values), {"MacMenu", "Control Center", "MacBar"})
        self.assertEqual(preset_values("Liquid Glass Dark")["MacBar"], "glass-light")

    def test_system_preset_tracks_gtk_darkness(self):
        profile = DesktopProfile("XFCE", "WhiteSur-Dark", "WhiteSur", "Bibata", "WhiteSur", None, None)
        self.assertEqual(
            preset_values("System", profile),
            {"MacMenu": "system", "Control Center": "midnight", "MacBar": "dark"},
        )
        self.assertEqual(preset_values("Light")["Control Center"], "light")
        with self.assertRaises(ValueError):
            preset_values("Unknown")

    def test_updates_only_theme_with_recoverable_private_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            configs = base / "config"
            data = base / "data"
            for directory_name, filename, contents in (
                ("macmenu", "settings.json", {"theme": "light", "favorites": ["org.xfce.Thunar"]}),
                ("macos-control-center", "config.json", {"theme": "light", "devices": [{"name": "test"}]}),
                ("macbar", "config.json", {"theme": "light", "height": 30}),
            ):
                path = configs / directory_name / filename
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(contents), encoding="utf-8")

            backup = apply_preset("Midnight", config_root=configs, data_root=data)
            self.assertTrue(backup.is_dir())
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
            menu = json.loads((configs / "macmenu/settings.json").read_text())
            self.assertEqual(menu["favorites"], ["org.xfce.Thunar"])
            self.assertEqual(menu["theme"], "dark")
            self.assertEqual(json.loads((configs / "macos-control-center/config.json").read_text())["theme"], "midnight")
            self.assertEqual(json.loads((configs / "macbar/config.json").read_text())["height"], 30)
            self.assertEqual(json.loads((backup / "macmenu/settings.json").read_text())["theme"], "light")
            self.assertEqual(stat.S_IMODE((configs / "macmenu/settings.json").stat().st_mode), 0o600)

    def test_invalid_preferences_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            damaged = base / "config" / "macmenu" / "settings.json"
            damaged.parent.mkdir(parents=True)
            damaged.write_text("{this is not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                apply_preset("Light", config_root=base / "config", data_root=base / "data")
            self.assertEqual(damaged.read_text(), "{this is not json")
            self.assertFalse((base / "config" / "macbar").exists())

    def test_symlinked_preferences_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            original = base / "outside.json"
            original.write_text('{"theme":"light"}')
            target = base / "config" / "macmenu/settings.json"
            target.parent.mkdir(parents=True)
            target.symlink_to(original)
            with self.assertRaises(ValueError):
                apply_preset("Light", config_root=base / "config", data_root=base / "data")
            self.assertEqual(original.read_text(), '{"theme":"light"}')


if __name__ == "__main__":
    unittest.main()
