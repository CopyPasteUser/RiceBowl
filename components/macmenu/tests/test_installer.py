"""Installer safety and upgrade regression tests; no real user paths touched."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("macmenu_installer", PROJECT / "scripts/install_user.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = self.root / "share/macmenu"
        self.link = self.root / "bin/macmenu"
        self.desktop = self.root / "share/applications/macmenu.desktop"

    def test_fresh_install_creates_only_managed_paths(self):
        installer.verify_existing(self.app, self.link, self.desktop)
        backup = installer.upgrade(PROJECT, self.app, self.link, self.desktop)
        self.assertIsNone(backup)
        self.assertEqual(self.link.resolve(), self.app / "launcher")
        self.assertTrue((self.app / ".macmenu-managed").is_file())
        self.assertIn("X-MacMenu-Managed=true", self.desktop.read_text())
        self.assertIn("1.0.0rc11", (self.app / "macmenu/__init__.py").read_text())
        for name in ("macmenu-app.svg", "macmenu-penguin.svg", "macmenu-penguin-ink.svg"):
            self.assertTrue((self.app / "assets" / name).is_file())
        self.assertIn(f"Icon={self.app / 'assets/macmenu-app.svg'}", self.desktop.read_text())
        self.assertFalse((self.root / "share/macmenu-backups").exists())

    def test_installed_symlink_forwards_command_line_flags(self):
        installer.upgrade(PROJECT, self.app, self.link, self.desktop)
        # Fake module checks the real installed shell wrapper and symlink
        # without launching a GUI or affecting the host GApplication.
        (self.app / "macmenu/__main__.py").write_text(
            "import json, sys\nprint(json.dumps(sys.argv[1:]))\n",
            encoding="utf-8",
        )
        expected = ["--toggle", "--hide", "--show", "--quit", "--version"]
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        result = subprocess.run(
            [str(self.link), *expected], capture_output=True, text=True,
            env=env, cwd=self.root, timeout=3,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), expected)

    def test_toggle_prefers_fast_native_activation_and_falls_back(self):
        installer.upgrade(PROJECT, self.app, self.link, self.desktop)
        (self.app / "macmenu/__main__.py").write_text(
            "import json, sys\nprint(json.dumps(sys.argv[1:]))\n", encoding="utf-8"
        )
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        fake_gapplication = fake_bin / "gapplication"
        fake_gapplication.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" > "$MACMENU_TEST_GAPPLICATION_LOG"\n'
            'exit "${MACMENU_TEST_GAPPLICATION_EXIT:-0}"\n',
            encoding="utf-8",
        )
        fake_gapplication.chmod(0o755)
        log = self.root / "gapplication-args.txt"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env["PATH"] = str(fake_bin) + os.pathsep + env.get("PATH", "")
        env["MACMENU_TEST_GAPPLICATION_LOG"] = str(log)

        quick = subprocess.run([str(self.link), "--toggle"], capture_output=True, text=True, env=env, cwd=self.root, timeout=3)
        self.assertEqual(quick.returncode, 0, quick.stderr)
        self.assertEqual(quick.stdout.strip(), "", "A warm toggle must not launch Python")
        self.assertEqual(log.read_text().strip(), "launch io.github.xfce.MacMenu")

        env["MACMENU_TEST_GAPPLICATION_EXIT"] = "1"
        fallback = subprocess.run([str(self.link), "--toggle"], capture_output=True, text=True, env=env, cwd=self.root, timeout=3)
        self.assertEqual(fallback.returncode, 0, fallback.stderr)
        self.assertEqual(json.loads(fallback.stdout), ["--toggle"])

        version = subprocess.run([str(self.link), "--version"], capture_output=True, text=True, env=env, cwd=self.root, timeout=3)
        self.assertEqual(json.loads(version.stdout), ["--version"])

    def test_old_user_install_is_backed_up_and_replaced(self):
        self.app.mkdir(parents=True)
        (self.app / ".macmenu-managed").touch()
        (self.app / "stale-rc2-module.py").write_text("old version")
        (self.app / "macmenu").mkdir()
        (self.app / "macmenu/session.py").write_text("legacy session controls")
        self.desktop.parent.mkdir(parents=True)
        self.desktop.write_text("[Desktop Entry]\nX-MacMenu-Managed=true\nExec=old\n")
        self.link.parent.mkdir(parents=True)
        self.link.symlink_to(self.app / "launcher")
        settings = self.root / "config/macmenu/settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text('{"favorites":["app.desktop"],"view":"classic"}')
        installer.verify_existing(self.app, self.link, self.desktop)
        backup = installer.upgrade(PROJECT, self.app, self.link, self.desktop)
        self.assertTrue((backup / "stale-rc2-module.py").is_file())
        self.assertFalse((self.app / "stale-rc2-module.py").exists())
        self.assertFalse((self.app / "macmenu/session.py").exists())
        self.assertEqual(self.link.resolve(), self.app / "launcher")
        self.assertIn("macmenu/launcher", self.desktop.read_text())
        self.assertEqual(settings.read_text(), '{"favorites":["app.desktop"],"view":"classic"}')

    def test_unmanaged_paths_are_never_replaced(self):
        self.app.mkdir(parents=True)
        (self.app / "user-data.txt").write_text("must stay")
        with self.assertRaises(installer.InstallError):
            installer.verify_existing(self.app, self.link, self.desktop)
        self.assertEqual((self.app / "user-data.txt").read_text(), "must stay")

    def test_unrelated_launcher_symlink_is_rejected(self):
        self.link.parent.mkdir(parents=True)
        self.link.symlink_to(self.root / "other-application")
        with self.assertRaises(installer.InstallError):
            installer.verify_existing(self.app, self.link, self.desktop)

    def test_only_exact_macmenu_module_process_matches(self):
        self.assertTrue(installer.is_macmenu_command(["/usr/bin/python3", "-m", "macmenu", "--show"]))
        self.assertFalse(installer.is_macmenu_command(["/usr/bin/python3", "-m", "otherapp"]))
        self.assertFalse(installer.is_macmenu_command(["/usr/bin/python3", "/path/macmenu.py"]))
        self.assertFalse(installer.is_macmenu_command(["/usr/bin/python3", "-m", "macmenu-malicious"]))

    def test_debian_removal_requires_explicit_interactive_approval(self):
        with patch.object(installer.sys.stdin, "isatty", return_value=False), \
             patch.object(installer.subprocess, "run") as run:
            with self.assertRaises(installer.InstallError):
                installer.resolve_system_package("1.0.0~rc3")
            run.assert_not_called()
        with patch.object(installer.sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="n"), \
             patch.object(installer.subprocess, "run") as run:
            with self.assertRaises(installer.InstallError):
                installer.resolve_system_package("1.0.0~rc3")
            run.assert_not_called()

    def test_debian_removal_only_targets_macmenu_package(self):
        with patch.object(installer.sys.stdin, "isatty", return_value=True), \
             patch("builtins.input", return_value="yes"), \
             patch.object(installer, "installed_system_package", return_value=None), \
             patch.object(installer.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as run:
            installer.resolve_system_package("1.0.0~rc3")
            run.assert_called_once_with(["sudo", "apt-get", "remove", "xfce-macmenu"], check=False)

    def test_upgrade_staging_failure_preserves_old_files(self):
        self.app.mkdir(parents=True)
        (self.app / ".macmenu-managed").touch()
        old = self.app / "important-old-file"
        old.write_text("untouched")
        with patch.object(installer, "desktop_contents", side_effect=OSError("simulated failure")):
            with self.assertRaises(OSError):
                installer.upgrade(PROJECT, self.app, self.link, self.desktop)
        self.assertEqual(old.read_text(), "untouched")
        self.assertFalse(self.link.exists())

    def test_dry_run_never_changes_paths(self):
        data_home = self.root / "share"
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(data_home),
                                          "XDG_BIN_HOME": str(self.root / "bin")}), \
             patch.object(installer, "installed_system_package", return_value=None), \
             patch.object(installer, "running_macmenu_pids", return_value=[]):
            self.assertEqual(installer.main(["--dry-run"]), 0)
        self.assertFalse(self.app.exists())
        self.assertFalse(self.link.exists())


if __name__ == "__main__":
    unittest.main()
