"""ChromeOS Settings navigation has real, searchable Linux destinations."""

from __future__ import annotations

from types import SimpleNamespace
import unittest

from macrice.chrome_settings import ACTIONS, SECTIONS, available_tool, search_actions, status_text


class ChromeSettingsTests(unittest.TestCase):
    def test_every_category_has_a_unique_navigable_action(self):
        sections = [item[0] for item in SECTIONS]
        self.assertEqual(len(sections), len(set(sections)))
        self.assertTrue(all(action.section in sections for action in ACTIONS))
        self.assertEqual(len({(action.section, action.name) for action in ACTIONS}), len(ACTIONS))
        self.assertTrue(all(action.tools for action in ACTIONS))

    def test_search_matches_section_description_and_unicode(self):
        self.assertIn("Connections", [action.name for action in search_actions("wi-fi")])
        self.assertIn("Power", [action.name for action in search_actions("DEVICE battery")])
        self.assertEqual(search_actions("no-invented-google-feature"), ())
        self.assertEqual(search_actions(" "), ACTIONS)

    def test_missing_backend_is_not_exposed_as_an_enabled_action(self):
        action = next(action for action in ACTIONS if action.name == "Sound")
        self.assertIsNone(available_tool(action, which=lambda _: None))
        self.assertEqual(available_tool(action, which=lambda name: name == "xfce4-mixer"),
                         "xfce4-mixer")

    def test_read_only_status_tracks_actual_reported_state(self):
        state = SimpleNamespace(network="wifi", battery=SimpleNamespace(percent=68,
                                   label="Charging"), sound=SimpleNamespace(percent=30,
                                   muted=False))
        actions = {action.name: action for action in ACTIONS}
        self.assertIn("Wi-Fi", status_text(actions["Connections"], state))
        self.assertIn("30%", status_text(actions["Sound"], state))
        self.assertIn("68%", status_text(actions["Power"], state))
        self.assertEqual(status_text(actions["Power"], None),
                         "Status temporarily unavailable")
        state.network = "offline"
        state.battery = None
        state.sound.muted = True
        self.assertIn("No active", status_text(actions["Connections"], state))
        self.assertIn("muted", status_text(actions["Sound"], state))
        self.assertIn("No battery", status_text(actions["Power"], state))


if __name__ == "__main__":
    unittest.main()
