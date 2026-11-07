"""Quick-action recipe is data-only and its command vocabulary is constrained."""

import json
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from macrice.de import recipes


RECIPE = Path(__file__).parents[1] / "examples/wayland/quick-controls.json"


class NativeQuickActionsTests(unittest.TestCase):
    def test_bundled_quick_actions_load_through_recipe_validator(self):
        parsed = recipes.parse(RECIPE.read_bytes())
        self.assertEqual(parsed.schema_version, 4)
        self.assertEqual(parsed.menu[1][1].actions,
                         ("wifi-toggle", "audio-mute", "audio-up", "audio-down"))
        root = ET.fromstring(recipes.labwc_menu(parsed)).find("menu")
        self.assertEqual([group.attrib["label"] for group in root.findall("menu")],
                         ["Applications", "Session"])

    def test_untrusted_custom_commands_are_never_a_valid_action(self):
        value = json.loads(RECIPE.read_text())
        value["menu"]["groups"][1]["actions"][0] = "sh -c nmcli networking off"
        with self.assertRaises(recipes.RecipeError):
            recipes.parse(json.dumps(value).encode())


if __name__ == "__main__":
    unittest.main()
