"""Deterministic screenshot comparisons, never invented preview screenshots."""

import json
import tempfile
import unittest
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

from scripts.compare_wayland_captures import compare, main


@unittest.skipIf(Image is None, "Optional Pillow is not installed in this runtime")
class WaylandVisualQaTests(unittest.TestCase):
    def test_native_smoke_embedded_shell_remains_literal(self):
        """Prevent quotes from prematurely closing the `sh -c` payload."""
        source = (Path(__file__).parent.parent /
                  "scripts/smoke_riceplate_native.sh").read_text(encoding="utf-8")
        embedded = source.split("dbus-run-session -- sh -eu -c '", 1)[1].split(
            "' sh \"$source_root\"", 1)[0]
        self.assertNotIn("'", embedded)

    def _private_recipe(self, directory: Path, *, bottom: bool = False) -> Path:
        source = Path(__file__).parent / "fixtures/riceplate-desktop-v5.json"
        data = json.loads(source.read_text(encoding="utf-8"))
        if bottom:
            data["panel"]["position"] = "bottom"
            data["desktop"]["icons"][0].update(x=600, y=700)
        path = directory / "recipe.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        path.chmod(0o600)
        return path

    def test_identical_real_pngs_are_reported_as_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "capture.png"
            Image.new("RGB", (32, 24), "#1357ab").save(path)
            result = compare(path, path)
            self.assertTrue(result["identical"])
            self.assertEqual(result["changed_pixel_ratio"], 0)
            self.assertEqual(result["size"], {"width": 32, "height": 24})
            self.assertEqual(result["perceptual_or_functional_accuracy"], "not_measured")

    def test_changes_are_measured_not_reported_as_fake_accuracy(self):
        with tempfile.TemporaryDirectory() as folder:
            reference = Path(folder) / "reference.png"
            actual = Path(folder) / "actual.png"
            Image.new("RGB", (10, 10), "#000000").save(reference)
            image = Image.new("RGB", (10, 10), "#000000")
            for x in range(5):
                for y in range(10):
                    image.putpixel((x, y), (255, 255, 255))
            image.save(actual)
            result = compare(reference, actual, threshold=24)
            self.assertEqual(result["changed_pixel_ratio"], .5)
            self.assertEqual(result["mean_absolute_rgb_error"], 127.5)
            self.assertFalse(result["identical"])

    def test_dimension_mismatch_and_corrupt_images_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder) / "a.png"
            b = Path(folder) / "b.png"
            Image.new("RGB", (10, 10)).save(a)
            Image.new("RGB", (11, 10)).save(b)
            with self.assertRaisesRegex(ValueError, "dimensions differ"):
                compare(a, b)
            b.write_text("not a screenshot")
            self.assertEqual(main([str(a), str(b)]), 2)
            with self.assertRaisesRegex(ValueError, "Threshold"):
                compare(a, a, threshold=256)

    def test_validated_rice_regions_report_pixel_changes_and_clipped_icons(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            source = self._private_recipe(directory)
            reference, actual = directory / "reference.png", directory / "actual.png"
            Image.new("RGB", (200, 260), "#223344").save(reference)
            image = Image.new("RGB", (200, 260), "#223344")
            image.putpixel((40, 105), (255, 255, 255))
            image.save(actual)
            result = compare(reference, actual, recipe_token=str(source))
            self.assertEqual(result["comparison_version"], 2)
            self.assertEqual(result["recipe"]["id"], "mockup-desktop")
            self.assertEqual(len(result["recipe"]["semantic_sha256"]), 64)
            regions = {item["id"]: item for item in result["regions"]}
            self.assertEqual(regions["panel"]["expected_rect"]["height"], 40)
            self.assertTrue(regions["panel"]["identical"])
            self.assertFalse(regions["desktop-icon-1"]["identical"])
            self.assertGreater(regions["desktop-icon-2"]["visible_fraction"], 0)
            self.assertLess(regions["desktop-icon-2"]["visible_fraction"], 1)
            self.assertEqual(regions["desktop-icon-3"]["visible_fraction"], round(48 / 104, 6))
            self.assertEqual({item["code"] for item in result["layout_issues"]},
                             {"icon_outside_output"})

    def test_bottom_panel_collision_is_reported_without_changing_recipe(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            source = self._private_recipe(directory, bottom=True)
            path = directory / "capture.png"
            Image.new("RGB", (800, 768), "#123456").save(path)
            before = source.read_bytes()
            result = compare(path, path, recipe_token=str(source))
            self.assertEqual(result["regions"][0]["expected_rect"]["y"], 728)
            self.assertEqual({item["code"] for item in result["layout_issues"]},
                             {"icon_outside_output", "icon_overlaps_panel"})
            self.assertEqual(source.read_bytes(), before)
            self.assertTrue(result["identical"])

    def test_overlay_and_heatmap_are_private_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            ref, current = directory / "ref.png", directory / "current.png"
            overlay, heatmap = directory / "overlay.png", directory / "heatmap.png"
            Image.new("RGB", (12, 12), "#000000").save(ref)
            Image.new("RGB", (12, 12), "#ffffff").save(current)
            result = compare(ref, current, overlay=overlay, heatmap=heatmap)
            self.assertEqual(result["overlay"], str(overlay))
            for path in (overlay, heatmap):
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                with Image.open(path) as image:
                    self.assertEqual(image.size, (12, 12))
            with Image.open(heatmap) as image:
                self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
            with self.assertRaisesRegex(ValueError, "exists"):
                compare(ref, current, overlay=overlay)
            self.assertTrue(overlay.exists())
            with self.assertRaisesRegex(ValueError, "distinct"):
                compare(ref, current, overlay=directory / "same.png",
                        heatmap=directory / "same.png")
            only = directory / "new.png"
            with self.assertRaisesRegex(ValueError, "exists"):
                compare(ref, current, overlay=only, heatmap=heatmap)
            self.assertFalse(only.exists(), "Partial diagnostics must be rolled back")

    def test_invalid_recipe_is_rejected_before_saving_diagnostics(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            ref = directory / "reference.png"
            Image.new("RGB", (12, 12)).save(ref)
            output = directory / "overlay.png"
            with self.assertRaisesRegex(ValueError, "Invalid or unsafe recipe"):
                compare(ref, ref, recipe_token=str(directory / "missing.json"), overlay=output)
            self.assertFalse(output.exists())

    def test_cli_recipe_and_artifacts_return_machine_readable_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            source = self._private_recipe(directory)
            ref, overlay = directory / "reference.png", directory / "overlay.png"
            Image.new("RGB", (1024, 768)).save(ref)
            from unittest.mock import patch
            with patch("builtins.print") as printer:
                code = main([str(ref), str(ref), "--recipe", str(source),
                             "--overlay", str(overlay)])
            self.assertEqual(code, 0)
            report = json.loads(printer.call_args.args[0])
            self.assertEqual(report["recipe"]["schema_version"], 5)
            self.assertEqual(report["overlay"], str(overlay))
            self.assertEqual(report["layout_issues"], [])


if __name__ == "__main__":
    unittest.main()
