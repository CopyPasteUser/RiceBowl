"""Native Aqua control contracts and the launcher Settings escape regression."""

import unittest
from pathlib import Path
from unittest import mock
from types import SimpleNamespace

from macrice.aero_shell import frutiger_select_page
from macrice import hardware_status as hw


class DummyButton:
    def __init__(self):
        self.active = False

    def get_active(self):
        return self.active

    def set_active(self, active):
        self.active = active


class DummyStack:
    def __init__(self):
        self.visible = None

    def set_visible_child_name(self, page):
        self.visible = page


class DummySection:
    def __init__(self):
        self.visible = None

    def set_visible(self, visible):
        self.visible = visible


class DummySearch:
    def __init__(self):
        self.focused = False

    def grab_focus(self):
        self.focused = True


class LauncherRegressionTests(unittest.TestCase):
    def test_settings_is_not_a_navigation_dead_end(self):
        stack = DummyStack()
        buttons = {name: DummyButton() for name in ("Apps", "Places", "Settings")}
        section, search = DummySection(), DummySearch()
        for chosen in ("Settings", "Places", "Settings", "Apps", "Settings", "Apps"):
            frutiger_select_page(stack, buttons, section, search, chosen)
            self.assertEqual(stack.visible, chosen)
            self.assertEqual([name for name, button in buttons.items() if button.active],
                             [chosen])
            self.assertEqual(section.visible, chosen == "Apps")
        self.assertTrue(search.focused)

    def test_page_selection_rejects_unknown_tabs(self):
        with self.assertRaises(ValueError):
            frutiger_select_page(DummyStack(), {"Apps": DummyButton()},
                                 DummySection(), DummySearch(), "Settings")

    def test_settings_scroll_is_independent_of_longest_page(self):
        source = (Path(__file__).resolve().parents[1] / "macrice/aero_shell.py").read_text()
        launcher = source.split("def _create_frutiger_menu(self):", 1)[1].split(
            "def _create_ten_menu(self):", 1)[0]
        self.assertIn("self.aqua_stack.set_vhomogeneous(False)", launcher)
        self.assertIn('label="‹ All apps"', launcher)
        self.assertIn('switch_to("Apps")', launcher)


class NativeDeviceTests(unittest.TestCase):
    def test_native_pages_offer_real_controls(self):
        from macrice.frutiger_native_controls import NATIVE_TASKS

        self.assertIn(("connections", "Network connections"), NATIVE_TASKS)
        self.assertIn(("connections", "Bluetooth devices"), NATIVE_TASKS)
        self.assertIn(("sound", "Output volume & mute"), NATIVE_TASKS)
        self.assertIn(("sound", "Input & output devices"), NATIVE_TASKS)
        self.assertIn(("display", "Display configuration"), NATIVE_TASKS)
        self.assertIn(("power", "Power management"), NATIVE_TASKS)
        self.assertIn(("power", "Battery status"), NATIVE_TASKS)

    def test_microphone_read_wpctl_and_mute(self):
        with mock.patch.object(hw.shutil, "which", side_effect=lambda name: "/bin/wpctl" if name == "wpctl" else None), \
             mock.patch.object(hw, "_run", return_value="Volume: 0.68 [MUTED]"):
            self.assertEqual(hw.read_microphone(), hw.SoundState(68, True))

    def test_microphone_write_is_verified(self):
        with mock.patch.object(hw.shutil, "which", return_value="/bin/wpctl"), \
             mock.patch.object(hw.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as command, \
             mock.patch.object(hw, "read_microphone", return_value=hw.SoundState(42, False)):
            self.assertEqual(hw.set_microphone_volume(42).percent, 42)
            self.assertEqual(command.call_args.args[0][:3],
                             ["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@"])

    def test_microphone_mute_rejects_unverified_backend(self):
        with mock.patch.object(hw.shutil, "which", return_value="/bin/wpctl"), \
             mock.patch.object(hw.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
             mock.patch.object(hw, "read_microphone", return_value=hw.SoundState(55, False)):
            with self.assertRaises(RuntimeError):
                hw.set_microphone_mute(True)

    def test_native_write_displays_verified_readback_not_optimistic_value(self):
        from macrice.frutiger_native_controls import NativeAquaControls

        panel = NativeAquaControls.__new__(NativeAquaControls)
        panel._generation, panel._busy, panel._syncing = 0, False, False
        panel.is_current = lambda: True
        panel._interactive = []
        actual, shown, status = [24], [], []
        panel._reader = lambda: actual[0]
        panel._renderer = shown.append
        panel._status = lambda message, **_kwargs: status.append(message)
        panel.GLib = SimpleNamespace(idle_add=lambda callback: callback())

        class ImmediateThread:
            def __init__(self, target, **_kwargs):
                self.target = target

            def start(self):
                self.target()

        with mock.patch("macrice.frutiger_native_controls.threading.Thread", ImmediateThread):
            panel.change(lambda: actual.__setitem__(0, 51))
        self.assertEqual(shown, [51])
        self.assertEqual(status[-1], "Applied and verified")

    def test_native_write_error_restores_readback_and_reports_failure(self):
        from macrice.frutiger_native_controls import NativeAquaControls

        panel = NativeAquaControls.__new__(NativeAquaControls)
        panel._generation, panel._busy, panel._syncing = 0, False, False
        panel.is_current = lambda: True
        panel._interactive = []
        shown, status = [], []
        panel._reader = lambda: 42
        panel._renderer = shown.append
        panel._status = lambda message, **kwargs: status.append((message, kwargs))
        panel.GLib = SimpleNamespace(idle_add=lambda callback: callback())

        class ImmediateThread:
            def __init__(self, target, **_kwargs):
                self.target = target

            def start(self):
                self.target()

        def fails():
            raise RuntimeError("Device rejected the change")

        with mock.patch("macrice.frutiger_native_controls.threading.Thread", ImmediateThread):
            panel.change(fails)
        self.assertEqual(shown, [42])
        self.assertEqual(status[-1], ("Device rejected the change", {"error": True}))


if __name__ == "__main__":
    unittest.main()
