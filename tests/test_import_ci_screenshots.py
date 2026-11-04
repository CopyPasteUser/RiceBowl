"""Screenshot provenance importer must refuse partial or unknown captures."""

import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from scripts.import_ci_screenshots import PROFILES, VERSIONS, import_gallery


class GalleryImportTests(unittest.TestCase):
    def test_every_current_rice_has_three_native_views(self):
        for profile in PROFILES:
            for view in ("start", "controls", "workspace"):
                self.assertEqual(VERSIONS[f"{profile}-{view}"],
                                 f"ricebowl-{profile}-{view}-0.9.1.png")
        self.assertIn("chromeos-notifications", VERSIONS)
        self.assertIn("chromeos-settings", VERSIONS)
        self.assertIn("macmenu-dark", VERSIONS)
        self.assertEqual(len(VERSIONS), len(set(VERSIONS.values())))

    def test_requires_verifiable_source_identifier(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "40-digit commit SHA"):
                import_gallery(Path(folder) / "missing.zip", Path(folder) / "gallery",
                               run_id=1, source_commit="main")
            self.assertFalse((Path(folder) / "gallery").exists())

    def test_missing_image_fails_before_replacing_user_gallery(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            archive = folder / "incomplete.zip"
            with ZipFile(archive, "w"):
                pass
            dest = folder / "gallery"
            dest.mkdir()
            existing = dest / "chromeos-start.webp"
            existing.write_bytes(b"user-image-must-remain")
            with self.assertRaisesRegex(ValueError, "Missing required screenshot"):
                import_gallery(archive, dest, run_id=123,
                               source_commit="a" * 40)
            self.assertEqual(existing.read_bytes(), b"user-image-must-remain")
            self.assertFalse((dest / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
