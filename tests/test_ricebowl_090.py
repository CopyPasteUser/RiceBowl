"""RiceBowl 0.9: hardware controls, native rice identities and safe CSS upgrades."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from macrice.hardware_status import (
    SoundState, set_sound_mute, set_sound_volume,
)
from macrice.installer import project_root
from macrice.thunar import _block, _legacy_block, _v080_block, plan_css
from macrice.heritage_shell import CSS


class ThunarIdentityTests(unittest.TestCase):
    def test_macos_thunar_css_is_unchanged(self):
        for name in ("night", "day"):
            with self.subTest(style=name):
                self.assertEqual(_block(name), _v080_block(name))

    def test_exact_08_thunar_css_upgrades_without_touching_user_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "gtk-3.0/gtk.css"
            path.parent.mkdir(parents=True)
            custom = "/* personal CSS */\nlabel { font-weight: bold; }\n"
            path.write_text(custom + _v080_block("winxp"), encoding="utf-8")
            planned = plan_css("frutiger", root)
            self.assertEqual(planned["before"], path.read_text())
            self.assertEqual(planned["after"], custom + _block("frutiger"))
            self.assertNotIn("window.thunar .path-bar button:active", planned["after"])

    def test_unknown_owned_block_remains_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "gtk-3.0/gtk.css"
            path.parent.mkdir(parents=True)
            path.write_text(_v080_block("winxp").replace("#b8d5f6", "#123abc"))
            with self.assertRaisesRegex(ValueError, "customized"):
                plan_css("winxp", root)

    def test_four_real_thunar_identities(self):
        expected = {
            "winxp": ("warm command bar", "#2767cb"),
            "winclassic": ("Win98/2000", "#000080"),
            "chromeos": ("lavender sidebar", "#e7ecfc"),
            "frutiger": ("green selection", "#a1ed43"),
        }
        for name, (descriptor, color) in expected.items():
            with self.subTest(style=name):
                self.assertIn(color, _block(name))
                self.assertIn("window.thunar toolbar", _block(name))
                self.assertIn("window.thunar statusbar", _block(name))
                self.assertIn("window.thunar", _block(name))

    def test_bundled_native_gtk_themes_cover_window_and_sidebar(self):
        for name in ("Luna", "Classic", "Chrome", "Frutiger"):
            css = (project_root() / f"assets/themes/RiceHub-{name}/gtk-3.0/gtk.css").read_text()
            self.assertIn("window.thunar menubar", css)
            self.assertIn("window.thunar .sidebar", css)
            self.assertIn("window.thunar statusbar", css)

    def test_dedicated_menu_styles_not_just_aero_palette(self):
        selectors = {
            "winxp": (b".luna-user", b".luna-places", b".luna-footer"),
            "winclassic": (b".classic-menu-item", b".classic-brand"),
            "chromeos": (b".chrome-app-shelf", b".chrome-status-pill"),
            "frutiger": (b".aqua-tab:checked", b".aqua-place", b".aqua-footer"),
        }
        for style, tokens in selectors.items():
            for token in tokens:
                with self.subTest(style=style, selector=token):
                    self.assertIn(token, CSS[style])


class HardwareControlTests(unittest.TestCase):
    def test_volume_rejects_out_of_bounds_before_running(self):
        for bad in (-1, 101, 1.5, True, "40"):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    set_sound_volume(bad)

    def test_verified_pipewire_volume_set(self):
        with mock.patch("macrice.hardware_status.shutil.which", return_value="/usr/bin/wpctl"), \
             mock.patch("macrice.hardware_status.subprocess.run",
                        return_value=SimpleNamespace(returncode=0)) as run, \
             mock.patch("macrice.hardware_status.read_sound",
                        return_value=SoundState(65, False)):
            self.assertEqual(set_sound_volume(65), SoundState(65, False))
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0],
                             ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.65"])
            self.assertEqual(run.call_args.kwargs["timeout"], 2.0)

    def test_verified_pactl_fallback(self):
        with mock.patch("macrice.hardware_status.shutil.which",
                        side_effect=lambda x: x == "pactl"), \
             mock.patch("macrice.hardware_status.subprocess.run",
                        return_value=SimpleNamespace(returncode=0)) as run, \
             mock.patch("macrice.hardware_status.read_sound",
                        return_value=SoundState(40, False)):
            self.assertEqual(set_sound_volume(40).percent, 40)
            self.assertEqual(run.call_args.args[0][-1], "40%")

    def test_backend_mismatch_fails_instead_of_faking_success(self):
        with mock.patch("macrice.hardware_status.shutil.which",
                        side_effect=lambda x: x == "wpctl"), \
             mock.patch("macrice.hardware_status.subprocess.run",
                        return_value=SimpleNamespace(returncode=0)), \
             mock.patch("macrice.hardware_status.read_sound",
                        return_value=SoundState(20, False)):
            with self.assertRaisesRegex(RuntimeError, "read-back mismatch"):
                set_sound_volume(80)

    def test_mute_and_unmute_are_verified(self):
        for requested in (True, False):
            with self.subTest(muted=requested), \
                 mock.patch("macrice.hardware_status.shutil.which",
                            side_effect=lambda x: x == "wpctl"), \
                 mock.patch("macrice.hardware_status.subprocess.run",
                            return_value=SimpleNamespace(returncode=0)) as run, \
                 mock.patch("macrice.hardware_status.read_sound",
                            return_value=SoundState(60, requested)):
                self.assertEqual(set_sound_mute(requested).muted, requested)
                self.assertEqual(run.call_args.args[0][-1],
                                 "1" if requested else "0")

    def test_mute_rejects_unavailable_or_unverified_backend(self):
        with self.assertRaises(ValueError):
            set_sound_mute("yes")
        with mock.patch("macrice.hardware_status.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "no backend"):
                set_sound_mute(True)


if __name__ == "__main__":
    unittest.main()
