"""Exercise safe fast-forward, pinned previews and rollback in local Git repos."""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice import updater
from macrice.cli import parser
from macrice.installer import InstallationError, MANAGED_MARKER


def git(path, *args):
    result = subprocess.run(["git", "-C", str(path), *args],
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origin = self.root / "author"
        self.origin.mkdir()
        git(self.origin, "init", "-b", "main")
        git(self.origin, "config", "user.name", "Test")
        git(self.origin, "config", "user.email", "test@example.invalid")
        (self.origin / "revision.txt").write_text("v1")
        git(self.origin, "add", "revision.txt")
        git(self.origin, "commit", "-m", "initial")
        self.bare = self.root / "remote.git"
        subprocess.run(["git", "clone", "--bare", str(self.origin), str(self.bare)],
                       capture_output=True, check=True)
        git(self.origin, "remote", "add", "origin", str(self.bare))
        self.checkout = self.root / "RiceBowl"
        subprocess.run(["git", "clone", str(self.bare), str(self.checkout)],
                       capture_output=True, check=True)
        self.old = git(self.checkout, "rev-parse", "HEAD")
        self.data = self.root / "data"
        self.installed = self.data / "macrice"
        self.installed.mkdir(parents=True)
        (self.installed / MANAGED_MARKER).write_text("managed")
        (self.installed / "launcher.py").write_text("v1")
        self.patches = (
            mock.patch.object(updater, "ALLOWED_REMOTES", {str(self.bare)}),
            mock.patch.object(updater, "data_home", return_value=self.data),
            mock.patch.object(updater.os, "geteuid", return_value=1000),
        )
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def new_revision(self):
        (self.origin / "revision.txt").write_text("v2")
        git(self.origin, "add", "revision.txt")
        git(self.origin, "commit", "-m", "new")
        git(self.origin, "push", "origin", "main")
        return git(self.origin, "rev-parse", "HEAD")

    def fake_installer(self, *, fail_new=False):
        def install(options, source, output):
            self.assertTrue(options.no_start)
            archive = self.data / "macrice-versions"
            archive.mkdir(exist_ok=True)
            old = archive / ("previous" if not (archive / "previous").exists() else "failed")
            self.installed.rename(old)
            self.installed.mkdir()
            (self.installed / MANAGED_MARKER).write_text("managed")
            value = (source / "revision.txt").read_text() if (source / "revision.txt").exists() else (
                source / "launcher.py").read_text()
            (self.installed / "launcher.py").write_text(value)
            if fail_new and value == "v2":
                raise InstallationError("simulated installation failure")
        return install

    def test_cached_check_is_read_only_and_refresh_is_explicit(self):
        self.new_revision()
        self.assertEqual(updater.inspect(source=self.checkout).commits, 0)
        self.assertEqual(updater.inspect(source=self.checkout, refresh=True).commits, 1)
        self.assertEqual(git(self.checkout, "rev-parse", "HEAD"), self.old)

    def test_stale_preview_rejected_before_install(self):
        new = self.new_revision()
        with mock.patch.object(updater, "install") as install:
            with self.assertRaisesRegex(updater.UpdateError, "changed since preview"):
                updater.apply(source=self.checkout, expected_revision=self.old)
            install.assert_not_called()
        self.assertNotEqual(new, self.old)

    def test_success_installs_pinned_archive_then_fast_forwards_checkout(self):
        new = self.new_revision()
        with mock.patch.object(updater, "install", side_effect=self.fake_installer()):
            plan = updater.apply(source=self.checkout, expected_revision=new)
        self.assertEqual(plan.commits, 1)
        self.assertEqual(git(self.checkout, "rev-parse", "HEAD"), new)
        self.assertEqual((self.installed / "launcher.py").read_text(), "v2")
        self.assertEqual((self.data / "macrice-versions/previous/launcher.py").read_text(), "v1")

    def test_failed_install_reinstalls_prior_bundle_and_preserves_checkout(self):
        self.new_revision()
        with mock.patch.object(updater, "install", side_effect=self.fake_installer(fail_new=True)):
            with self.assertRaisesRegex(updater.UpdateError, "previous installed bundle reinstalled"):
                updater.apply(source=self.checkout)
        self.assertEqual(git(self.checkout, "rev-parse", "HEAD"), self.old)
        self.assertEqual((self.installed / "launcher.py").read_text(), "v1")

    def test_dirty_checkout_and_wrong_origin_are_rejected(self):
        (self.checkout / "untracked.txt").write_text("personal")
        with self.assertRaisesRegex(updater.UpdateError, "untracked.txt"):
            updater.inspect(source=self.checkout)
        (self.checkout / "untracked.txt").unlink()
        with mock.patch.object(updater, "ALLOWED_REMOTES", {"https://example.invalid/other.git"}):
            with self.assertRaisesRegex(updater.UpdateError, "official RiceBowl"):
                updater.inspect(source=self.checkout)

    def test_explicit_preservation_in_local_stash_keeps_tracked_and_untracked(self):
        (self.checkout / "revision.txt").write_text("user-edited")
        (self.checkout / "private-note.txt").write_text("user-data")
        stash_sha = updater.preserve_changes(source=self.checkout)
        self.assertEqual(git(self.checkout, "rev-parse", "refs/stash"), stash_sha)
        self.assertEqual((self.checkout / "revision.txt").read_text(), "v1")
        self.assertFalse((self.checkout / "private-note.txt").exists())
        self.assertFalse(updater.local_changes(self.checkout))
        # The saved files can be safely recovered at an explicit later time.
        git(self.checkout, "stash", "apply", stash_sha)
        self.assertEqual((self.checkout / "revision.txt").read_text(), "user-edited")
        self.assertEqual((self.checkout / "private-note.txt").read_text(), "user-data")

    def test_cli_accepts_explicit_pinned_revision_and_requires_user_confirmation(self):
        args = parser().parse_args(["update", "apply", "--yes", "--revision", "a" * 40])
        self.assertTrue(args.yes)
        self.assertEqual(args.revision, "a" * 40)
        self.assertEqual(parser().parse_args(["update", "check", "--refresh"]).action,
                         "check")

    def test_linked_archive_location_does_not_receive_previous_installation(self):
        self.new_revision()
        owned_elsewhere = self.root / "private"
        owned_elsewhere.mkdir()
        (self.data / "macrice-versions").symlink_to(owned_elsewhere, target_is_directory=True)
        with mock.patch.object(updater, "install") as install:
            with self.assertRaisesRegex(updater.UpdateError, "archive location is unsafe"):
                updater.apply(source=self.checkout)
            install.assert_not_called()
        self.assertFalse(list(owned_elsewhere.iterdir()))


if __name__ == "__main__":
    unittest.main()
