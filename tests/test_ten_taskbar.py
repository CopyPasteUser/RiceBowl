"""Windows 10 taskbar visibility preferences stay local, bounded and safe."""

import json
import tempfile
import unittest
from pathlib import Path

from macrice.ten_taskbar import DEFAULTS, load, save


class TenTaskbarPreferencesTests(unittest.TestCase):
    def test_defaults_and_atomic_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ricehub/windows10-taskbar.json"
            self.assertEqual(load(path), DEFAULTS)
            save(path, {"search_mode": "hidden", "task_view": True})
            self.assertEqual(load(path), {"search_mode": "hidden", "task_view": True})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.glob(".ten-taskbar-*")), [])

    def test_symlink_and_invalid_values_rejected_without_clobbering(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.json"
            source.write_text(json.dumps({"schema": 2, "options": DEFAULTS}))
            link = root / "link.json"
            link.symlink_to(source)
            with self.assertRaises(ValueError):
                load(link)
            with self.assertRaises(ValueError):
                save(link, DEFAULTS)
            with self.assertRaises(ValueError):
                save(source, {"search_mode": "no", "task_view": True})
            self.assertEqual(load(source), DEFAULTS)

    def test_existing_schema_one_preserves_search_visibility(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "windows10-taskbar.json"
            for enabled in (True, False):
                path.write_text(json.dumps({"schema": 1, "options": {
                    "search": enabled, "task_view": False}}))
                self.assertEqual(load(path), {"search_mode": "icon" if enabled else "hidden",
                                              "task_view": False})


if __name__ == "__main__":
    unittest.main()
