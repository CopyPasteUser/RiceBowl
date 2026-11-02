"""Resource profiles and on-demand measurements do not touch a real desktop."""

import json
import tempfile
import unittest
from pathlib import Path

from macrice.performance import PROFILES, _component, apply_profile, measure_processes


class PerformanceTests(unittest.TestCase):
    def test_profiles_only_change_selected_control_center_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config/macos-control-center/config.json"
            config.parent.mkdir(parents=True)
            previous = {"theme": "midnight", "poll_seconds": 13,
                        "devices": [{"name": "Personal NAS"}], "resource_profile": "balanced"}
            config.write_text(json.dumps(previous))
            backup = apply_profile("light", config_root=root / "config", data_root=root / "data")
            updated = json.loads(config.read_text())
            self.assertEqual(updated["poll_seconds"], 13)
            self.assertEqual(updated["devices"], previous["devices"])
            self.assertEqual(updated["theme"], "midnight")
            self.assertEqual(updated["resource_profile"], "light")
            self.assertFalse(updated["media_thumbnail"])
            self.assertEqual(json.loads((backup / "control-center-config.json").read_text()), previous)
            self.assertEqual((backup / "control-center-config.json").stat().st_mode & 0o777, 0o600)

    def test_visual_maps_to_existing_responsive_policy(self):
        self.assertEqual(PROFILES["visual"]["resource_profile"], "responsive")

    def test_does_not_follow_symlinked_preferences(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config/macos-control-center/config.json"
            config.parent.mkdir(parents=True)
            personal = root / "other.json"
            personal.write_text('{"theme":"light"}')
            config.symlink_to(personal)
            with self.assertRaises(ValueError):
                apply_profile("light", config_root=root / "config", data_root=root / "data")
            self.assertEqual(personal.read_text(), '{"theme":"light"}')

    def test_process_classifier_is_bounded_to_known_components(self):
        self.assertEqual(_component(["/usr/bin/python3", "-m", "macmenu", "--toggle"]), "MacMenu")
        self.assertEqual(_component(["/usr/bin/python3", "/tmp/macbar.py"]), "MacBar")
        self.assertEqual(_component(["/usr/bin/plank"]), "Plank")
        self.assertIsNone(_component(["/usr/bin/python3", "myservice.py", "macmenu"]))

    def test_empty_proc_report_is_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(measure_processes(proc_root=Path(tmp)), [])


if __name__ == "__main__":
    unittest.main()
