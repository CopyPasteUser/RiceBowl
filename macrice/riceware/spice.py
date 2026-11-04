"""riceSpice: UI-independent access to RiceBowl's existing Linux controls.

No device is changed by reading a snapshot. Mutations use existing verified
backends; later rice-specific interfaces can consume the same results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .. import hardware_status as hardware


@dataclass(frozen=True)
class Result:
    name: str
    status: str  # ok, unavailable, error
    value: Any = None
    reason: str | None = None


READERS: dict[str, Callable[[], Any]] = {
    "audio": hardware.read_sound,
    "audio_outputs": hardware.read_sound_outputs,
    "battery": hardware.read_battery,
    "bluetooth": hardware.read_bluetooth,
    "brightness": hardware.read_brightness,
    "microphone": hardware.read_microphone,
    "network": hardware.read_network,
    "power_profiles": hardware.read_power_profiles,
    "wifi": hardware.read_wifi_radio,
    "wifi_networks": hardware.read_wifi_networks,
}

# The first item is the mutating backend; the second is the readback to expose.
# These are deliberately explicit: a renderer cannot call arbitrary shell tools.
WRITERS: dict[str, tuple[Callable[..., Any], str]] = {
    "audio_volume": (hardware.set_sound_volume, "audio"),
    "audio_mute": (hardware.set_sound_mute, "audio"),
    "audio_output": (hardware.set_sound_output, "audio_outputs"),
    "bluetooth_power": (hardware.set_bluetooth_power, "bluetooth"),
    "bluetooth_connect": (lambda address: hardware.set_bluetooth_connection(address, True), "bluetooth"),
    "bluetooth_disconnect": (lambda address: hardware.set_bluetooth_connection(address, False), "bluetooth"),
    "brightness": (hardware.set_brightness, "brightness"),
    "microphone_volume": (hardware.set_microphone_volume, "microphone"),
    "microphone_mute": (hardware.set_microphone_mute, "microphone"),
    "power_profile": (hardware.set_power_profile, "power_profiles"),
    "wifi": (hardware.set_wifi_radio, "wifi"),
    "wifi_connect": (hardware.connect_wifi, "wifi_networks"),
    "wifi_disconnect": (hardware.disconnect_wifi, "wifi_networks"),
}


def _available(name: str, value: Any) -> bool:
    if value is None:
        return False
    if name in ("audio", "microphone"):
        return value.percent is not None
    if name == "bluetooth":
        return value.powered is not None
    if name == "power_profiles":
        return value[0] is not None or bool(value[1])
    if name == "audio_outputs":
        return bool(value)
    return True


def read(name: str) -> Result:
    if name not in READERS:
        raise ValueError(f"Unknown riceSpice capability: {name}")
    try:
        value = READERS[name]()
    except (OSError, RuntimeError, ValueError) as exc:
        return Result(name, "error", reason=str(exc))
    if not _available(name, value):
        return Result(name, "unavailable", reason="No supported device or backend")
    return Result(name, "ok", value=value)


def snapshot() -> tuple[Result, ...]:
    """A bounded on-demand read, never a permanent polling loop."""
    return tuple(read(name) for name in READERS)


def change(action: str, value: Any = None) -> Result:
    if action not in WRITERS:
        raise ValueError(f"Unknown riceSpice action: {action}")
    writer, capability = WRITERS[action]
    try:
        if action == "wifi_disconnect":
            if value is not None:
                raise ValueError("wifi_disconnect takes no value")
            outcome = writer()
        else:
            if value is None:
                raise ValueError(f"{action} requires a value")
            outcome = writer(value)
        if action in ("wifi_connect", "wifi_disconnect") and outcome is not True:
            raise RuntimeError("NetworkManager could not verify the requested connection state")
    except (OSError, RuntimeError, ValueError) as exc:
        return Result(action, "error", reason=str(exc))
    verified = read(capability)
    # A successful setter alone is insufficient: expose actual post-write state.
    return Result(action, verified.status, verified.value, verified.reason)
