"""riceSpice: UI-independent access to RiceBowl's existing Linux controls.

No device is changed by reading a snapshot. Mutations use existing verified
backends; later rice-specific interfaces can consume the same results.
"""

from __future__ import annotations

import threading
import re
from dataclasses import dataclass
from typing import Any, Callable

from .. import hardware_status as hardware


@dataclass(frozen=True)
class Result:
    name: str
    status: str  # ok, unavailable, error
    value: Any = None
    reason: str | None = None


@dataclass(frozen=True)
class ActionSpec:
    name: str
    kind: str  # boolean, integer, selection, address, ssid, none
    minimum: int | None = None
    maximum: int | None = None


ACTION_SPECS = {
    "audio_volume": ActionSpec("audio_volume", "integer", 0, 100),
    "audio_mute": ActionSpec("audio_mute", "boolean"),
    "audio_output": ActionSpec("audio_output", "selection"),
    "bluetooth_power": ActionSpec("bluetooth_power", "boolean"),
    "bluetooth_connect": ActionSpec("bluetooth_connect", "address"),
    "bluetooth_disconnect": ActionSpec("bluetooth_disconnect", "address"),
    "brightness": ActionSpec("brightness", "integer", 1, 100),
    "microphone_volume": ActionSpec("microphone_volume", "integer", 0, 100),
    "microphone_mute": ActionSpec("microphone_mute", "boolean"),
    "power_profile": ActionSpec("power_profile", "selection"),
    "wifi": ActionSpec("wifi", "boolean"),
    "wifi_connect": ActionSpec("wifi_connect", "ssid"),
    "wifi_disconnect": ActionSpec("wifi_disconnect", "none"),
}


def action_specs() -> tuple[ActionSpec, ...]:
    """Renderer control metadata; no hardware probing or UI layout policy."""
    return tuple(ACTION_SPECS.values())


