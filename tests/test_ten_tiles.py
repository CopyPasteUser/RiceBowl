"""Bounded, per-rice Windows 10 Start customization without desktop writes."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from macrice.ten_tiles import (default_layout, grid_positions, load, move, move_to, pin,
                               rename_group, resize, save, tile_location, unpin,
                               validate)


class App:
    def __init__(self, identifier, title):
        self.identifier, self.title = identifier, title

    def get_id(self):
        return self.identifier

    def get_display_name(self):
        return self.title

    def get_name(self):
        return self.title


APPS = [App(f"a{i}.desktop", name) for i, name in enumerate(
    ("File Manager", "Browser", "Settings", "Terminal", "Editor", "Music"))]


class TenTileTests(unittest.TestCase):
    def layout(self):
        return default_layout(APPS, ("a1.desktop",))

    def test_default_is_real_bounded_and_separate_from_pins(self):
        result = self.layout()
        self.assertEqual([group["name"] for group in result["groups"]],
                         ["Productivity", "Explore"])
        self.assertEqual(result["groups"][0]["tiles"][0]["id"], "a1.desktop")
        self.assertEqual(sum(len(group["tiles"]) for group in result["groups"]), 6)

    def test_pin_unpin_resize_move_and_rename_are_immutable(self):
        original = self.layout()
        result = unpin(original, "a1.desktop")
        self.assertIsNone(tile_location(result, "a1.desktop"))
        result = pin(result, "a1.desktop", group_index=1)
        self.assertEqual(tile_location(result, "a1.desktop")[0], 1)
        result = resize(result, "a1.desktop", "wide")
        self.assertEqual(result["groups"][1]["tiles"][-1]["size"], "wide")
        result = move(result, "a1.desktop", group_index=0)
        result = move(result, "a1.desktop", offset=-5)
        self.assertEqual(tile_location(result, "a1.desktop"), (0, 0))
        result = rename_group(result, 1, "  My tools  ")
        self.assertEqual(result["groups"][1]["name"], "My tools")
        self.assertEqual(original["groups"][0]["tiles"][0]["id"], "a1.desktop")

    def test_layout_file_roundtrip_has_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ricehub" / "windows10-tiles.json"
            self.assertIsNone(load(path))
            result = self.layout()
            save(path, result)
            self.assertEqual(load(path), result)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(stored["schema"], 1)

    def test_drag_reorder_same_group_and_between_groups(self):
        original = self.layout()
        ids = [tile["id"] for tile in original["groups"][0]["tiles"]]
        moved = move_to(original, ids[0], ids[2], after=True)
        self.assertEqual([tile["id"] for tile in moved["groups"][0]["tiles"]],
                         [ids[1], ids[2], ids[0], ids[3]])
        destination = original["groups"][1]["tiles"][0]["id"]
        moved = move_to(moved, ids[0], destination)
        self.assertEqual(tile_location(moved, ids[0]), (1, 0))
        self.assertEqual(tile_location(original, ids[0]), (0, 0))
        self.assertEqual(move_to(moved, ids[0], ids[0]), moved)

    def test_rejects_corrupt_symlinked_or_unbounded_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tiles.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema"):
                load(path)
            link = Path(tmp) / "link.json"
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                load(link)
            with self.assertRaises(ValueError):
                save(link, self.layout())
        invalid = self.layout()
        invalid["groups"][0]["tiles"].append(
            invalid["groups"][0]["tiles"][0].copy())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate(invalid)
        with self.assertRaises(ValueError):
            rename_group(self.layout(), 0, "\n")

    def test_mosaic_respects_size_spans_without_overlap(self):
        result = self.layout()["groups"][0]["tiles"]
        for item, size in zip(result, ("wide", "small", "medium", "large")):
            item["size"] = size
        positions = grid_positions(result)
        cells = []
        for col, row, width, height in positions:
            self.assertLessEqual(col + width, 4)
            cells.extend((col + x, row + y) for x in range(width)
                         for y in range(height))
        self.assertEqual(len(cells), len(set(cells)))
        self.assertEqual(len(positions), len(result))


if __name__ == "__main__":
    unittest.main()
