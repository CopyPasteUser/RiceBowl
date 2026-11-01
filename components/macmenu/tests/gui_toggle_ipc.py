"""Verify that three independent shortcut invocations toggle a resident launcher."""

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

from gi.repository import GLib

from macmenu.config import sanitize
from macmenu.model import AppEntry
from macmenu.ui import MacMenu


def invoke() -> None:
    path = Path(__file__).with_name("gui_toggle_client.py")
    child = subprocess.Popen([sys.executable, str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    until = time.monotonic() + 5
    while child.poll() is None and time.monotonic() < until:
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        time.sleep(0.004)
    if child.poll() is None:
        child.kill()
        raise AssertionError("Remote --toggle did not complete within five seconds")
    out, err = child.communicate()
    assert child.returncode == 0, f"Remote --toggle returned {child.returncode}: {out!r}, {err!r}"
    while GLib.MainContext.default().pending():
        GLib.MainContext.default().iteration(False)


def main() -> int:
    entry = AppEntry("test.desktop", "Test App", "", "Utilities")
    with patch("macmenu.ui.installed_apps", return_value=[entry]), patch(
        "macmenu.ui.load", return_value=sanitize({})
    ):
        app = MacMenu()
        app.set_application_id("io.github.xfce.MacMenuToggleIPCSmoke")
        assert app.register(), "Could not register the IPC smoke server"
        try:
            invoke()
            window = app.window
            assert window and window.get_visible(), "First process should open"
            invoke()
            assert not window.get_visible(), "Second process should close"
            invoke()
            assert app.window is window and window.get_visible(), "Third process should reopen same window"
            # XFCE's Super-only shortcut may momentarily move keyboard focus
            # before the remote command arrives. The focus-out callback must
            # not preempt the explicit toggle and turn it into a new show.
            with patch.object(window, "is_active", return_value=False):
                window.on_focus_out(None, None)
                invoke()
            assert not window.get_visible(), "Super shortcut must close even if focus-out precedes IPC"
            invoke()
            assert window.get_visible(), "Reopen after an explicit shortcut toggle"
            with patch.object(window, "is_active", return_value=False):
                window.on_focus_out(None, None)
                deadline = time.monotonic() + 0.8
                while window.get_visible() and time.monotonic() < deadline:
                    while GLib.MainContext.default().pending():
                        GLib.MainContext.default().iteration(False)
                    time.sleep(0.005)
            assert not window.get_visible(), "Click-away without another command must still close"
            print("IPC toggle: open/close/open, Super focus-race and click-away all passed")
        finally:
            app.perform("quit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
