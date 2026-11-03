"""Preserve installed Thunar CSS while repairing unreadable native menus."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from macrice.thunar import _block, _pre_spacing_block, plan_css


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


if __name__ == "__main__":
    unittest.main()
