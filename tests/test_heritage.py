"""Each new rice is a real reversible session, not a demo dialog."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice import heritage
from macrice.cli import main
from macrice.hub_catalog import FAMILY_BY_KEY
from macrice.installer import project_root
from macrice.rice import RiceError, STYLES, apply, plan, restore
from macrice.session_shortcuts import _direct_commands, command_for
from macrice.shell_session import SHELLS, sync_theme
from tests.test_rice import FakeBackend, setup_apps


class HeritageTests(unittest.TestCase):
    def test_original_assets_are_complete(self):
        root = project_root()
        for key, profile in heritage.PROFILES.items():
            with self.subTest(key=key):
                self.assertEqual(FAMILY_BY_KEY[key].styles, (key,))
                self.assertTrue(FAMILY_BY_KEY[key].available)
                self.assertEqual(STYLES[key].gtk, profile.theme)
                self.assertEqual((root / "assets/wallpapers" / profile.wallpaper).read_bytes()[:3], b"\xff\xd8\xff")
                self.assertTrue((root / "assets/themes" / profile.theme / "xfwm4/close-active.png").is_file())
                self.assertTrue((root / "assets/icons" / profile.icon_theme / "scalable/apps/start-here.svg").is_file())
                self.assertEqual(len(heritage.preflight(key, root, root / "nonexistent-data")), 2)
                self.assertIn(f"{key}-shell", heritage.autostart_content(key))

    def test_every_theme_is_transactional_and_removes_other_shells(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            old = fake.values.copy()
            backups = []
            for key, profile in heritage.PROFILES.items():
                with self.subTest(key=key):
                    before = list(root.iterdir())
                    changes, *_ = plan(key, backend=fake, data_root=root / "data", config_root=root / "config")
                    self.assertEqual(list(root.iterdir()), before)
                    self.assertIn(profile.theme, [c["after"] for c in changes])
                    backup = apply(key, backend=fake, data_root=root / "data", config_root=root / "config")
                    backups.append(backup)
                    manifest = json.loads((backup / "manifest.json").read_text())
                    self.assertEqual(manifest["schema"], 5)
                    self.assertEqual(set(manifest["shell_autostarts"]), {"aero", "ten", *heritage.PROFILES})
                    self.assertEqual(fake.get("xfconf", "xsettings", "/Net/ThemeName"), profile.theme)
                    self.assertIsNotNone(heritage.read_autostart(key, root / "config"))
                    for other in heritage.PROFILES:
                        if other != key:
                            self.assertIsNone(heritage.read_autostart(other, root / "config"))
            for index, backup in enumerate(reversed(backups)):
                self.assertEqual(restore(backend=fake, data_root=root / "data", config_root=root / "config"), backup)
            self.assertEqual(fake.values, old)

    def test_conflicting_user_autostart_blocks_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = FakeBackend()
            setup_apps(root / "config")
            file = root / "config/autostart/ricehub-winxp-shell.desktop"
            file.parent.mkdir(parents=True)
            file.write_text("[Desktop Entry]\nExec=user-program\n")
            with self.assertRaisesRegex(RiceError, "customized"):
                apply("winxp", backend=fake, data_root=root / "data", config_root=root / "config")
            self.assertEqual(fake.calls, [])

    def test_cli_and_direct_shortcut_mapping(self):
        for key, profile in heritage.PROFILES.items():
            with self.subTest(key=key):
                with mock.patch("macrice.aero_shell.run", return_value=0) as shared:
                    self.assertEqual(main([f"{key}-shell", "--toggle-menu"]), 0)
                    shared.assert_called_once_with([f"ricehub-{key}-shell", "--toggle-menu"], profile=key)
                self.assertEqual(command_for("menu", profile.theme), ("macrice", f"{key}-shell", "--toggle-menu"))
                bindings = _direct_commands(profile.theme, Path("/tmp/installed-bin"))
                self.assertEqual(bindings["Super_L"], f"/tmp/installed-bin/ricehub-toggle {key}-menu")
                self.assertEqual(bindings["Control_R"], f"/tmp/installed-bin/ricehub-toggle {key}-control")

    def test_session_coordinator_never_starts_two_taskbars(self):
        for key, profile in heritage.PROFILES.items():
            self.assertEqual(SHELLS[key], f"{key}-shell")
            with (self.subTest(key=key), mock.patch.dict("os.environ", {"DISPLAY": ":8"}),
                  mock.patch("macrice.shell_session._shell", return_value=[]) as shell,
                  mock.patch("macrice.shell_session._stop", return_value=[]),
                  mock.patch("macrice.shell_session._stop_macbar", return_value=[]),
                  mock.patch("macrice.shell_session._activate_session_controls", return_value=[])):
                self.assertEqual(sync_theme(profile.theme), ())
                self.assertEqual([call.args for call in shell.call_args_list if call.args[1] is False], [(key, False)])


if __name__ == "__main__":
    unittest.main()
