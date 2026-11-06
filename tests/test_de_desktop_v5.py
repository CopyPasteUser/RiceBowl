"""Schema-v5 desktop icons: authoring, review and untrusted-input boundaries."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from macrice.de import catalog, drafts, recipes, review


FIXTURE = Path(__file__).parent / "fixtures/riceplate-desktop-v5.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class DesktopV5Tests(unittest.TestCase):
    def test_roundtrip_and_catalog_describe_real_native_icons(self):
        parsed = recipes.parse(FIXTURE.read_bytes())
        self.assertEqual(parsed.schema_version, 5)
        self.assertEqual(len(parsed.desktop_icons), 3)
        self.assertEqual([icon.action for icon in parsed.desktop_icons],
                         ["applications", "terminal", "lock"])
        self.assertEqual(review._manifest(parsed), sample())
        legacy = recipes.parse((FIXTURE.parent / "riceplate-shell-v4.json").read_bytes())
        self.assertEqual(json.loads(recipes.waybar_config(parsed)[0])["modules-left"],
                         json.loads(recipes.waybar_config(legacy)[0])["modules-left"])
        self.assertEqual(catalog.describe()["recipe"]["shell_extensions"]["desktop"]["icons"]["native"],
                         "interactive-layer-surfaces")
        self.assertEqual(catalog.describe()["recipe"]["shell_extensions"]["desktop"]["icons"]["native_placement"],
                         "single-output-logical-bounds-reflow")

    def test_template_edit_review_preserves_source_and_private_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.json"
            patch = Path(folder) / "edit.json"
            output = Path(folder) / "output.json"
            created = recipes.create_from_template(
                source="classic", destination=source, recipe_id="generated-desktop",
                name="Generated desktop", schema_version=5)
            self.assertEqual(len(created.desktop_icons), 2)
            before = source.read_bytes()
            patch.write_text(json.dumps({"edit_version": 1, "operations": [
                {"op": "set", "path": "/desktop/icons", "value": [
                    {"label": "Terminal", "action": "terminal", "x": 144, "y": 112},
                    {"label": "Applications", "action": "applications", "x": 32, "y": 112},
                ]},
            ]}), encoding="utf-8")
            result = drafts.create_edit(recipe_token=str(source), edit_source=patch,
                                        destination=output)
            self.assertTrue(result["created"])
            self.assertFalse(result["applied"])
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            changes = review.review(str(output), str(source))["comparison"]["changes"]
            self.assertEqual([change["path"] for change in changes], ["/desktop/icons"])

    def test_out_of_output_bounds_recipe_is_valid_for_runtime_reflow(self):
        # The schema bounds author intent (<=4096), not a specific display.
        # Real compositor geometry determines placement at runtime.
        fixture = FIXTURE.parent / "riceplate-desktop-v5-overflow.json"
        parsed = recipes.parse(fixture.read_bytes())
        self.assertEqual(parsed.desktop_icons[0].x, 4090)
        self.assertEqual(parsed.desktop_icons[0].y, 700)
        self.assertEqual(len(parsed.desktop_icons), 3)

    def test_invalid_icon_lists_are_rejected_with_no_implicit_commands(self):
        good = sample()
        scenarios = [
            None, [], [{}], [good["desktop"]["icons"][0]] * 9,
            [{"label": "Escape", "action": "sh -c whoami", "x": 12, "y": 90}],
            [{"label": "Evil/Command", "action": "terminal", "x": 12, "y": 90}],
            [{"label": "ABCDEFGHIJKLM", "action": "terminal", "x": 12, "y": 90}],
            [{"label": "OK", "action": "terminal", "x": True, "y": 90}],
            [{"label": "OK", "action": "terminal", "x": 4097, "y": 90}],
            [{"label": "OK", "action": "terminal", "x": 12, "y": 71}],
            [{"label": "OK", "action": "terminal", "x": 12, "y": 4097}],
            [{"label": "OK", "action": "terminal", "x": 12, "y": 90, "exec": "bad"}],
            [{"label": "First", "action": "terminal", "x": 32, "y": 96},
             {"label": "Second", "action": "lock", "x": 135, "y": 183}],
        ]
        for icons in scenarios:
            with self.subTest(icons=icons):
                invalid = copy.deepcopy(good)
                invalid["desktop"]["icons"] = icons
                with self.assertRaises(recipes.RecipeError):
                    recipes.parse(json.dumps(invalid).encode())
        invalid = copy.deepcopy(good)
        invalid["desktop"].pop("icons")
        with self.assertRaises(recipes.RecipeError):
            recipes.parse(json.dumps(invalid).encode())
        old = json.loads((FIXTURE.parent / "riceplate-shell-v4.json").read_text())
        old["desktop"]["icons"] = good["desktop"]["icons"]
        with self.assertRaises(recipes.RecipeError):
            recipes.parse(json.dumps(old).encode())


if __name__ == "__main__":
    unittest.main()
