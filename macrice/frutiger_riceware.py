"""Aqua World renderer bridge for the shared, verified Riceware backend."""

from __future__ import annotations

from .riceware import spice
from .riceware.native_hardware import RicewareHardware
from .riceware.worker import LatestRequestRunner


class FrutigerController:
    def __init__(self, GLib, *, runner=None):
        self.runner = runner if runner is not None else LatestRequestRunner(GLib.idle_add)
        self.hardware = RicewareHardware()
        self.closed = False

    def submit(self, key, operation, callback):
        if self.closed:
            return

        def delivered(response):
            if not self.closed:
                callback(response)

        self.runner.submit("frutiger-" + key, operation, delivered)

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
