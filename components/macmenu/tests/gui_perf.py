"""Measure the end-to-end process cost of warm GTK launcher activations."""

import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from gi.repository import GLib

from macmenu.config import sanitize
from macmenu.model import AppEntry
from macmenu.ui import MacMenu


APP_ID = "io.github.xfce.MacMenuPerfSmoke"


def invoke(command: list[str]) -> float:
    started = time.perf_counter()
    env = {**os.environ, "MACMENU_TEST_APP_ID": APP_ID}
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    deadline = time.monotonic() + 4
    while child.poll() is None and time.monotonic() < deadline:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        time.sleep(0.002)
    if child.poll() is None:
        child.kill()
        raise AssertionError(f"Timeout invoking {command[0]}")
    output, error = child.communicate()
    assert child.returncode == 0, f"Command {command[0]} failed: {output!r}, {error!r}"
    while GLib.MainContext.default().pending():
        GLib.MainContext.default().iteration(False)
    return (time.perf_counter() - started) * 1000


def main() -> int:
    entry = AppEntry("test.desktop", "Test App", "", "Utilities")
    with patch("macmenu.ui.installed_apps", return_value=[entry]), patch(
        "macmenu.ui.load", return_value=sanitize({})
    ):
        app = MacMenu()
        app.set_application_id(APP_ID)
        assert app.register(), "Could not register performance probe"
        try:
            app.perform("show")
            original = app.window
            assert original and original.get_visible()
            commands = {
                "python-gio": [sys.executable, str(Path(__file__).with_name("gui_toggle_client.py"))],
            }
            if shutil.which("gapplication"):
                commands["gapplication"] = ["gapplication", "launch", APP_ID]
            if shutil.which("gdbus"):
                commands["gdbus"] = [
                    "gdbus", "call", "--session", "--dest", APP_ID,
                    "--object-path", "/" + APP_ID.replace(".", "/"),
                    "--method", "org.gtk.Application.Activate", "{}",
                ]
            for name, command in commands.items():
                samples = []
                for _ in range(7):
                    was_visible = original.get_visible()
                    samples.append(invoke(command))
                    assert app.window is original, "Warm activation must reuse the GTK window"
                    assert original.get_visible() != was_visible, f"{name} did not actually toggle"
                print(f"{name}: median={statistics.median(samples):.1f} ms; samples={[round(s) for s in samples]}")
        finally:
            app.perform("quit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
