"""Private, reversible Wayland recipe selection without active-desktop changes."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.de import recipes, session


class _Executed(Exception):
    def __init__(self, args, environment):
        self.args = args
        self.environment = environment


def _capture(_program, arguments, environment):
    raise _Executed(arguments, environment)


class RecipeSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "config"
        self.config.mkdir(mode=0o700)
        environment = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.config)})
        environment.start()
        self.addCleanup(environment.stop)

    def _import(self, recipe_id="user-rice"):
        source = self.root / "source.json"
        data = json.loads(recipes.BUILTINS["chrome"].read_text())
        data["id"] = recipe_id
        source.write_text(json.dumps(data), encoding="utf-8")
        source.chmod(0o600)
        return recipes.import_recipe(source)[1]

    def test_initial_read_only_state_creates_nothing(self):
        self.assertEqual(recipes.current_selection(), ("classic", None))
        self.assertIsNone(recipes.selected_recipe())
        self.assertFalse((self.config / "ricebowl").exists())

    def test_select_restore_and_repeat_preserve_previous(self):
        installed = self._import()
        self.assertEqual(recipes.change_selection("user-rice"), ("user-rice", "classic"))
        self.assertEqual(recipes.current_selection(), ("user-rice", "classic"))
        self.assertEqual(recipes.selected_recipe(), "user-rice")
        self.assertEqual(recipes.change_selection("user-rice"), ("user-rice", "user-rice"))
        self.assertEqual(recipes.change_selection(restore=True), ("classic", "user-rice"))
        self.assertEqual(recipes.current_selection(), ("classic", "user-rice"))
        self.assertEqual(recipes.change_selection(restore=True), ("user-rice", "classic"))
        self.assertEqual(installed.read_bytes(), (self.root / "source.json").read_bytes())
        state = self.config / "ricebowl" / "recipes" / ".active-recipe"
        self.assertEqual(state.stat().st_mode & 0o777, 0o600)
        lock = state.with_name(".active-recipe.lock")
        self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
        self.assertEqual([item.recipe_id for item, _ in recipes.imported_recipes()], ["user-rice"])

    def test_invalid_or_missing_target_does_not_clobber_selected_recipe(self):
        self._import()
        recipes.change_selection("user-rice")
        for invalid in ("../escape", "/tmp/untrusted.json", "not-imported"):
            with self.subTest(invalid=invalid), self.assertRaises(recipes.RecipeError):
                recipes.change_selection(invalid)
            self.assertEqual(recipes.current_selection(), ("user-rice", "classic"))

    def test_corrupted_or_symlinked_selection_is_rejected_without_overwrite(self):
        self._import()
        directory = self.config / "ricebowl" / "recipes"
        state = directory / ".active-recipe"
        state.write_text("{not-json}", encoding="utf-8")
        state.chmod(0o600)
        with self.assertRaisesRegex(recipes.RecipeError, "Invalid selected"):
            recipes.current_selection()
        with self.assertRaisesRegex(recipes.RecipeError, "Invalid selected"):
            recipes.change_selection("user-rice")
        self.assertEqual(state.read_text(), "{not-json}")
        state.unlink()
        source = self.root / "important.txt"
        source.write_text("keep me", encoding="utf-8")
        state.symlink_to(source)
        with self.assertRaisesRegex(recipes.RecipeError, "safely"):
            recipes.current_selection()
        self.assertEqual(source.read_text(), "keep me")

    def test_cli_selection_is_explicit_and_reversible(self):
        from macrice.cli import main
        self._import()
        with mock.patch("builtins.print") as printed:
            self.assertEqual(main(["de", "recipe-select", "--recipe", "user-rice"]), 0)
            self.assertIn("current session unchanged", str(printed.call_args))
            self.assertEqual(main(["de", "recipe-current", "--json"]), 0)
            self.assertEqual(json.loads(printed.call_args.args[0])["active"], "user-rice")
            self.assertEqual(main(["de", "recipe-restore"]), 0)
        self.assertEqual(recipes.current_selection(), ("classic", "user-rice"))
        with mock.patch("sys.stderr"):
            self.assertEqual(main(["de", "recipe-select", "--recipe", "/tmp/panel.json"]), 1)
            self.assertEqual(main(["de", "recipe-restore", "--recipe", "classic"]), 1)

    def test_wayland_start_inherits_selected_recipe_and_recovers_if_missing(self):
        installed = self._import()
        recipes.change_selection("user-rice")
        runtime = self.root / "runtime"
        runtime.mkdir(mode=0o700)
        env = {"XDG_RUNTIME_DIR": str(runtime), "DBUS_SESSION_BUS_ADDRESS": "unix:path=fake"}
        for desired in (str(installed), None):
            with self.subTest(desired=desired):
                with self.assertRaises(_Executed) as caught:
                    session.start(nested=True, environment=env, which=lambda name: f"/usr/bin/{name}",
                                  execute=_capture)
                self.assertEqual(caught.exception.environment.get("RICEBOWL_DE_RECIPE"), desired)
            if desired:
                installed.unlink()  # Simulate removing an imported file outside RiceBowl.

    def test_corrupted_saved_preference_falls_back_but_bad_explicit_recipe_fails(self):
        self._import()
        recipes.change_selection("user-rice")
        state = self.config / "ricebowl" / "recipes" / ".active-recipe"
        state.write_text("not-json", encoding="utf-8")
        runtime = self.root / "runtime"
        runtime.mkdir(mode=0o700)
        env = {"XDG_RUNTIME_DIR": str(runtime), "DBUS_SESSION_BUS_ADDRESS": "unix:path=fake"}
        with mock.patch("sys.stderr"), self.assertRaises(_Executed) as caught:
            session.start(nested=True, environment=env, which=lambda name: f"/usr/bin/{name}",
                          execute=_capture)
        self.assertNotIn("RICEBOWL_DE_RECIPE", caught.exception.environment)
        with self.assertRaises(recipes.RecipeError):
            session.start(nested=True, recipe="nonexistent-id", environment=env,
                          which=lambda name: f"/usr/bin/{name}", execute=_capture)


if __name__ == "__main__":
    unittest.main()
