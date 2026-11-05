"""Visual pack import, integrity, collision and rollback tests on isolated XDG roots."""

import hashlib
import json
import os
import tempfile
import unittest
import warnings
import zipfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from macrice.rice import RiceError, restore
from macrice.hub_catalog import selected_style, style_options
from macrice import cli
from macrice.riceware import pack_import, packs
from test_rice import FakeBackend, setup_apps


PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89")


def bundle(folder, *, pack_id="my-aero", base_style="aero-meadow", assets=None,
           files=None, **extra):
    content = files if files is not None else {
        "wallpaper/background.png": PNG,
        "gtk/gtk-3.0/gtk.css": b"@define-color bg_color #234567;\nwindow { background: @bg_color; }\n",
        "xfwm/xfwm4/themerc": b"active_text_color=#fff\n",
        "icons/index.theme": b"[Icon Theme]\nName=My Aero\nInherits=Adwaita\n",
        "icons/16x16/apps/example.png": PNG,
    }
    declared = assets if assets is not None else {
        "wallpaper": "wallpaper/background.png", "gtk": True, "xfwm": True, "icons": True,
    }
    manifest = {
        "schema_version": 2, "id": pack_id, "name": "My Aero", "base_style": base_style,
        "description": "Safe test pack", "license": {"spdx": "CC0-1.0",
                                                 "author": "Example", "source": "Original test artwork"},
        "assets": declared,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in content.items()},
        **extra,
    }
    target = folder / "example.zip"
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, data in content.items():
            archive.writestr(name, data)
    return target


