"""Standalone native GApplication test: one hotkey command toggles open/close/open."""

from unittest.mock import patch

from macmenu.config import sanitize
from macmenu.model import AppEntry
from macmenu.ui import MacMenu


def main() -> int:
    entry = AppEntry("test.desktop", "Test App", "", "Utilities")
    with patch("macmenu.ui.installed_apps", return_value=[entry]), patch(
        "macmenu.ui.load", return_value=sanitize({})
    ):
        app = MacMenu()
        app.set_application_id("io.github.xfce.MacMenuToggleSmoke")
        assert app.register(), "Could not register GApplication for toggle test"
        try:
            app.perform("toggle")
            original = app.window
            assert original and original.get_visible(), "Invocation 1 must open the launcher"
            app.perform("toggle")
            assert not original.get_visible(), "Invocation 2 must hide the launcher"
            app.perform("toggle")
            assert app.window is original and original.get_visible(), "Invocation 3 must reopen the same launcher"
            print("Toggle smoke: first opens, second closes, third reopens without restarting")
        finally:
            app.perform("quit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
