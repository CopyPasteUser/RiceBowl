"""Offline Windows 98 Help search and navigation regressions."""
from __future__ import annotations

import unittest

from macrice.classic98_help import INDEX, TOPICS, search_topics


class ClassicHelpTests(unittest.TestCase):
    def test_bundled_topics_are_substantial_and_local(self):
        self.assertGreaterEqual(len(TOPICS), 10)
        self.assertIn("Finding Files", TOPICS)
        self.assertIn("Privacy and Recovery", TOPICS)
        self.assertTrue(all(len(text) >= 80 for text in TOPICS.values()))

    def test_index_references_only_real_topics(self):
        self.assertTrue(INDEX)
        self.assertEqual(set(INDEX.values()) - set(TOPICS), set())

    def test_search_matches_body_and_casefolded_title(self):
        self.assertIn("Finding Files", search_topics("SEARCH a selected folder"))
        self.assertIn("Taskbar", search_topics("TaSkBaR"))

    def test_search_index_alias_and_order(self):
        self.assertIn("Privacy and Recovery", search_topics("backup"))
        self.assertEqual(search_topics("  "), ())
        matches = search_topics("linux")
        self.assertEqual(matches, tuple(topic for topic in TOPICS if topic in matches))


if __name__ == "__main__":
    unittest.main()
