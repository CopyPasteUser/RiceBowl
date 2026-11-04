"""Small verified device API shared by native GTK rice controls.

Capability names are allowlisted: device operations go through riceSpice,
which reads back mutations rather than trusting successful subprocess exits.
"""

from __future__ import annotations

from ..hardware_status import BluetoothState, SoundState
from . import media, spice


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
    "connect_wifi_secured": "wifi_connect_secure",
    "disconnect_wifi": "wifi_disconnect",
    "set_bluetooth_power": "bluetooth_power",
    "pair_bluetooth_device": "bluetooth_pair",
    "set_sound_volume": "audio_volume",
    "set_sound_mute": "audio_mute",
    "set_sound_output": "audio_output",
    "set_microphone_volume": "microphone_volume",
    "set_microphone_mute": "microphone_mute",
    "set_brightness": "brightness",
    "set_power_profile": "power_profile",
}


class RicewareHardware:
    """Device controls only report successful mutations with verified readback."""

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

    def connect_wifi_secured(self, ssid, password):
        return self._write("connect_wifi_secured", (ssid, password))

    def read_media_players(self):
        return media.read_media_players()

    def media_action(self, player, command):
        return media.media_action(player, command)