class PackImportTests(unittest.TestCase):
    def test_inspection_is_read_only_and_license_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            archive = bundle(home)
            detail = pack_import.inspect_archive(archive)
            self.assertEqual(detail["assets"]["gtk"], True)
            self.assertFalse((home / "data").exists())
            with self.assertRaisesRegex(ValueError, "license"):
                pack_import.install_archive(archive, data_root=home / "data")
            self.assertFalse((home / "data").exists())

    def test_build_roundtrip_and_never_overwrite_user_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            draft = root / "draft"
            (draft / "wallpaper").mkdir(parents=True)
            (draft / "wallpaper/background.png").write_bytes(PNG)
            definition = {
                "schema_version": 2, "id": "my-scene", "name": "My scene",
                "base_style": "winxp", "description": "A wallpaper rice",
                "license": {"spdx": "CC0-1.0", "author": "Creator",
                            "source": "Original artwork"},
                "assets": {"wallpaper": "wallpaper/background.png"},
            }
            (draft / "manifest.json").write_text(json.dumps(definition))
            output = root / "pack.zip"
            with redirect_stdout(StringIO()):
                self.assertEqual(cli.main(["riceware", "packs", "build", "--directory",
                                           str(draft), "--output", str(output)]), 0)
            self.assertEqual(pack_import.inspect_archive(output)["id"], "my-scene")
            self.assertTrue(output.exists())
            with self.assertRaisesRegex(ValueError, "already exists"):
                pack_import.build_archive(draft, output)
            self.assertTrue(output.exists())

    def test_import_discover_validate_and_apply_to_full_rice_then_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, config = root / "data", root / "config"
            setup_apps(config)
            fake = FakeBackend()
            previous = fake.values.copy()
            archive = bundle(root)
            pack = pack_import.install_archive(archive, accept_license=True, data_root=data)
            self.assertEqual(pack.source, "installed")
            discovered, warnings = packs.discover(data / "ricebowl/packs")
            self.assertEqual(warnings, ())
            self.assertIn(pack, discovered)
            self.assertIn((pack.id, "My Aero · visual pack"), style_options("windows7", (pack,)))
            self.assertEqual(selected_style(pack.id, (pack,)), ("aero-meadow", "My Aero"))
            with mock.patch("macrice.riceware.packs.discover", return_value=((pack,), ())):
                self.assertEqual(packs.shell_for_theme(pack_import.theme_name(pack)), ("aero", False))
            appearance, wallpaper = pack_import.style_for(pack, data_root=data)
            self.assertEqual(appearance.gtk, pack_import.theme_name(pack))
            self.assertTrue(wallpaper.is_file())
            self.assertEqual(pack_import.theme_name(pack), appearance.xfwm)
            self.assertEqual(appearance.icon_theme, appearance.gtk)
            with mock.patch("macrice.rice.os.geteuid", return_value=1000):
                changes, _apps, _source, _target = pack_import.plan_pack(
                    pack, backend=fake, data_root=data, config_root=config)
                self.assertEqual(fake.values, previous)
                self.assertEqual(next(c["after"] for c in changes if c["key"] == "/Net/ThemeName"), appearance.gtk)
                backup = pack_import.apply_pack(pack, backend=fake, data_root=data, config_root=config)
                self.assertTrue(backup.is_dir())
                self.assertEqual(fake.values[("xfconf", "xsettings", "/Net/ThemeName")], appearance.gtk)
                self.assertEqual(fake.values[("xfconf", "xsettings", "/Net/IconThemeName")], appearance.gtk)
                restore(backend=fake, data_root=data, config_root=config)
            self.assertEqual(fake.values, previous)

    def test_active_pack_refuses_uninstall_and_removal_is_recoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            pack = pack_import.install_archive(bundle(root), accept_license=True, data_root=data)
            fake = FakeBackend()
            fake.values[("xfconf", "xsettings", "/Net/ThemeName")] = pack_import.theme_name(pack)
            with self.assertRaisesRegex(ValueError, "active"):
                pack_import.remove_installed(pack, backend=fake, data_root=data)
            self.assertEqual(pack_import.verify_installed(pack, data_root=data)["id"], pack.id)
            fake.values[("xfconf", "xsettings", "/Net/ThemeName")] = "WhiteSur-Dark"
            recovery = pack_import.remove_installed(pack, backend=fake, data_root=data)
            self.assertTrue((recovery / "assets/theme/gtk-3.0/gtk.css").is_file())
            self.assertTrue((recovery / "manifest.json").is_file())
            self.assertFalse((data / "ricebowl/packs/my-aero.json").exists())
            self.assertFalse((data / "themes" / pack_import.theme_name(pack)).is_symlink())

    def test_rejects_untrusted_paths_scripts_links_and_checksums(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            samples = (
                {"wallpaper/../../secret.png": PNG},
                {"gtk/gtk-3.0/run.sh": b"#!/bin/sh\nexit 0\n"},
                {"gtk/gtk-3.0/gtk.css": b"@import url('file:///etc/passwd');"},
                {"gtk/gtk-3.0/gtk.css": b"window { background-image: url(https://example.test/a); }"},
            )
            for files in samples:
                with self.subTest(name=list(files)):
                    categories = {"gtk": True} if "gtk" in next(iter(files)) else {"wallpaper": next(iter(files))}
                    with self.assertRaises(ValueError):
                        pack_import.inspect_archive(bundle(root, files=files, assets=categories))
            bad = bundle(root)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(bad, "a") as archive:
                    archive.writestr("icons/16x16/apps/example.png", PNG)
            with self.assertRaisesRegex(ValueError, "duplicated"):
                pack_import.inspect_archive(bad)

    def test_failed_install_collisions_do_not_modify_other_packs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            archive = bundle(root)
            pack = pack_import.install_archive(archive, accept_license=True, data_root=data)
            with self.assertRaisesRegex(ValueError, "already in use"):
                pack_import.install_archive(archive, accept_license=True, data_root=data)
            asset = data / "ricebowl/assets" / (pack.id + "-" + pack.revision[:12]) / "theme/gtk-3.0/gtk.css"
            asset.write_text("tampered")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                pack_import.verify_installed(pack, data_root=data)
            self.assertTrue(asset.exists())

    def test_malicious_symlink_not_followed_and_only_declared_assets_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            archive = bundle(root, assets={"wallpaper": "wallpaper/background.png"},
                             files={"wallpaper/background.png": PNG})
            pack = pack_import.install_archive(archive, accept_license=True, data_root=data)
            self.assertEqual(pack.asset_types, ("wallpaper",))
            self.assertFalse((data / "themes" / pack_import.theme_name(pack)).exists())
            stored = data / "ricebowl/assets" / (pack.id + "-" + pack.revision[:12]) / "wallpaper/background.png"
            stored.unlink()
            stored.symlink_to(Path("/etc/passwd"))
            with self.assertRaises(OSError):
                pack_import.style_for(pack, data_root=data)

    def test_partial_install_is_rolled_back_on_link_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            archive = bundle(root)
            original = os.symlink
            calls = []

            def fail_second(target, link):
                calls.append(link)
                if len(calls) == 2:
                    raise OSError("simulated symlink failure")
                return original(target, link)

            with mock.patch("macrice.riceware.pack_import.os.symlink", side_effect=fail_second):
                with self.assertRaisesRegex(OSError, "simulated"):
                    pack_import.install_archive(archive, accept_license=True, data_root=data)
            self.assertFalse((data / "ricebowl/packs/my-aero.json").exists())
            self.assertEqual(list((data / "ricebowl/assets").iterdir()), [])
            self.assertEqual(list((data / "themes").iterdir()), [])

    def test_apply_failure_restores_desktop_and_pending_snapshot_blocks_uninstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, config = root / "data", root / "config"
            setup_apps(config)
            pack = pack_import.install_archive(bundle(root), accept_license=True, data_root=data)
            fake = FakeBackend()
            before = fake.values.copy()
            fake.fail_key = "/general/theme"
            with mock.patch("macrice.rice.os.geteuid", return_value=1000):
                with self.assertRaisesRegex(RiceError, "rolled back"):
                    pack_import.apply_pack(pack, backend=fake, data_root=data, config_root=config)
            self.assertEqual(fake.values, before)
            fake.fail_key = None
            with mock.patch("macrice.rice.os.geteuid", return_value=1000):
                pack_import.apply_pack(pack, backend=fake, data_root=data, config_root=config)
            fake.values[("xfconf", "xsettings", "/Net/ThemeName")] = "OtherTheme"
            fake.values[("xfconf", "xsettings", "/Net/IconThemeName")] = "OtherIcons"
            fake.values[("xfconf", "xfwm4", "/general/theme")] = "OtherWM"
            with self.assertRaisesRegex(ValueError, "pending Rice restore"):
                pack_import.remove_installed(pack, backend=fake, data_root=data)


if __name__ == "__main__":
    unittest.main()
