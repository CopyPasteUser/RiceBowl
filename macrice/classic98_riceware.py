"""Bounded riceSpice bridge for the Windows 98 shell and its small dialogs.

The renderer owns this object. No global worker, service or extra tray is
started, and all callbacks return to the GTK main loop.
"""

from __future__ import annotations

from .riceware import spice
from .riceware.worker import LatestRequestRunner


class Classic98Controller:
    def __init__(self, GLib, *, runner=None):
        self.runner = runner or LatestRequestRunner(GLib.idle_add, workers=3)
        self.closed = False

    def submit(self, key, operation, complete):
        if self.closed:
            return

        def delivered(response):
            if self.closed:
                return
            result = (spice.Result(key, "error", reason=response.error)
                      if response.error else response.value)
            complete(result)

        self.runner.submit("classic98-" + key, operation, delivered)

    def refresh_status(self, complete):
        self.submit("desktop-status", lambda: spice.read("desktop_status"),
                    lambda result: complete(result.value if result.status == "ok" else None))

    def change_audio(self, action, value, complete):
        self.submit(action, lambda: spice.change(action, value),
                    lambda result: complete(result.value if result.status == "ok" else None,
                                            None if result.status == "ok" else
                                            result.reason or "Audio backend unavailable"))

    def close(self):
        if not self.closed:
            self.closed = True
            self.runner.close()