def _validate(action: str, value: Any) -> None:
    spec = ACTION_SPECS[action]
    if spec.kind == "none":
        if value is not None:
            raise ValueError(f"{action} takes no value")
        return
    if spec.kind == "boolean":
        if type(value) is not bool:
            raise ValueError(f"{action} requires a boolean")
        return
    if spec.kind == "integer":
        if type(value) is not int or not spec.minimum <= value <= spec.maximum:
            raise ValueError(f"{action} requires {spec.minimum}–{spec.maximum}")
        return
    if not isinstance(value, str) or not value.strip() or "\x00" in value or len(value) > 256:
        raise ValueError(f"{action} requires a valid text selection")
    if spec.kind == "address" and not re.fullmatch(r"[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}", value):
        raise ValueError("Select a valid Bluetooth device address")
    if spec.kind == "ssid":
        try:
            size = len(value.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise ValueError("Wi-Fi SSID is not valid UTF-8") from exc
        if size > 32:
            raise ValueError("Wi-Fi SSIDs must not exceed 32 bytes")


READERS: dict[str, Callable[[], Any]] = {
    "audio": hardware.read_sound,
    "audio_outputs": hardware.read_sound_outputs,
    "battery": hardware.read_battery,
    "bluetooth": hardware.read_bluetooth,
    "brightness": hardware.read_brightness,
    "desktop_status": hardware.read_status,
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
    "bluetooth_disconnect": (
        lambda address: hardware.set_bluetooth_connection(address, False), "bluetooth"),
    "brightness": (hardware.set_brightness, "brightness"),
    "microphone_volume": (hardware.set_microphone_volume, "microphone"),
    "microphone_mute": (hardware.set_microphone_mute, "microphone"),
    "power_profile": (hardware.set_power_profile, "power_profiles"),
    "wifi": (hardware.set_wifi_radio, "wifi"),
    "wifi_connect": (hardware.connect_wifi, "wifi_networks"),
    "wifi_disconnect": (hardware.disconnect_wifi, "wifi_networks"),
}

# Lock a device family across write AND readback. UI workers may race, but two
# RiceBowl surfaces must not interleave conflicting writes to the same device.
_LOCKS = {name: threading.Lock() for name in
          ("audio", "bluetooth", "brightness", "microphone", "power", "wifi")}


def _family(action: str) -> str:
    if action.startswith("audio"):
        return "audio"
    if action.startswith("bluetooth"):
        return "bluetooth"
    if action.startswith("microphone"):
        return "microphone"
    if action.startswith("power"):
        return "power"
    if action.startswith("wifi"):
        return "wifi"
    return action


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
    if name == "wifi_networks" and not value:
        # Empty can mean no nearby networks OR an absent NetworkManager.
        return hardware.read_wifi_radio() is not None
    return True


def read(name: str) -> Result:
    if name not in READERS:
        raise ValueError(f"Unknown riceSpice capability: {name}")
    try:
        value = READERS[name]()
        available = _available(name, value)
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
        return Result(name, "error", reason=str(exc))
    if not available:
        return Result(name, "unavailable", value, "No supported device or backend")
    return Result(name, "ok", value=value)


def scan_wifi(*, rescan: bool = False) -> Result:
    """Read Wi-Fi networks; explicit Refresh can request an actual NM rescan."""
    if type(rescan) is not bool:
        raise ValueError("rescan must be a boolean")
    try:
        value = hardware.read_wifi_networks(rescan=rescan)
        available = _available("wifi_networks", value)
    except (OSError, RuntimeError, ValueError, TypeError, AttributeError) as exc:
        return Result("wifi_networks", "error", reason=str(exc))
    if not available:
        return Result("wifi_networks", "unavailable", value, "NetworkManager unavailable")
    return Result("wifi_networks", "ok", value)


def snapshot() -> tuple[Result, ...]:
    """On-demand capabilities, without the aggregate status's duplicate probes."""
    return tuple(read(name) for name in READERS if name != "desktop_status")


def _matches(action: str, requested: Any, actual: Any) -> bool:
    """Verify the requested target against real state, not a setter's exit code."""
    if action in ("audio_volume", "microphone_volume"):
        return isinstance(requested, int) and not isinstance(requested, bool) and \
            actual.percent is not None and abs(actual.percent - requested) <= 2
    if action in ("audio_mute", "microphone_mute"):
        return isinstance(requested, bool) and actual.muted is requested
    if action == "audio_output":
        return any(item.name == requested and item.active for item in actual)
    if action == "bluetooth_power":
        return isinstance(requested, bool) and actual.powered is requested
    if action in ("bluetooth_connect", "bluetooth_disconnect"):
        expected = action == "bluetooth_connect"
        return any(item.address == requested and item.connected is expected for item in actual.devices)
    if action == "brightness":
        return isinstance(requested, int) and not isinstance(requested, bool) and \
            abs(actual - requested) <= 5
    if action == "power_profile":
        return actual[0] == requested
    if action == "wifi":
        return isinstance(requested, bool) and actual is requested
    if action == "wifi_connect":
        return any(item.ssid == requested and item.connected for item in actual)
    if action == "wifi_disconnect":
        return not any(item.connected for item in actual)
    return False


def change(action: str, value: Any = None) -> Result:
    if action not in WRITERS:
        raise ValueError(f"Unknown riceSpice action: {action}")
    writer, capability = WRITERS[action]
    try:
        _validate(action, value)
    except ValueError as exc:
        return Result(action, "error", reason=str(exc))
    with _LOCKS[_family(action)]:
        try:
            if action == "wifi_disconnect":
                outcome = writer()
            else:
                outcome = writer(value)
            if action in ("wifi_connect", "wifi_disconnect") and outcome is not True:
                raise RuntimeError("NetworkManager could not verify the connection state")
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            return Result(action, "error", reason=str(exc))
        verified = read(capability)
        if verified.status != "ok":
            return Result(action, "error", verified.value,
                          verified.reason or "Requested change has no verifiable readback")
        try:
            matches = _matches(action, value, verified.value)
        except (AttributeError, TypeError, ValueError):
            matches = False
        if not matches:
            return Result(action, "error", verified.value,
                          "Requested value does not match current device state")
        return Result(action, "ok", verified.value)
