"""Contract tests for offline RiceBowl Creator component discovery."""

import json
import unittest
from unittest import mock

from macrice.de import catalog, recipes
from macrice.de import creator_contract


class ComponentCatalogTests(unittest.TestCase):
    def test_catalog_is_complete_truthful_and_declarative(self):
        info = catalog.describe()
        catalog.validate_catalog_contract()
        self.assertEqual(info["catalog_version"], 4)
        self.assertEqual(info["scope"], "wayland-shell-preview")
        self.assertFalse(info["complete_desktop_environment"])
        self.assertEqual(info["recipe"]["schema_versions"], [1, 2, 3, 4, 5])
        self.assertFalse(info["recipe"]["custom_commands"])
        self.assertFalse(info["recipe"]["custom_actions"])
        self.assertFalse(info["recipe"]["external_assets"])
        self.assertEqual(info["recipe"]["maximum_bytes"], recipes.MAX_RECIPE_BYTES)
        self.assertEqual(info["authoring"]["draft_edit"], creator_contract.describe())
        self.assertEqual(info["authoring"]["draft_edit"]["operation"], "set")
        self.assertFalse(info["authoring"]["draft_edit"]["mutates_active_desktop"])
        self.assertEqual(info["recipe"]["sections"], ["start", "center", "end"])
        self.assertEqual(info["recipe"]["panel_positions"], ["top", "bottom"])
        self.assertEqual({part["id"] for part in info["components"]}, recipes.WIDGETS)
        implemented = {part["id"] for part in info["components"]
                       if part["native"] != "unavailable"}
        self.assertEqual(implemented, {"launcher", "tasks", "clock"})
        self.assertTrue(all(not part["keyboard_navigation"] for part in info["components"]))
        self.assertEqual({name: field["default"] for name, field in
                          info["recipe"]["metrics"]["fields"].items()},
                         dict(zip(recipes.METRIC_FIELDS, recipes.METRIC_DEFAULTS)))

    def test_agent_json_catalog_is_deterministic_read_only_and_flag_scoped(self):
        from macrice.cli import main

        with mock.patch("builtins.print") as printer:
            self.assertEqual(main(["de", "catalog", "--json"]), 0)
            first = printer.call_args.args[0]
        self.assertEqual(json.loads(first), catalog.describe())
        with mock.patch("builtins.print") as printer:
            self.assertEqual(main(["de", "catalog", "--json"]), 0)
            self.assertEqual(printer.call_args.args[0], first)
        with mock.patch("builtins.print") as printer:
            self.assertEqual(main(["de", "catalog"]), 0)
            rows = "\n".join(args.args[0] for args in printer.call_args_list)
            self.assertIn("launcher", rows)
            self.assertIn("not available", rows)
        for flags in (("--recipe", "classic"), ("--nested",),
                      ("--panel", "native"), ("--output", "/tmp/unused.json"),
                      ("--schema-version", "2")):
            with self.subTest(flags=flags), mock.patch("sys.stderr"):
                self.assertEqual(main(["de", "catalog", *flags]), 1)

    def test_catalog_serializes_to_json_without_private_environment_data(self):
        payload = json.dumps(catalog.describe(), sort_keys=True, ensure_ascii=False)
        self.assertLess(len(payload), 16_384)
        self.assertNotIn("/home/", payload)
        self.assertNotIn("https://", payload)
        self.assertNotIn("exec:", payload)


if __name__ == "__main__":
    unittest.main()
