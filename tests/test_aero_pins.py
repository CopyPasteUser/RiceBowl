"""User-local Aero taskbar pin configuration stays isolated and recoverable."""
import json
import tempfile
import unittest
from pathlib import Path

from macrice.aero_pins import (PIN_LIMIT, PinConfigError, load_pins, pin_file,
                              reorder_pins, save_pins, validate_ids)


class AeroPinsTests(unittest.TestCase):
    def test_reorder_pins_before_after_and_noop(self):
        entries = ("first.desktop", "second.desktop", "third.desktop")
        self.assertEqual(reorder_pins(entries, "first.desktop", "third.desktop"),
                         ("second.desktop", "first.desktop", "third.desktop"))
        self.assertEqual(reorder_pins(entries, "first.desktop", "third.desktop", after=True),
                         ("second.desktop", "third.desktop", "first.desktop"))
        self.assertEqual(reorder_pins(entries, "third.desktop", "first.desktop"),
                         ("third.desktop", "first.desktop", "second.desktop"))
        self.assertEqual(reorder_pins(entries, "unknown.desktop", "first.desktop"), entries)
        self.assertEqual(reorder_pins(entries, "first.desktop", "first.desktop"), entries)
        self.assertEqual(reorder_pins(entries, "first.desktop", "not-a-target"), entries)

    def test_reorder_rejects_invalid_or_duplicate_preferences(self):
        with self.assertRaises(PinConfigError):
            reorder_pins(("first.desktop", "first.desktop"), "first.desktop", "first.desktop")

    def test_all_installable_shells_have_isolated_pin_files(self):
        profiles = ("aero", "windows10", "winxp", "winclassic", "chromeos", "frutiger")
        paths = [pin_file(profile) for profile in profiles]
        self.assertEqual(len(set(paths)), len(profiles))
        for profile, path in zip(profiles, paths):
            self.assertEqual(path.name, f"{profile}-pins.json")
        with self.assertRaises(PinConfigError):
            pin_file("unexpected-profile")

    def test_pins_roundtrip_and_explicit_empty_choice(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ricehub/aero-pins.json"
            self.assertIsNone(load_pins(path))
            save_pins(path, ["org.xfce.Thunar.desktop", "firefox.desktop"])
            self.assertEqual(load_pins(path), ("org.xfce.Thunar.desktop", "firefox.desktop"))
            save_pins(path, [])
            self.assertEqual(load_pins(path), ())

    def test_invalid_file_is_not_overwritten_by_load(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "aero-pins.json"
            path.write_text("{not-json")
            with self.assertRaises(PinConfigError):
                load_pins(path)
            self.assertEqual(path.read_text(), "{not-json")

    def test_ids_are_bounded_and_non_executable(self):
        self.assertEqual(validate_ids(["org.example.App.desktop"]), ("org.example.App.desktop",))
        for ids in (["/tmp/evil.desktop"], ["../../../bad.desktop"], ["x.desktop", "x.desktop"],
                    ["x.desktop"] * (PIN_LIMIT + 1), ["x.desktop\nExec=evil"]):
            with self.assertRaises(PinConfigError):
                validate_ids(ids)

    def test_symlink_destination_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            victim = base / "important.json"
            victim.write_text("keep me")
            entry = base / "aero-pins.json"
            entry.symlink_to(victim)
            with self.assertRaises(PinConfigError):
                save_pins(entry, [])
            self.assertEqual(victim.read_text(), "keep me")

    def test_unknown_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "aero-pins.json"
            p.write_text(json.dumps({"schema": 2, "pinned": []}))
            with self.assertRaises(PinConfigError):
                load_pins(p)
