"""Real-window gallery setup must be isolated, mapped and reproducible."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from screenshots.capture_native_workspace import REPO, SAMPLES, prepare_isolated_desktop
from macrice.rice import STYLES


class NativeWorkspaceGalleryTests(unittest.TestCase):
    def test_all_six_profiles_use_their_real_gtk_xfwm_and_icon_themes(self):
        for profile, (style_name, _palette) in SAMPLES.items():
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                with patch.dict(os.environ), patch("subprocess.run") as call:
                    base = Path(directory)
                    fixture = prepare_isolated_desktop(base, profile)
                    style = STYLES[style_name]
                    settings = (base / "config/gtk-3.0/settings.ini").read_text()
                    self.assertIn("gtk-theme-name=" + style.gtk, settings)
                    self.assertIn("gtk-icon-theme-name=" + style.icon_theme, settings)
                    self.assertIn("window.thunar", (base / "config/gtk-3.0/gtk.css").read_text())
                    self.assertEqual((base / ".themes").resolve(), REPO / "assets/themes")
                    self.assertEqual((base / ".icons").resolve(), REPO / "assets/icons")
                    self.assertTrue((fixture / "Documents").is_dir())
                    self.assertTrue((fixture / "README.txt").is_file())
                    self.assertEqual(os.environ["RICEBOWL_CAPTURE_FIXTURE_DIR"], str(fixture))
                    self.assertEqual(call.call_args.args[0][-1], style.xfwm)

    def test_real_thunar_and_xfwm_are_required_for_workspace_capture(self):
        source = (REPO / "macrice/aero_shell.py").read_text(encoding="utf-8")
        for needle in ("--capture-workspace", '"thunar", fixture',
                       '"xdotool", "search", "--onlyvisible", "--name", "RiceBowl-Preview"',
                       '"thunar" in (window.get_class_group().get_id() or "").casefold()',
                       "self._capture_screen(f\"ricebowl-{profile}-workspace-0.9.1.png\")"):
            self.assertIn(needle, source)


if __name__ == "__main__":
    unittest.main()
