"""No real desktop is modified while testing opt-in XP shortcuts."""

import tempfile
import unittest
from pathlib import Path

from macrice.luna_desktop import _desktop_entry, desktop_path, manage


class XpDesktopTests(unittest.TestCase):
    def test_xdg_custom_desktop_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            config = home / ".config"
            config.mkdir()
            (config / "user-dirs.dirs").write_text(
                'XDG_DESKTOP_DIR="$HOME/Schreibtisch"\n', encoding="utf-8")
            self.assertEqual(desktop_path(home, config), home / "Schreibtisch")
            (config / "user-dirs.dirs").write_text(
                'XDG_DESKTOP_DIR="/etc"\n', encoding="utf-8")
            self.assertEqual(desktop_path(home, config), home / "Desktop")

    def test_install_remove_are_opt_in_and_preserve_modified_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            catalog = {"ricebowl-xp-computer.desktop": _desktop_entry(
                "My Computer", "computer", "computer:///")}
            name = "ricebowl-xp-computer.desktop"
            self.assertEqual(manage("status", folder=folder, catalog=catalog), ((), ()))
            self.assertEqual(manage("install", folder=folder, catalog=catalog)[0], (name,))
            self.assertTrue((folder / name).stat().st_mode & 0o100)
            self.assertIn("installed", str(manage("status", folder=folder, catalog=catalog)))
            (folder / name).write_text("user edited", encoding="utf-8")
            self.assertEqual(manage("remove", folder=folder, catalog=catalog)[0], ())
            self.assertEqual((folder / name).read_text(encoding="utf-8"), "user edited")
            self.assertEqual(manage("install", folder=folder, catalog=catalog)[0], ())

    def test_removal_cleans_untouched_entry_not_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            untouched = folder / "notes.txt"
            untouched.write_text("keep", encoding="utf-8")
            catalog = {"ricebowl-xp-trash.desktop": _desktop_entry(
                "Recycle Bin", "user-trash", "trash:///")}
            manage("install", folder=folder, catalog=catalog)
            self.assertEqual(manage("remove", folder=folder, catalog=catalog)[0],
                             ("ricebowl-xp-trash.desktop",))
            self.assertEqual(untouched.read_text(encoding="utf-8"), "keep")

    def test_existing_symlink_is_never_followed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            victim = folder / "victim"
            victim.write_text("safe", encoding="utf-8")
            (folder / "ricebowl-xp-trash.desktop").symlink_to(victim)
            catalog = {"ricebowl-xp-trash.desktop": _desktop_entry(
                "Recycle Bin", "user-trash", "trash:///")}
            self.assertEqual(manage("install", folder=folder, catalog=catalog)[0], ())
            self.assertEqual(victim.read_text(encoding="utf-8"), "safe")

    def test_uri_percent_is_safe_for_desktop_file(self):
        text = _desktop_entry("My Documents", "folder", "file:///home/a/My%20Docs")
        self.assertIn('"file:///home/a/My%%20Docs"', text)


if __name__ == "__main__":
    unittest.main()
