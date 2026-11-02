"""RiceHub key routing and reversible XFCE shortcut ownership."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice import session_shortcuts as shortcuts
from macrice.cli import main


class ShortcutTests(unittest.TestCase):
    def test_cli_key_commands_forward_to_active_component(self):
        with mock.patch.object(shortcuts, "dispatch") as dispatch:
            self.assertEqual(main(["session-menu"]), 0)
            self.assertEqual(main(["session-control"]), 0)
        self.assertEqual(dispatch.call_args_list, [mock.call("menu"), mock.call("control")])

    def test_cli_can_toggle_windows_taskbar_or_action_center(self):
        with mock.patch("macrice.aero_shell.run", return_value=0) as aero:
            self.assertEqual(main(["aero-shell", "--toggle-menu"]), 0)
        aero.assert_called_once_with(["ricehub-aero-shell", "--toggle-menu"])
        with mock.patch("macrice.aero_shell.run", return_value=0) as aero:
            self.assertEqual(main(["aero-shell", "--control"]), 0)
        aero.assert_called_once_with(["ricehub-aero-shell", "--control"])
        with mock.patch("macrice.ten_shell.run", return_value=0) as ten:
            self.assertEqual(main(["windows10-shell", "--actions"]), 0)
        ten.assert_called_once_with(["ricehub-ten-shell", "--actions"])

    def test_menu_and_control_follow_active_rice(self):
        self.assertEqual(shortcuts.command_for("menu", "WhiteSur-Dark"), ("macmenu", "--toggle"))
        self.assertEqual(shortcuts.command_for("control", "WhiteSur-Light"),
                         ("macos-control-center-toggle",))
        self.assertEqual(shortcuts.command_for("menu", "RiceHub-Aero"),
                         ("macrice", "aero-shell", "--toggle-menu"))
        self.assertEqual(shortcuts.command_for("control", "RiceHub-Aero"),
                         ("macrice", "aero-shell", "--control"))
        self.assertEqual(shortcuts.command_for("menu", "RiceHub-Ten-Dark"),
                         ("macrice", "windows10-shell", "--toggle-menu"))
        self.assertEqual(shortcuts.command_for("control", "RiceHub-Ten-Light"),
                         ("macrice", "windows10-shell", "--actions"))

    def test_bindings_backup_and_restore_original_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            current = {"Super_L": "xfce4-popup-whiskermenu", "Control_R": None}
            with mock.patch.object(shortcuts, "_read", side_effect=lambda key: current[key]), \
                 mock.patch.object(shortcuts, "_write", side_effect=lambda key, value: current.__setitem__(key, value)):
                shortcuts.install_bindings("RiceHub-Aero", state_dir=state, launcher=Path("/usr/local/bin/macrice"))
                self.assertEqual(current["Super_L"], "/usr/local/bin/ricehub-toggle aero-menu")
                self.assertEqual(current["Control_R"], "/usr/local/bin/ricehub-toggle aero-control")
                shortcuts.install_bindings("WhiteSur-Dark", state_dir=state, launcher=Path("/usr/local/bin/macrice"))
                self.assertEqual(current["Super_L"], "/usr/local/bin/macmenu --toggle")
                self.assertEqual(current["Control_R"], "/usr/local/bin/macos-control-center-toggle")
                shortcuts.install_bindings("RiceHub-Ten-Light", state_dir=state,
                                           launcher=Path("/home/testuser/.local/bin/macrice"))
                self.assertIn("/home/testuser/.local/bin/ricehub-toggle ten-menu", current["Super_L"])
                shortcuts.restore_bindings(state_dir=state)
            self.assertEqual(current, {"Super_L": "xfce4-popup-whiskermenu", "Control_R": None})

    def test_user_edited_binding_is_never_overwritten_or_restored(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp)
            current = {"Super_L": None, "Control_R": None}
            with mock.patch.object(shortcuts, "_read", side_effect=lambda key: current[key]), \
                 mock.patch.object(shortcuts, "_write", side_effect=lambda key, value: current.__setitem__(key, value)):
                shortcuts.install_bindings("WhiteSur-Light", state_dir=state, launcher=Path("/usr/local/bin/macrice"))
                current["Super_L"] = "user-custom-shortcut"
                warnings = shortcuts.install_bindings("RiceHub-Aero", state_dir=state,
                                                      launcher=Path("/usr/local/bin/macrice"))
                self.assertTrue(warnings)
                shortcuts.restore_bindings(state_dir=state)
            self.assertEqual(current["Super_L"], "user-custom-shortcut")
            self.assertIsNone(current["Control_R"])

    def test_legacy_dynamic_bindings_upgrade_without_losing_originals(self):
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary)
            original = {"Super_L": "xfce4-popup-whiskermenu", "Control_R": None}
            legacy = {key: f"/home/simon/.local/bin/macrice {name}"
                      for key, name in shortcuts.KEY_COMMANDS.items()}
            shortcuts._save(state / shortcuts.STATE_FILE,
                            {"version": 1, "original": original, "managed": legacy})
            current = dict(legacy)
            with mock.patch.object(shortcuts, "_read", side_effect=lambda key: current[key]), \
                 mock.patch.object(shortcuts, "_write", side_effect=lambda key, value: current.__setitem__(key, value)):
                shortcuts.install_bindings("RiceHub-Aero", state_dir=state,
                                           launcher=Path("/home/simon/.local/bin/macrice"))
                self.assertEqual(current["Super_L"], "/home/simon/.local/bin/ricehub-toggle aero-menu")
                shortcuts.restore_bindings(state_dir=state)
            self.assertEqual(current, original)


if __name__ == "__main__":
    unittest.main()
