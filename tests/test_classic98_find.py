"""Real filesystem regression tests for Windows 98 Find.

Only disposable temporary directories are read; no user file is modified.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

from macrice.classic98_find import (
    FindCriteria, MAX_TEXT_FILE, search_folder, validate_criteria,
)


class Classic98FindTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        (self.root / "alpha.txt").write_text("Hello Überfluss\nSecond line", encoding="utf-8")
        (self.root / "beta.log").write_text("Something else", encoding="utf-8")
        (self.root / ".hidden.txt").write_text("secret", encoding="utf-8")
        (self.root / "nested").mkdir()
        (self.root / "nested" / "gamma.txt").write_text("HELLO world", encoding="utf-8")

    def scan(self, criteria=None, **options):
        events = []
        def deliver(paths, scanned, final, reason):
            events.append((list(paths), scanned, final, reason))
        summary = search_folder(
            self.root, criteria or FindCriteria(name="a"), threading.Event(),
            deliver, **options)
        found = [p.relative_to(self.root).as_posix()
                 for paths, _, _, _ in events for p in paths]
        self.assertEqual(sum(len(batch[0]) for batch in events), summary.matches)
        self.assertTrue(events[-1][2])
        return found, summary

    def test_invalid_and_unbounded_requests_are_rejected(self):
        for criteria in (
            FindCriteria(), FindCriteria(min_bytes=20, max_bytes=10),
            FindCriteria(kind="bad", name="x"),
            FindCriteria(kind="folders", text="test"),
            FindCriteria(extension="../secret"),
            FindCriteria(modified_within_days=2),
            FindCriteria(min_bytes=-1),
        ):
            with self.subTest(criteria=criteria), self.assertRaises(ValueError):
                validate_criteria(criteria)

    def test_filename_casefold_and_nested(self):
        found, status = self.scan(FindCriteria(name="ALPHA"))
        self.assertEqual(found, ["alpha.txt"])
        self.assertEqual(status.reason, "complete")

    def test_extension_type_and_hidden_filter(self):
        found, _ = self.scan(FindCriteria(extension=".txt"))
        self.assertEqual(set(found), {"alpha.txt", "nested/gamma.txt"})
        found, _ = self.scan(FindCriteria(extension="txt", include_hidden=True))
        self.assertEqual(set(found), {"alpha.txt", "nested/gamma.txt", ".hidden.txt"})
        found, _ = self.scan(FindCriteria(kind="folders"))
        self.assertEqual(found, ["nested"])
        found, _ = self.scan(FindCriteria(kind="files"))
        self.assertNotIn("nested", found)

    def test_size_filter_only_regular_files(self):
        found, _ = self.scan(FindCriteria(min_bytes=20))
        self.assertIn("alpha.txt", found)
        self.assertNotIn("beta.log", found)
        self.assertNotIn("nested", found)
        found, _ = self.scan(FindCriteria(max_bytes=20))
        self.assertIn("beta.log", found)

    def test_date_filter(self):
        old = time.time() - 400 * 86400
        os.utime(self.root / "beta.log", (old, old))
        found, _ = self.scan(FindCriteria(kind="files", modified_within_days=7),
                             now=time.time())
        self.assertIn("alpha.txt", found)
        self.assertNotIn("beta.log", found)

    def test_bounded_text_search_unicode_and_binary(self):
        (self.root / "data.bin").write_bytes(b"HELLO\x00hidden")
        (self.root / "huge.txt").write_bytes(b"x" * (MAX_TEXT_FILE + 1))
        found, summary = self.scan(FindCriteria(text="hello"))
        self.assertEqual(set(found), {"alpha.txt", "nested/gamma.txt"})
        self.assertGreaterEqual(summary.content_skipped, 1)
        found, _ = self.scan(FindCriteria(text="überFLUSS"))
        self.assertEqual(found, ["alpha.txt"])

    def test_no_recursion_into_symlinked_directory(self):
        outside = self.root.parent / "unrelated"
        with tempfile.TemporaryDirectory() as external:
            (Path(external) / "out-of-scope.txt").write_text("secret")
            (self.root / "escape").symlink_to(external, target_is_directory=True)
            found, _ = self.scan(FindCriteria(name="out-of-scope"))
            self.assertEqual(found, [])

    def test_cancellation_before_search(self):
        stop = threading.Event()
        stop.set()
        events = []
        summary = search_folder(self.root, FindCriteria(name="a"), stop,
                                lambda *args: events.append(args))
        self.assertEqual(summary.reason, "stopped")
        self.assertEqual(summary.matches, 0)
        self.assertEqual(len(events), 1)

    def test_result_and_scan_limits(self):
        found, summary = self.scan(FindCriteria(kind="files"), max_results=1)
        self.assertEqual(len(found), 1)
        self.assertEqual(summary.reason, "result limit reached")
        found, summary = self.scan(FindCriteria(name="a"), max_visited=1)
        self.assertLessEqual(len(found), 1)
        self.assertEqual(summary.reason, "scan limit reached")


if __name__ == "__main__":
    unittest.main()
