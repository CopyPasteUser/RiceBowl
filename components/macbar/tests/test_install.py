"""Installer checks using isolated user directories; never touch the real session."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


INSTALL = Path(__file__).resolve().parents[1] / "install.sh"
UNINSTALL = Path(__file__).resolve().parents[1] / "uninstall.sh"


class InstallTests(unittest.TestCase):
    def test_replace_requires_autostart(self) -> None:
        proc = subprocess.run(["sh", str(INSTALL), "--replace-xfce"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("requires --autostart", proc.stderr)

    def test_install_autostart_and_config_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            env = {**os.environ, "HOME": folder, "XDG_CONFIG_HOME": str(root / "config"),
                   "XDG_DATA_HOME": str(root / "data")}
            config = root / "config/macbar/config.json"
            config.parent.mkdir(parents=True)
            config.write_text('{"theme":"light"}')
            subprocess.run(["sh", str(INSTALL), "--autostart", "--replace-xfce"],
                           check=True, capture_output=True, env=env)

            self.assertEqual(config.read_text(), '{"theme":"light"}')
            desktop = (root / "config/autostart/macbar.desktop").read_text()
            self.assertIn("--replace-xfce", desktop)
            self.assertIn("OnlyShowIn=XFCE;", desktop)
            self.assertTrue((root / ".local/bin/macbar").is_file())
            self.assertTrue((root / "data/macbar/macbar.py").is_file())

            subprocess.run(["sh", str(UNINSTALL)], check=True, capture_output=True, env=env)
            self.assertFalse((root / "config/autostart/macbar.desktop").exists())
            self.assertFalse((root / ".local/bin/macbar").exists())
            self.assertEqual(config.read_text(), '{"theme":"light"}')


if __name__ == "__main__":
    unittest.main()
