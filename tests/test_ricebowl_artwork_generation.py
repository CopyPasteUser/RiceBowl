"""Prevent regression from distinctive icons back into identical generic placeholders."""
import tempfile
import unittest
from pathlib import Path

from macrice.installer import project_root
from scripts.ricebowl_artwork import CURATED_ICONS, write_generated_icon


class RiceBowlArtworkGenerationTests(unittest.TestCase):
    def test_curated_icons_survive_asset_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            for relative in CURATED_ICONS:
                asset = Path(tmp) / relative
                asset.parent.mkdir(parents=True, exist_ok=True)
                asset.write_text("<svg>user-reviewed artwork</svg>\n", encoding="utf-8")
                self.assertFalse(write_generated_icon(asset, relative, "<svg>generic placeholder</svg>"))
                self.assertEqual(asset.read_text(), "<svg>user-reviewed artwork</svg>\n")

    def test_missing_curated_icon_fails_instead_of_faking_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            for relative in CURATED_ICONS:
                target = Path(tmp) / relative
                with self.assertRaisesRegex(FileNotFoundError, "hand-curated"):
                    write_generated_icon(target, relative, "<svg/>")
                self.assertFalse(target.exists())

    def test_non_curated_art_is_reproducibly_generated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "apps/accessories-calculator.svg"
            self.assertTrue(write_generated_icon(path, "apps/accessories-calculator.svg", "<svg/>"))
            self.assertTrue(write_generated_icon(path, "apps/accessories-calculator.svg", "<svg>new</svg>"))
            self.assertEqual(path.read_text(), "<svg>new</svg>")

    def test_build_scripts_use_preserving_helper(self):
        scripts = project_root() / "scripts"
        for name in ("build_aero_assets.py", "build_ten_assets.py", "build_heritage_assets.py"):
            with self.subTest(script=name):
                content = (scripts / name).read_text(encoding="utf-8")
                self.assertIn("from ricebowl_artwork import write_generated_icon", content)
                self.assertIn("write_generated_icon(", content)

    def test_heritage_start_art_matches_icon_theme(self):
        root = project_root() / "assets"
        designs = {
            "Luna-Icons": "ricebowl-xp-start.svg",
            "Classic-Icons": "ricebowl-classic-start.svg",
            "Chrome-Icons": "ricebowl-chrome-start.svg",
            "Frutiger-Icons": "ricebowl-frutiger-start.svg",
        }
        observed = []
        for theme, artwork in designs.items():
            original = (root / artwork).read_bytes()
            observed.append(original)
            for alias in ("start-here", "xfce4-menu", "ricehub-start", "ricebowl-start"):
                with self.subTest(theme=theme, alias=alias):
                    target = root / "icons" / ("RiceHub-" + theme) / "scalable/apps" / (alias + ".svg")
                    self.assertEqual(target.read_bytes(), original)
        self.assertEqual(len(observed), len(set(observed)))


if __name__ == "__main__":
    unittest.main()
