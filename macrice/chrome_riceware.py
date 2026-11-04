"""ChromeOS renderer bridge to Riceware's verified Linux device backends.

ChromeOS owns its Material You presentation, not its own hardware threads.
The adapter deliberately exposes the old controls' narrow read/write contract
so native GTK pages can migrate without changing unrelated rices.
"""

from __future__ import annotations

from .riceware import spice
from .riceware.native_hardware import RicewareHardware, READS, WRITES
from .riceware.worker import LatestRequestRunner


class ChromeHardware(RicewareHardware):
    """Backward-compatible ChromeOS name for the shared verified facade."""


class ChromeController:
    """Single closeable worker for ChromeOS devices and notification history."""

    def __init__(self, GLib, *, runner=None):
        self.runner = runner if runner is not None else LatestRequestRunner(GLib.idle_add)
        self.hardware = ChromeHardware()
        self.closed = False

    def submit(self, key, operation, callback):
        if self.closed:
            return

        def delivered(response):
            if not self.closed:
                callback(response)

        self.runner.submit("chrome-" + key, operation, delivered)

    def refresh_status(self, callback):
        def completed(response):
            result = response.value
            callback(result.value if not response.error and result.status == "ok" else None)

        self.submit("desktop-status", lambda: spice.read("desktop_status"), completed)

    def change_audio(self, action, value, callback):
        def completed(response):
            result = response.value
            if response.error or result.status != "ok":
                callback(None, response.error or result.reason or "Audio unavailable")
            else:
                callback(result.value, None)

        self.submit(action, lambda: spice.change(action, value), completed)

    def close(self):
        if not self.closed:
            self.closed = True
            self.runner.close()
