"""Real local-file copy and safe undo without touching the user's Desktop."""

import os
import tempfile
import unittest
from pathlib import Path
from threading import Event

from macrice.riceware import file_drop


class FileDropTests(unittest.TestCase):
    def test_explicit_non_overwriting_copy_and_undo(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "a.txt"
            target = Path(root) / "Desktop"
            target.mkdir()
            source.write_text("hello world", encoding="utf-8")
            plan = file_drop.plan_copy([source.as_uri()], target)
            self.assertEqual(plan.total_bytes, 11)
            receipt = file_drop.copy_files(plan)
            self.assertEqual((target / "a.txt").read_text(), "hello world")
            self.assertEqual((target / "a.txt").stat().st_mode & 0o777, 0o600)
            self.assertEqual(file_drop.undo_copy(receipt), (1, 0))
            self.assertFalse((target / "a.txt").exists())
            self.assertTrue(source.exists())

    def test_refuse_overwrite_symlinks_directories_and_remote_uris(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("safe", encoding="utf-8")
            target = Path(root) / "destination"
            target.mkdir()
            for unsafe in ("smb://server/a", "file://remote/test", "https://site/a",
                           "file:///tmp/a?overwrite=true", "file:///tmp/%00"):
                with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                    file_drop.parse_local_uris([unsafe])
            with self.assertRaises(ValueError):
                file_drop.plan_copy([target.as_uri()], target)
            link = Path(root) / "alias.txt"
            link.symlink_to(source)
            with self.assertRaises(ValueError):
                file_drop.plan_copy([link.as_uri()], target)
            (target / source.name).write_text("original", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                file_drop.plan_copy([source.as_uri()], target)
            self.assertEqual((target / source.name).read_text(), "original")

    def test_cancellation_never_deletes_existing_destination(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_bytes(b"test")
            target = Path(root) / "destination"
            target.mkdir()
            plan = file_drop.plan_copy([source.as_uri()], target)
            cancel = Event()
            cancel.set()
            with self.assertRaisesRegex(RuntimeError, "cancelled"):
                file_drop.copy_files(plan, cancel=cancel)
            self.assertFalse((target / source.name).exists())

    def test_partially_completed_batch_undoes_all_unchanged_new_files(self):
        with tempfile.TemporaryDirectory() as root:
            source_a = Path(root) / "a.txt"
            source_b = Path(root) / "b.txt"
            source_a.write_text("a", encoding="utf-8")
            source_b.write_text("b", encoding="utf-8")
            target = Path(root) / "destination"
            target.mkdir()
            plan = file_drop.plan_copy([source_a.as_uri(), source_b.as_uri()], target)
            # A collision appearing after acceptance is caught at O_EXCL;
            # earlier outputs are rolled back while the new file is preserved.
            (target / "b.txt").write_text("someone else's edit", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                file_drop.copy_files(plan)
            self.assertFalse((target / "a.txt").exists())
            self.assertEqual((target / "b.txt").read_text(), "someone else's edit")

    def test_undo_skips_modified_and_replaced_files(self):
        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "source.txt"
            source.write_text("safe", encoding="utf-8")
            target = Path(root) / "destination"
            target.mkdir()
            receipt = file_drop.copy_files(file_drop.plan_copy([source.as_uri()], target))
            copied = target / source.name
            copied.write_text("user changed this", encoding="utf-8")
            self.assertEqual(file_drop.undo_copy(receipt), (0, 1))
            self.assertEqual(copied.read_text(), "user changed this")

    def test_rejects_unbounded_or_empty_uri_lists(self):
        for values in ([], ["file:///tmp/a"] * 33, "file:///tmp/a"):
            with self.assertRaises(ValueError):
                file_drop.parse_local_uris(values)


if __name__ == "__main__":
    unittest.main()
