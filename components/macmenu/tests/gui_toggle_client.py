"""Issue a real --toggle IPC command to the isolated GApplication smoke server."""

import os

from macmenu.ui import MacMenu


if __name__ == "__main__":
    app = MacMenu()
    app.set_application_id(os.environ.get("MACMENU_TEST_APP_ID", "io.github.xfce.MacMenuToggleIPCSmoke"))
    raise SystemExit(app.run(["macmenu", "--toggle"]))
