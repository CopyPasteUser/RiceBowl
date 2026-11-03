"""RiceBowl branding and safe upgrade regression tests."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice import aero, heritage, shell_session, ten
from macrice.installer import project_root


class RiceBowlBrandingTests(unittest.TestCase):
    def test_metadata_migration_is_exact_and_backed_up(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source"
            current = source / "assets/themes/RiceHub-Aero"
            installed = root / "data/themes/RiceHub-Aero"
            for directory in (current, installed):
                (directory / "scalable/apps").mkdir(parents=True)
                (directory / "gtk-3.0").mkdir()
            items = {
                "index.theme": b"[Desktop Entry]\nName=RiceBowl Aero\n",
                "scalable/apps/start-here.svg": b"<svg><title>RiceBowl</title></svg>\n",
                "gtk-3.0/gtk.css": b"/* personal-compatible theme */\n",
            }
            for relative, data in items.items():
                (current / relative).write_bytes(data)
                (installed / relative).write_bytes(data.replace(b"RiceBowl", b"RiceHub"))
            bundles = (("assets/themes/RiceHub-Aero", "themes/RiceHub-Aero"),)
            packages = aero.preflight(source, root / "data", bundles)
            aero.install(packages)
            for relative, data in items.items():
                self.assertEqual((installed / relative).read_bytes(), data)
            backups = list((installed.parent / ".ricebowl-metadata-backups").glob("*.bak"))
            self.assertEqual(len(backups), 2)
            self.assertTrue(all(b.stat().st_mode & 0o077 == 0 for b in backups))
            self.assertEqual(len(aero.preflight(source, root / "data", bundles)), 1)

    def test_customized_icon_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src"
            dest = root / "data/themes/RiceHub-Aero"
            source.mkdir()
            dest.mkdir(parents=True)
            (source / "index.theme").write_text("Name=RiceBowl Aero\n")
            (dest / "index.theme").write_text("Name=custom user edit\n")
            with self.assertRaisesRegex(aero.AeroAssetError, "conflicts"):
                aero.preflight(root, root / "data", (("src", "themes/RiceHub-Aero"),))
            self.assertEqual((dest / "index.theme").read_text(), "Name=custom user edit\n")

    def test_legacy_autostarts_and_rebrand_roundtrip(self):
        root = project_root()
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            bindir = config / "bin"
            with mock.patch.object(aero, "bin_home", return_value=bindir), \
                 mock.patch.object(ten, "bin_home", return_value=bindir), \
                 mock.patch.object(heritage, "bin_home", return_value=bindir):
                for module in (aero, ten):
                    target = module.autostart_file(config)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    legacy = module.legacy_autostart_content(root)
                    canonical = module.autostart_content(root)
                    self.assertIn("Name=RiceHub", legacy)
                    self.assertIn("Name=RiceBowl", canonical)
                    target.write_text(legacy)
                    self.assertEqual(module.read_autostart(config), legacy)
                    module.write_autostart(config, canonical)
                    self.assertEqual(target.read_text(), canonical)
                    module.write_autostart(config, legacy)
                    self.assertEqual(target.read_text(), legacy)
                for key in heritage.PROFILES:
                    target = heritage._target(key, config)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    legacy = heritage.legacy_autostart_content(key)
                    canonical = heritage.autostart_content(key)
                    self.assertIn("Name=RiceHub", legacy)
                    self.assertIn("Name=RiceBowl", canonical)
                    target.write_text(legacy)
                    self.assertEqual(heritage.read_autostart(key, config), legacy)
                    heritage.write_autostart(key, config, canonical)
                    self.assertEqual(target.read_text(), canonical)
                    heritage.write_autostart(key, config, legacy)
                    self.assertEqual(target.read_text(), legacy)

    def test_session_reconciler_migrates_only_owned_label(self):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            with mock.patch("macrice.environment.bin_home", return_value=config / "bin"):
                shell_session.install_login_reconciler(config)
                target = config / "autostart/ricehub-session-sync.desktop"
                branded = target.read_text()
                self.assertIn("Name=RiceBowl Session Reconcile", branded)
                target.write_text(branded.replace("Name=RiceBowl", "Name=RiceHub"))
                shell_session.install_login_reconciler(config)
                self.assertEqual(target.read_text(), branded)
                target.write_text(branded.replace("Name=RiceBowl", "Name=User Project"))
                with self.assertRaisesRegex(OSError, "customized"):
                    shell_session.install_login_reconciler(config)

    def test_display_names_and_generator_syntax(self):
        root = project_root()
        for family in ("Aero", "Chrome", "Classic", "Frutiger", "Luna", "Ten-Dark", "Ten-Light"):
            path = root / "assets/themes" / ("RiceHub-" + family) / "index.theme"
            self.assertIn("Name=RiceBowl", path.read_text())
        for family in ("Aero", "Chrome-Icons", "Classic-Icons", "Frutiger-Icons",
                       "Luna-Icons", "Ten-Penguin"):
            path = root / "assets/icons" / ("RiceHub-" + family) / "index.theme"
            self.assertIn("Name=RiceBowl", path.read_text())
        self.assertEqual((root / "assets/ricehub-symbolic.svg").read_bytes(),
                         (root / "assets/ricebowl-symbolic.svg").read_bytes())
        for script in ("build_aero_assets.py", "build_ten_assets.py", "build_heritage_assets.py"):
            file = root / "scripts" / script
            compile(file.read_text(), str(file), "exec")
        project = (root / "pyproject.toml").read_text()
        self.assertIn('name = "ricebowl-xfce"', project)
        self.assertIn('version = "0.9.0"', project)


if __name__ == "__main__":
    unittest.main()
