"""Exercise the published OS-inspired and original Creator recipes as data."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from macrice.de import recipes, review


EXAMPLES = Path(__file__).resolve().parents[1] / "examples/wayland"


class CreatorExamplesTests(unittest.TestCase):
    def test_both_examples_use_the_exact_native_recipe_contract(self):
        fingerprints = set()
        for name in ("heritage-workstation", "orbit-atelier"):
            with self.subTest(name=name):
                path = EXAMPLES / f"{name}.json"
                data = json.loads(path.read_text(encoding="utf-8"))
                recipe = recipes.parse(path.read_bytes())
                self.assertEqual(recipe.recipe_id, name)
                self.assertEqual(recipe.schema_version, 5)
                self.assertEqual(set(data), {
                    "schema_version", "id", "name", "panel", "colors",
                    "menu", "desktop", "tokens", "responsive"})
                self.assertTrue(recipe.desktop_icons)
                self.assertTrue(recipe.layout)
                self.assertTrue(recipe.compact)
                self.assertEqual(
                    {icon.action for icon in recipe.desktop_icons},
                    {"applications", "terminal", "lock"},
                )
                self.assertEqual(
                    {action for group in recipe.menu[1] for action in group.actions},
                    {"applications", "terminal", "lock", "logout"},
                )
                fingerprints.add(review._semantic_hash(review._manifest(recipe)))
        self.assertEqual(len(fingerprints), 2)

    def test_examples_demonstrate_distinct_shell_compositions(self):
        classic = recipes.parse((EXAMPLES / "heritage-workstation.json").read_bytes())
        original = recipes.parse((EXAMPLES / "orbit-atelier.json").read_bytes())
        self.assertEqual(classic.position, "bottom")
        self.assertEqual(original.position, "top")
        self.assertNotEqual(classic.wallpaper, original.wallpaper)
        self.assertNotEqual(classic.layout, original.layout)
        self.assertNotEqual(classic.colors, original.colors)
        self.assertNotEqual(classic.compact, original.compact)


if __name__ == "__main__":
    unittest.main()
