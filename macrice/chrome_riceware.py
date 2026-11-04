"""ChromeOS renderer bridge to Riceware's verified Linux device backends.

ChromeOS owns its Material You presentation, not its own hardware threads.
The adapter deliberately exposes the old controls' narrow read/write contract
so native GTK pages can migrate without changing unrelated rices.
"""

from __future__ import annotations

from .hardware_status import BluetoothState, SoundState
from .riceware import spice
from .riceware.worker import LatestRequestRunner


READS = {
    "read_wifi_radio": ("wifi", None),
    "read_wifi_networks": ("wifi_networks", ()),
    "read_bluetooth": ("bluetooth", BluetoothState(None, ())),
    "read_sound": ("audio", SoundState(None, None)),
    "read_sound_outputs": ("audio_outputs", ()),
    "read_microphone": ("microphone", SoundState(None, None)),
    "read_brightness": ("brightness", None),
    "read_battery": ("battery", None),
    "read_power_profiles": ("power_profiles", (None, ())),
}

WRITES = {
    "set_wifi_radio": "wifi",
    "connect_wifi": "wifi_connect",
    "disconnect_wifi": "wifi_disconnect",
    "set_bluetooth_power": "bluetooth_power",
    "set_sound_volume": "audio_volume",
    "set_sound_mute": "audio_mute",
    "set_sound_output": "audio_output",
    "set_microphone_volume": "microphone_volume",
    "set_microphone_mute": "microphone_mute",
    "set_brightness": "brightness",
    "set_power_profile": "power_profile",
}


class ChromeHardware:
    """Narrow facade: never signal mutation success without spice readback."""

    def _read(self, method):
        name, fallback = READS[method]
        result = spice.read(name)
        if result.status == "error":
            raise RuntimeError(result.reason or f"{name} read failed")
        return result.value if result.value is not None else fallback

    def _write(self, method, *args):
        result = spice.change(WRITES[method], *args)
        if result.status != "ok":
            raise RuntimeError(result.reason or f"{method} could not be verified")
        return result.value

    def __getattr__(self, name):
        if name in READS:
            return lambda: self._read(name)
        if name in WRITES:
            return lambda *args: self._write(name, *args)
        raise AttributeError(name)

    def set_bluetooth_connection(self, address, connected):
        if type(connected) is not bool:
            raise ValueError("Bluetooth connection must be a boolean")
        result = spice.change("bluetooth_connect" if connected else "bluetooth_disconnect",
                              address)
        if result.status != "ok":
            raise RuntimeError(result.reason or "Bluetooth connection was not verified")
        return result.value


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
