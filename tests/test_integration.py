"""Full user-local install in an isolated fake home; never touches the real desktop."""

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallIntegrationTests(unittest.TestCase):
    def test_all_three_install_without_starting_or_replacing_xfce(self):
        with tempfile.TemporaryDirectory(prefix="macrice-install-") as directory:
            base = Path(directory)
            env = os.environ.copy()
            locations = {
                "HOME": base / "home",
                "XDG_DATA_HOME": base / "data",
                "XDG_BIN_HOME": base / "bin",
                "XDG_CONFIG_HOME": base / "config",
                "XDG_RUNTIME_DIR": base / "runtime",
            }
            for path in locations.values():
                path.mkdir(parents=True)
            env.update({key: str(path) for key, path in locations.items()})
            env["PATH"] = "/usr/bin:/bin"

            config = locations["XDG_CONFIG_HOME"] / "macmenu/settings.json"
            config.parent.mkdir()
            config.write_text(json.dumps({"theme": "violet", "favorites": ["org.xfce.Thunar"]}))
            dock_pin = locations["XDG_CONFIG_HOME"] / "plank/dock1/launchers/user-app.dockitem"
            dock_pin.parent.mkdir(parents=True)
            dock_pin.write_text("[PlankDockItemPreferences]\nLauncher=file:///usr/share/applications/thunar.desktop\n")

            for _ in range(2):
                process = subprocess.run(
                    ["bash", str(ROOT / "install.sh"), "--no-start"],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=45,
                )
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

            for name in ("macrice", "macmenu", "macos-control-center-toggle", "macbar"):
                launcher = locations["XDG_BIN_HOME"] / name
                self.assertTrue(launcher.is_file(), name)
                self.assertTrue(os.access(launcher, os.X_OK), name)
            self.assertTrue((locations["XDG_DATA_HOME"] / "macrice" / ".macrice-managed").exists())
            self.assertTrue((locations["XDG_CONFIG_HOME"] / "autostart/macos-control-center-resident.desktop").exists())
            self.assertFalse((locations["XDG_CONFIG_HOME"] / "autostart/macbar.desktop").exists())
            self.assertFalse((locations["XDG_CONFIG_HOME"] / "xfce4").exists())
            self.assertIn("thunar.desktop", dock_pin.read_text())
            settings = json.loads(config.read_text())
            self.assertEqual(settings["favorites"], ["org.xfce.Thunar"])
            self.assertEqual(settings["theme"], "violet")

            check = subprocess.run(
                [str(locations["XDG_BIN_HOME"] / "macrice"), "status"],
                env=env, capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertIn("MacMenu: installed", check.stdout)
            self.assertIn("Control Center: installed", check.stdout)
            self.assertIn("MacBar: installed", check.stdout)
            self.assertIn("Plank:", check.stdout)


if __name__ == "__main__":
    unittest.main()
