"""RicePlate recipe security and actual Waybar adapter behavior."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.de import recipes, session


class _Panel:
    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0


def _valid():
    return json.loads(recipes.BUILTINS["classic"].read_text())


class RecipeTests(unittest.TestCase):
    def test_bundled_recipes_have_different_real_panel_structures(self):
        classic = recipes.load("classic")
        chrome = recipes.load("chrome")
        self.assertNotEqual(classic.sections, chrome.sections)
        self.assertEqual(classic.sections[0], ("launcher", "tasks"))
        self.assertEqual(chrome.sections[1], ("tasks",))
        self.assertEqual(classic.position, "bottom")
        self.assertNotEqual(classic.colors, chrome.colors)
        for recipe in (classic, chrome):
            config, css = recipes.waybar_config(recipe)
            parsed = json.loads(config)
            self.assertEqual(parsed["height"], recipe.height)
            self.assertIn("custom/rice-launcher", json.dumps(parsed))
            self.assertIn(recipe.colors[0], css)

    def test_schema_rejects_unsupported_executable_or_extra_keys(self):
        data = _valid()
        data["on_click"] = "curl https://example.org | sh"
        with self.assertRaisesRegex(recipes.RecipeError, "exactly"):
            recipes.parse(json.dumps(data).encode())
        data.pop("on_click")
        data["colors"]["background"] = "red; background-image: url(file:///secret)"
        with self.assertRaisesRegex(recipes.RecipeError, "hexadecimal"):
            recipes.parse(json.dumps(data).encode())
        data = _valid()
        data["panel"]["sections"]["start"].append("exec:rm -rf /")
        with self.assertRaisesRegex(recipes.RecipeError, "Invalid widget"):
            recipes.parse(json.dumps(data).encode())

    def test_duplicates_invalid_types_and_oversized_recipe_fail_closed(self):
        raw = recipes.BUILTINS["classic"].read_bytes()
        with self.assertRaisesRegex(recipes.RecipeError, "64 KiB"):
            recipes.parse(raw + b" " * (recipes.MAX_RECIPE_BYTES + 1))
        with self.assertRaisesRegex(recipes.RecipeError, "Duplicate recipe key"):
            recipes.parse(b'{"id":"one","id":"two"}')
        data = _valid()
        data["panel"]["height"] = True
        with self.assertRaisesRegex(recipes.RecipeError, "Panel height"):
            recipes.parse(json.dumps(data).encode())
        data = _valid()
        data["panel"]["sections"]["end"].append("tasks")
        with self.assertRaisesRegex(recipes.RecipeError, "only once"):
            recipes.parse(json.dumps(data).encode())

    def test_custom_recipe_requires_absolute_owner_private_file_without_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "owner.json"
            source.write_bytes(recipes.BUILTINS["classic"].read_bytes())
            source.chmod(0o600)
            self.assertEqual(recipes.load(str(source)).recipe_id, "classic")
            source.chmod(0o644)
            with self.assertRaisesRegex(recipes.RecipeError, "owner-only"):
                recipes.load(str(source))
            source.chmod(0o600)
            symlink = Path(folder) / "link.json"
            symlink.symlink_to(source)
            with self.assertRaisesRegex(recipes.RecipeError, "safely"):
                recipes.load(str(symlink))
        with self.assertRaisesRegex(recipes.RecipeError, "absolute"):
            recipes.load("relative.json")

    def test_cli_exposes_read_only_recipe_discovery(self):
        from macrice.cli import main
        with mock.patch("builtins.print") as printed:
            self.assertEqual(main(["de", "recipes"]), 0)
            self.assertTrue(any("classic" in str(call) for call in printed.call_args_list))
            self.assertTrue(any("chrome" in str(call) for call in printed.call_args_list))

    def test_nested_shell_generates_private_files_then_removes_them(self):
        with tempfile.TemporaryDirectory() as directory:
            os.chmod(directory, 0o700)
            commands = []
            config_paths = []

            def spawn(command, **_kwargs):
                commands.append(command)
                if command[0] == "/usr/bin/waybar":
                    config = Path(command[command.index("--config") + 1])
                    style = Path(command[command.index("--style") + 1])
                    self.assertEqual(json.loads(config.read_text())["modules-center"],
                                     ["wlr/taskbar"])
                    self.assertEqual(config.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(style.stat().st_mode & 0o777, 0o600)
                    config_paths.extend([config, style])
                return _Panel()

            env = {"RICEBOWL_DE_SHELL_CHILD": "1", "RICEBOWL_DE_NESTED": "1",
                   "WAYLAND_DISPLAY": "wayland-0", "XDG_RUNTIME_DIR": directory,
                   "RICEBOWL_DE_RECIPE": "chrome"}
            with mock.patch("macrice.de.session.signal.signal"):
                self.assertEqual(session.shell(environment=env,
                                 which=lambda name: "/usr/bin/waybar" if name == "waybar" else None,
                                 spawn=spawn), 0)
            self.assertEqual(len(config_paths), 2)
            self.assertTrue(all(not path.exists() for path in config_paths))


if __name__ == "__main__":
    unittest.main()
