"""Windows 7 desktop shortcuts are explicit and never alter user-owned files."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from macrice.luna_desktop import manage as manage_xp
from macrice.win7_desktop import _entry, entries, manage


class Win7DesktopTests(unittest.TestCase):
    def test_four_real_locations_have_distinct_ricebowl_marker(self):
        catalog = entries()
        self.assertEqual(set(catalog), {
            "ricebowl-win7-computer.desktop", "ricebowl-win7-documents.desktop",
            "ricebowl-win7-network.desktop", "ricebowl-win7-trash.desktop",
        })
        for content in catalog.values():
            self.assertIn("X-RiceBowl-Win7-Managed=true", content)
            self.assertNotIn("X-RiceBowl-XP-Managed", content)
            self.assertIn("Exec=gio open", content)
        self.assertIn("computer:///", catalog["ricebowl-win7-computer.desktop"])
        self.assertIn("trash:///", catalog["ricebowl-win7-trash.desktop"])

    def test_safe_install_remove_preserves_everything_not_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            xp = folder / "ricebowl-xp-computer.desktop"
            xp.write_text("XP user desktop file", encoding="utf-8")
            user = folder / "my-file.desktop"
            user.write_text("User file", encoding="utf-8")
            catalog = {"ricebowl-win7-computer.desktop": _entry("Computer", "computer", "computer:///")}
            name = "ricebowl-win7-computer.desktop"
            self.assertEqual(manage("status", folder=folder, catalog=catalog), ((), ()))
            self.assertEqual(manage("install", folder=folder, catalog=catalog)[0], (name,))
            self.assertTrue((folder / name).stat().st_mode & 0o100)
            self.assertEqual(manage("install", folder=folder, catalog=catalog)[0], ())
            self.assertEqual(manage("remove", folder=folder, catalog=catalog)[0], (name,))
            self.assertEqual(xp.read_text(encoding="utf-8"), "XP user desktop file")
            self.assertEqual(user.read_text(encoding="utf-8"), "User file")
            self.assertEqual(manage("install", folder=folder, catalog=catalog)[0], (name,))
            (folder / name).write_text("user-modified", encoding="utf-8")
            self.assertEqual(manage("remove", folder=folder, catalog=catalog)[0], ())
            self.assertEqual((folder / name).read_text(encoding="utf-8"), "user-modified")

    def test_wrong_prefix_and_symlinks_are_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            target = folder / "target"
            target.write_text("safe", encoding="utf-8")
            name = "ricebowl-win7-computer.desktop"
            (folder / name).symlink_to(target)
            catalog = {name: _entry("Computer", "computer", "computer:///")}
            changed, preserved = manage("install", folder=folder, catalog=catalog)
            self.assertEqual(changed, ())
            self.assertTrue(preserved)
            self.assertEqual(target.read_text(encoding="utf-8"), "safe")
            with self.assertRaises(ValueError):
                manage_xp("install", folder=folder, catalog=catalog)
            with self.assertRaises(ValueError):
                manage("install", folder=folder,
                       catalog={"ricebowl-xp-computer.desktop": "not ours"})


if __name__ == "__main__":
    unittest.main()
