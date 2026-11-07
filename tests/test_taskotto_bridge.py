"""Contract tests for RiceBowl's optional Taskotto v1 TOML handoff."""

import dataclasses
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.de import recipes, taskotto


FIXTURE = Path(__file__).parent / "fixtures/taskotto-classic-v1.toml"


class TaskottoBridgeTests(unittest.TestCase):
    def test_classic_fixture_is_reproducible_versioned_data(self):
        content = taskotto.render(recipes.load("classic"))
        self.assertEqual(content, FIXTURE.read_bytes())
        self.assertIn(b"format_version = 1\n", content)
        self.assertIn(b'base_theme = "system"\n', content)
        self.assertIn(b'accent = "#4179aa"\n', content)
        self.assertIn(b'surface = "#203c59"\n', content)
        self.assertIn(b'text = "#f3f7fa"\n', content)

    def test_only_known_wallpapers_select_historical_rice(self):
        generic = recipes.load("classic")
        for wallpaper, theme in taskotto.WALLPAPER_THEME.items():
            recipe = dataclasses.replace(generic, wallpaper=wallpaper)
            self.assertIn(f'base_theme = "{theme}"\n'.encode(), taskotto.render(recipe))
        self.assertIn(b'base_theme = "chromeos"\n', taskotto.render(recipes.load("chrome")))
        self.assertIn(b'base_theme = "system"\n', taskotto.render(
            dataclasses.replace(generic, wallpaper=None)))

    def test_export_is_owner_only_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "taskotto-rice.toml"
            result = taskotto.export("classic", output)
            self.assertEqual(result.recipe_id, "classic")
            self.assertEqual(output.read_bytes(), FIXTURE.read_bytes())
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                taskotto.export("chrome", output)
            self.assertEqual(output.read_bytes(), FIXTURE.read_bytes())
            with self.assertRaisesRegex(recipes.RecipeError, "absolute .toml"):
                taskotto.export("classic", Path("relative.toml"))

    def test_cli_exports_and_rejects_incompatible_options(self):
        from macrice.cli import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.toml"
            with mock.patch("builtins.print"):
                self.assertEqual(main(["de", "taskotto-export", "--recipe", "classic",
                                       "--output", str(path)]), 0)
            self.assertEqual(path.read_bytes(), FIXTURE.read_bytes())
            with mock.patch("sys.stderr"):
                self.assertEqual(main(["de", "taskotto-export", "--recipe", "classic",
                                       "--output", str(path), "--nested"]), 1)
                self.assertEqual(main(["de", "taskotto-export", "--recipe", "classic",
                                       "--output", str(path)]), 1)


if __name__ == "__main__":
    unittest.main()
