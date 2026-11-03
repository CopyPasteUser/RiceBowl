"""Preserve installed Thunar CSS while repairing unreadable native menus."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from macrice.thunar import (_block, _pre_spacing_block, _v091_block,
                           preference_type, preferences_for, plan_css)


class ThunarMenubarTests(unittest.TestCase):
    def test_menu_spacing_is_scoped_to_the_four_affected_identities(self):
        fix = "window.thunar menubar > menuitem { padding: 3px 10px; }"
        for profile in ("aero", "winxp", "chromeos", "frutiger"):
            self.assertIn(fix, _block(profile))
            self.assertNotIn(fix, _pre_spacing_block(profile))
        for profile in ("winclassic", "ten-dark", "ten-light", "night", "day"):
            self.assertNotIn(fix, _block(profile))

    def test_upgrading_exact_prior_css_preserves_unowned_rules(self):
        for profile in ("aero", "winxp", "chromeos", "frutiger"):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                config = Path(directory)
                css_path = config / "gtk-3.0/gtk.css"
                css_path.parent.mkdir()
                prefix, suffix = "/* user's first rule */\n", "/* user's last rule */\n"
                original = prefix + _pre_spacing_block(profile) + suffix
                css_path.write_text(original)
                planned = plan_css(profile, config)
                self.assertEqual(planned["before"], original)
                self.assertEqual(planned["after"], prefix + _block(profile) + suffix)

    def test_genuinely_edited_managed_css_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            css_path = config / "gtk-3.0/gtk.css"
            css_path.parent.mkdir()
            css_path.write_text(_pre_spacing_block("winxp").replace("#fff8e8", "#123456"))
            with self.assertRaisesRegex(ValueError, "customized"):
                plan_css("winxp", config)

    def test_aero_explorer_migrates_existing_managed_css_without_touching_user_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            css_path = config / "gtk-3.0/gtk.css"
            css_path.parent.mkdir()
            original = "/* personal GTK overrides */\n" + _v091_block("aero") + "/* custom footer */\n"
            css_path.write_text(original)
            changes = plan_css("aero", config)
            self.assertEqual(changes["before"], original)
            self.assertEqual(changes["after"], "/* personal GTK overrides */\n" +
                             _block("aero") + "/* custom footer */\n")
            self.assertEqual(plan_css("aero", config), changes)  # read-only
            css_path.write_text(changes["after"])
            self.assertEqual(plan_css("aero", config)["after"], changes["after"])
            css_path.write_text(changes["after"].replace("#e9f2fa", "#e9f2fb"))
            with self.assertRaisesRegex(ValueError, "customized"):
                plan_css("aero", config)

    def test_2009_explorer_scope_and_other_rices_are_not_restyled(self):
        css = _block("aero")
        for selector in ("window.thunar toolbar button:hover",
                         "window.thunar .path-bar", "window.thunar .sidebar",
                         "window.thunar .standard-view", "window.thunar statusbar"):
            self.assertIn(selector, css)
        self.assertNotIn("Seven Explorer", _block("winxp"))
        self.assertEqual(_block("winxp"), _v091_block("winxp"))
        self.assertEqual(_block("frutiger"), _v091_block("frutiger"))

    def test_menubar_behavior_is_profile_specific_and_has_real_boolean_type(self):
        self.assertEqual(dict(preferences_for("aero"))["/last-menubar-visible"], "false")
        self.assertEqual(dict(preferences_for("winxp"))["/last-menubar-visible"], "true")
        self.assertEqual(dict(preferences_for("night"))["/last-menubar-visible"], "true")
        self.assertEqual(preference_type("/last-menubar-visible"), "bool")
        self.assertEqual(preference_type("/last-location-bar"), "string")


if __name__ == "__main__":
    unittest.main()
