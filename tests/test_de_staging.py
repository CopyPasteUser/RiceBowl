"""Reviewed Creator next-login staging, conflict detection and one-step undo."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.cli import main as cli
from macrice.de import catalog, creator_contract, recipes, review, staging


def _private_recipe(path: Path, recipe_id: str = "author-made") -> Path:
    data = json.loads(recipes.BUILTINS["chrome"].read_text())
    data["id"] = recipe_id
    data["name"] = "Author's panel"
    path.write_text(json.dumps(data))
    path.chmod(0o600)
    return path


class CreatorStagingTests(unittest.TestCase):
    def test_status_is_read_only_and_truthful_before_any_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "unused"
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}), \
                 mock.patch("macrice.de.session.start") as startup:
                result = staging.status()
            self.assertEqual(result["next_session"], "classic")
            self.assertFalse(result["can_restore"])
            self.assertEqual(result["semantic_sha256"],
                             review.review("classic")["summary"]["semantic_sha256"])
            self.assertFalse(config.exists())
            startup.assert_not_called()

    def test_review_stage_status_and_rollback_are_one_explicit_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir(mode=0o700)
            source = _private_recipe(root / "owner.json")
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}), \
                 mock.patch("macrice.de.session.start") as startup:
                recipes.import_recipe(source)
                digest = review.review("author-made")["summary"]["semantic_sha256"]
                staged = staging.stage("author-made", digest, expected_active="classic")
                self.assertTrue(staged["changed"])
                self.assertFalse(staged["applied"])
                self.assertEqual(staging.status()["next_session"], "author-made")
                self.assertTrue(staging.status()["can_restore"])
                self.assertEqual(recipes.current_selection(), ("author-made", "classic"))
                self.assertEqual(staging.status()["semantic_sha256"], digest)
                # The selected recipe is pinned for the next session, not just
                # compared once during the stage command.
                selection = json.loads((config / "ricebowl" / "recipes" / ".active-recipe").read_text())
                self.assertEqual(selection["schema_version"], 2)
                self.assertEqual(selection["active_sha256"], digest)
                self.assertEqual(recipes.selected_recipe(), "author-made")
                # Repeating the same stage preserves the previous rollback target.
                repeated = staging.stage("author-made", digest, expected_active="author-made")
                self.assertFalse(repeated["changed"])
                self.assertEqual(recipes.current_selection()[1], "classic")
                result = staging.rollback(expected_active="author-made")
                self.assertEqual(result["next_session"], "classic")
                self.assertTrue(result["changed"])
                self.assertEqual(recipes.current_selection(), ("classic", "author-made"))
                lock = config / "ricebowl" / "recipes" / ".active-recipe"
                self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
            startup.assert_not_called()
            self.assertTrue(source.exists())

    def test_conflict_and_stale_review_never_mutate_existing_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir(mode=0o700)
            source = _private_recipe(root / "source.json")
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                recipes.import_recipe(source)
                digest = review.review("author-made")["summary"]["semantic_sha256"]
                with self.assertRaises(staging.StageError) as error:
                    staging.stage("author-made", digest, expected_active="chrome")
                self.assertEqual(error.exception.code, "selection_conflict")
                self.assertEqual(recipes.current_selection(), ("classic", None))
                installed = config / "ricebowl" / "recipes" / "author-made.json"
                changed = json.loads(installed.read_text())
                changed["panel"]["height"] = 48
                installed.write_text(json.dumps(changed))
                installed.chmod(0o600)
                with self.assertRaises(staging.StageError) as error:
                    staging.stage("author-made", digest, expected_active="classic")
                self.assertEqual(error.exception.code, "recipe_changed")
                self.assertEqual(recipes.current_selection(), ("classic", None))
                with self.assertRaises(staging.StageError) as error:
                    staging.stage("author-made", "0" * 64)
                self.assertEqual(error.exception.code, "recipe_changed")
                digest = review.review("author-made")["summary"]["semantic_sha256"]
                staging.stage("author-made", digest)
                with self.assertRaises(staging.StageError) as error:
                    staging.rollback(expected_active="chrome")
                self.assertEqual(error.exception.code, "selection_conflict")
                self.assertEqual(recipes.current_selection(), ("author-made", "classic"))

    def test_staged_recipe_modified_after_review_is_rejected_at_next_login(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir(mode=0o700)
            source = _private_recipe(root / "source.json")
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                recipes.import_recipe(source)
                digest = review.review("author-made")["summary"]["semantic_sha256"]
                staging.stage("author-made", digest)
                installed = config / "ricebowl" / "recipes" / "author-made.json"
                changed = json.loads(installed.read_text())
                changed["colors"]["background"] = "#010203"
                installed.write_text(json.dumps(changed))
                installed.chmod(0o600)
                self.assertEqual(recipes.current_selection()[0], "author-made")
                with self.assertRaises(recipes.RecipeFingerprintMismatch):
                    recipes.selected_recipe()
                with self.assertRaises(staging.StageError) as error:
                    staging.status()
                self.assertEqual(error.exception.code, "invalid_selection_state")
                self.assertEqual(staging.rollback()["next_session"], "classic")
                self.assertEqual(recipes.selected_recipe(), "classic")

    def test_malformed_hash_and_missing_previous_rejected_without_change(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.mkdir(mode=0o700)
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                for digest in ("", "A" * 64, "0" * 63, "0" * 65):
                    with self.subTest(digest=digest), self.assertRaises(staging.StageError):
                        staging.stage("classic", digest)
                    self.assertEqual(recipes.current_selection(), ("classic", None))
                with self.assertRaises(staging.StageError) as error:
                    staging.rollback()
                self.assertEqual(error.exception.code, "rollback_unavailable")
                with self.assertRaises(staging.StageError):
                    staging.stage("/some/private.json", "0" * 64)

    def test_old_selection_format_migrates_only_on_explicit_creator_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir(mode=0o700)
            source = _private_recipe(root / "source.json")
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                recipes.import_recipe(source)
                selection_file = config / "ricebowl" / "recipes" / ".active-recipe"
                selection_file.write_text(json.dumps({
                    "schema_version": 1, "active": "author-made", "previous": "classic",
                }))
                selection_file.chmod(0o600)
                self.assertEqual(recipes.selected_recipe(), "author-made")
                self.assertEqual(json.loads(selection_file.read_text())["schema_version"], 1)
                digest = review.review("author-made")["summary"]["semantic_sha256"]
                self.assertFalse(staging.stage("author-made", digest)["changed"])
                state = json.loads(selection_file.read_text())
                self.assertEqual(state["schema_version"], 2)
                self.assertEqual(state["previous"], "classic")
                self.assertEqual(state["active_sha256"], digest)
                self.assertEqual(staging.rollback()["next_session"], "classic")

    def test_invalid_pinned_state_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.mkdir(mode=0o700)
            store = config / "ricebowl" / "recipes"
            store.mkdir(parents=True, mode=0o700)
            state = store / ".active-recipe"
            for digest in (True, "not-a-checksum", "A" * 64):
                with self.subTest(digest=digest):
                    state.write_text(json.dumps({
                        "schema_version": 2, "active": "classic", "previous": "chrome",
                        "active_sha256": digest, "previous_sha256": None,
                    }))
                    state.chmod(0o600)
                    with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                        with self.assertRaises(recipes.RecipeError):
                            recipes.selected_recipe()
                        with self.assertRaises(staging.StageError) as error:
                            staging.status()
                        self.assertEqual(error.exception.code, "invalid_selection_state")

    def test_cli_contract_and_stable_path_free_errors(self):
        contract = creator_contract.describe_staging()
        self.assertEqual(catalog.describe()["authoring"]["staging"], contract)
        self.assertTrue(contract["reviewed_hash_saved_in_selection"])
        self.assertFalse(contract["recipe_file_immutable"])
        commands = {part["command"] for part in creator_contract.describe_creator_api()["commands"]}
        self.assertTrue({"creator-stage", "creator-status", "creator-rollback"} <= commands)
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(config)}):
                with mock.patch("builtins.print") as printed:
                    self.assertEqual(cli(["de", "creator-status", "--json"]), 0)
                self.assertEqual(json.loads(printed.call_args.args[0])["next_session"], "classic")
                digest = review.review("chrome")["summary"]["semantic_sha256"]
                with mock.patch("builtins.print") as printed:
                    self.assertEqual(cli(["de", "creator-stage", "--recipe", "chrome",
                                          "--expect-sha256", digest, "--json"]), 0)
                self.assertEqual(json.loads(printed.call_args.args[0])["next_session"], "chrome")
                with mock.patch("builtins.print") as printed:
                    self.assertEqual(cli(["de", "creator-rollback", "--expect-active", "chrome",
                                          "--json"]), 0)
                self.assertEqual(json.loads(printed.call_args.args[0])["next_session"], "classic")
                with mock.patch("builtins.print") as printed:
                    self.assertEqual(cli(["de", "creator-stage", "--recipe", "chrome",
                                          "--expect-sha256", "0" * 64,
                                          "--json"]), 2)
                rejected = json.loads(printed.call_args.args[0])
                self.assertEqual(rejected["error"]["code"], "recipe_changed")
                self.assertNotIn(directory, json.dumps(rejected))
                self.assertEqual(recipes.current_selection()[0], "classic")
                for command in (["de", "catalog", "--expect-active", "classic"],
                                ["de", "creator-status", "--expect-sha256", digest],
                                ["de", "creator-rollback", "--recipe", "classic"],
                                ["de", "creator-stage", "--recipe", "chrome"],
                                ["de", "creator-stage", "--nested", "--recipe", "chrome",
                                 "--expect-sha256", digest]):
                    with self.subTest(command=command), mock.patch("sys.stderr"):
                        self.assertEqual(cli(command), 1)


if __name__ == "__main__":
    unittest.main()
