"""XP Help topics and shared factual System Properties data."""

import unittest

from macrice.classic98_system import collect_system, report_sections
from macrice.luna_help import TOPICS, search_topics


class LunaHelpTests(unittest.TestCase):
    def test_search_is_case_insensitive_and_uses_actual_bundled_text(self):
        self.assertEqual(search_topics(""), ())
        self.assertIn("Taskbar and Quick Launch", search_topics("quick launch"))
        self.assertIn("Connecting to networks", search_topics("BLUETOOTH"))
        self.assertEqual(search_topics("nonexistent topic 73891"), ())

    def test_topics_do_not_claim_windows_software_or_riceexplorer_completion(self):
        self.assertIn("Linux", TOPICS["Getting started"])
        self.assertIn("being developed separately", TOPICS["Files and the desktop"])

    def test_system_report_uses_xp_label_without_changing_win98_default(self):
        snapshot = collect_system()
        xp = report_sections(snapshot, rice_name="Windows XP Luna")
        classic = report_sections(snapshot)
        self.assertIn("Windows XP Luna-inspired", xp["General"])
        self.assertIn("Windows 98-inspired", classic["General"])


if __name__ == "__main__":
    unittest.main()
