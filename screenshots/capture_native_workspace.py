#!/usr/bin/env python3
"""Capture a genuine XFWM4 + Thunar window for a non-macOS RiceBowl rice.

Run only inside a disposable Xvfb / dbus-run-session environment. This script
uses its own temporary HOME, XDG directories and XFCE settings, never touching
the developer's normal desktop or previewing composited mockups.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from macrice.rice import STYLES  # noqa: E402
from macrice.thunar import _block, preference_type, preferences_for  # noqa: E402


SAMPLES = {
    "aero": ("aero-cascade", "aero"),
    "windows10": ("ten-light", "ten-light"),
    "winxp": ("winxp", "winxp"),
    "winclassic": ("winclassic", "winclassic"),
    "chromeos": ("chromeos", "chromeos"),
    "frutiger": ("frutiger", "frutiger"),
}


def prepare_isolated_desktop(base: Path, profile: str) -> Path:
    style_key, palette = SAMPLES[profile]
    style = STYLES[style_key]
    os.environ.update({
        "HOME": str(base),
        "XDG_CONFIG_HOME": str(base / "config"),
        "XDG_DATA_HOME": str(base / "data"),
        "XDG_CACHE_HOME": str(base / "cache"),
        "RICEHUB_WNCK_INTEGRATION": "1",
    })
    (base / ".themes").symlink_to(REPO / "assets/themes", target_is_directory=True)
    (base / ".icons").symlink_to(REPO / "assets/icons", target_is_directory=True)
    gtk_config = base / "config/gtk-3.0"
    gtk_config.mkdir(parents=True)
    (gtk_config / "settings.ini").write_text(
        "[Settings]\n"
        f"gtk-theme-name={style.gtk}\n"
        f"gtk-icon-theme-name={style.icon_theme}\n"
        f"gtk-font-name={style.font}\n", encoding="utf-8")
    (gtk_config / "gtk.css").write_text(_block(palette), encoding="utf-8")

    fixture = base / "RiceBowl-Preview"
    fixture.mkdir()
    for folder in ("Documents", "Downloads", "Music", "Pictures", "Projects"):
        (fixture / folder).mkdir()
    (fixture / "README.txt").write_text(
        "RiceBowl virtual-X11 acceptance fixture.\n"
        "This is an actual Thunar window with the profile's GTK and XFWM4 theme.\n",
        encoding="utf-8")
    os.environ["RICEBOWL_CAPTURE_FIXTURE_DIR"] = str(fixture)
    subprocess.run(
        ["xfconf-query", "-c", "xfwm4", "-p", "/general/theme",
         "--create", "-t", "string", "-s", style.xfwm],
        check=True, timeout=8, capture_output=True)
    # Match the actual Rice apply transaction. xfwm4's distro default may
    # include a Shade button that Windows XP/7 never had; showing it in a
    # screenshot would falsely suggest that the applied Rice uses that layout.
    subprocess.run(
        ["xfconf-query", "-c", "xfwm4", "-p", "/general/button_layout",
         "--create", "-t", "string", "-s", style.button_layout],
        check=True, timeout=8, capture_output=True)
    # The applied Rice also owns these precise Thunar preferences; a native
    # acceptance screenshot must exercise the same breadcrumb/icon-view layout.
    for property_name, value in preferences_for(palette):
        subprocess.run(
            ["xfconf-query", "-c", "thunar", "-p", property_name,
             "--create", "-t", preference_type(property_name), "-s", value],
            check=True, timeout=8, capture_output=True)
    return fixture


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SAMPLES:
        raise SystemExit("Usage: capture_native_workspace.py <aero|windows10|winxp|winclassic|chromeos|frutiger>")
    profile = sys.argv[1]
    if "DISPLAY" not in os.environ:
        raise SystemExit("Requires an isolated virtual X11 display")
    with tempfile.TemporaryDirectory(prefix="ricebowl-native-capture-") as directory:
        prepare_isolated_desktop(Path(directory), profile)
        wm = subprocess.Popen(
            ["xfwm4", "--compositor=off", "--vblank=off"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            from macrice.aero_shell import run

            return run([f"ricebowl-{profile}-shell", "--capture-workspace"], profile=profile)
        finally:
            wm.terminate()
            try:
                wm.wait(timeout=5)
            except subprocess.TimeoutExpired:
                wm.kill()
                wm.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
