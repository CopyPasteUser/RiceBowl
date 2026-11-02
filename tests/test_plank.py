"""Plank integration is read-only except for explicitly starting its process."""

import subprocess
import unittest
from unittest import mock

from macrice import plank
from macrice.cli import COMMANDS, open_component, parser
from macrice.environment import detect, installed_components


class PlankTests(unittest.TestCase):
    @mock.patch("macrice.plank._query")
    @mock.patch("macrice.plank.installed", return_value=True)
    def test_dock_settings_use_relocatable_schema(self, _installed, query):
        query.side_effect = ["WhiteSur", "bottom", "48", "intelligent", "center"]
        settings = plank.preferences()
        self.assertEqual(settings.theme, "WhiteSur")
        self.assertEqual(settings.position, "bottom")
        self.assertEqual(settings.icon_size, "48")
        self.assertEqual(settings.hide_mode, "intelligent")
        self.assertEqual(query.call_count, 5)
        for call in query.call_args_list:
            self.assertEqual(call.args[0:3], ("gsettings", "get", plank.DOCK_SCHEMA))

    @mock.patch("macrice.plank._query")
    @mock.patch("macrice.plank.installed", return_value=False)
    def test_absent_dock_skips_gsettings(self, _installed, query):
        self.assertIsNone(plank.preferences().theme)
        query.assert_not_called()

    @mock.patch("macrice.plank.running", return_value=True)
    @mock.patch("macrice.plank.shutil.which", return_value="/usr/bin/plank")
    @mock.patch("macrice.plank.subprocess.Popen")
    def test_open_dock_does_not_duplicate_running_process(self, popen, _which, _running):
        self.assertIn("already running", plank.open_dock())
        popen.assert_not_called()

    @mock.patch("macrice.plank.shutil.which", return_value="/usr/bin/plank")
    @mock.patch("macrice.plank.subprocess.Popen")
    def test_preferences_use_native_plank_window(self, popen, _which):
        plank.open_dock(show_preferences=True)
        self.assertEqual(popen.call_args.args[0], ["/usr/bin/plank", "--preferences"])
        self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)

    @mock.patch("macrice.plank.running", return_value=False)
    @mock.patch("macrice.plank.shutil.which", return_value="/usr/bin/plank")
    @mock.patch("macrice.plank.subprocess.Popen")
    def test_start_only_without_arguments(self, popen, _which, _running):
        open_component("dock")
        self.assertEqual(popen.call_args.args[0], ["/usr/bin/plank"])

    @mock.patch("macrice.plank.shutil.which", return_value=None)
    def test_missing_plank_shows_install_hint(self, _which):
        with self.assertRaisesRegex(RuntimeError, "sudo apt install plank"):
            plank.open_dock(show_preferences=True)

    @mock.patch("macrice.plank.subprocess.run")
    @mock.patch("macrice.plank.shutil.which", side_effect=["/usr/bin/plank", "/usr/bin/pgrep"])
    def test_running_check_is_scoped_to_current_user(self, _which, run):
        run.return_value.returncode = 0
        self.assertTrue(plank.running())
        self.assertIn("-u", run.call_args.args[0])

    @mock.patch("macrice.plank.installed", return_value=True)
    def test_suite_reports_plank_and_exposes_commands(self, _installed):
        self.assertIn("Plank", installed_components())
        self.assertTrue(installed_components()["Plank"])
        self.assertEqual(COMMANDS["dock"], ("plank",))
        self.assertEqual(parser().parse_args(["dock", "preferences"]).action, "preferences")

    @mock.patch("macrice.plank.preferences")
    @mock.patch("macrice.environment._xfconf", return_value="WhiteSur-Dark")
    def test_xfce_profile_includes_plank_details(self, _xfconf, prefs):
        prefs.return_value = plank.DockPreferences("WhiteSur", "bottom", "48", "intelligent")
        report = detect().as_dict()
        self.assertEqual(report["gtk_theme"], "WhiteSur-Dark")
        self.assertEqual(report["plank_position"], "bottom")
        self.assertEqual(report["plank_icon_size"], "48")
        self.assertEqual(report["plank_hide_mode"], "intelligent")


if __name__ == "__main__":
    unittest.main()
