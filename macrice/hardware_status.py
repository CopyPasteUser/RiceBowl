"""Low-overhead hardware status for RiceBowl's non-macOS XFCE taskbars.

No root access, privileged APIs, long-running monitors, or fake status indicators.
All probes are bounded and return an explicit unknown state if unavailable.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BatteryState:
    percent: int
    charging: bool
    label: str


@dataclass(frozen=True)
class SoundState:
    percent: int | None
    muted: bool | None


@dataclass(frozen=True)
class DesktopStatus:
    battery: BatteryState | None
    network: str               # wifi, ethernet, offline
    sound: SoundState


@dataclass(frozen=True)
class WifiNetwork:
    ssid: str
    signal: int
    security: str
    connected: bool


@dataclass(frozen=True)
class SoundOutput:
    name: str
    label: str
    active: bool


@dataclass(frozen=True)
class BluetoothState:
    powered: bool | None
    connected: tuple[str, ...]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def _battery_percent(path: Path) -> tuple[float, float] | None:
    """Prefer energy-weighted aggregation, fall back to capacity percentage."""
    for prefix in ("energy", "charge"):
        current, full = _read(path / f"{prefix}_now"), _read(path / f"{prefix}_full")
        try:
            if current is not None and full is not None and float(full) > 0:
                return max(0.0, float(current)), float(full)
        except ValueError:
            pass
    try:
        capacity = _read(path / "capacity")
        if capacity is not None:
            return max(0.0, min(100.0, float(capacity))), 100.0
    except ValueError:
        pass
    return None


def read_battery(root: Path = Path("/sys/class/power_supply")) -> BatteryState | None:
    """Report the combined installed batteries. Desktop machines return None."""
    try:
        batteries = sorted(root.iterdir())
    except OSError:
        return None
    total_now = total_full = 0.0
    states = []
    for path in batteries:
        if _read(path / "type") != "Battery" or _read(path / "present") == "0":
            continue
        result = _battery_percent(path)
        if result is None:
            continue
        now, full = result
        total_now += min(now, full)
        total_full += full
        states.append((_read(path / "status") or "Unknown").casefold())
    if not total_full:
        return None
    percent = max(0, min(100, round(total_now / total_full * 100)))
    charging = any(state == "charging" for state in states)
    label = ("Charging" if charging else "Fully charged" if all(
        state == "full" for state in states) else "Discharging" if any(
        state == "discharging" for state in states) else "Battery status unknown")
    return BatteryState(percent, charging, label)


def read_network(root: Path = Path("/sys/class/net"),
                 route: Path = Path("/proc/net/route")) -> str:
    """Use the active IPv4 default route, not interface-name guesses.

    Report offline when the default route is absent. No SSID or IP is read.
    """
    text = _read(route)
    if not text:
        return "offline"
    candidates = []
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 8 or fields[1] != "00000000":
            continue
        try:
            flags = int(fields[3], 16)
            metric = int(fields[6])
        except ValueError:
            continue
        if not (flags & 1) or not fields[0] or fields[0] == "lo":
            continue
        candidates.append((metric, fields[0]))
    def kind(interface: str) -> str | None:
        path = root / interface
        if (path / "wireless").exists() or (path / "phy80211").exists() or interface.startswith("wl"):
            return "wifi"
        if interface.startswith(("en", "eth")):
            return "ethernet"
        return None  # VPNs, tunnels and virtual bridges are not Ethernet.

    # Normally the default route points directly to the physical interface.
    for _, interface in sorted(candidates):
        physical = kind(interface)
        if physical:
            return physical
    if candidates:
        # A VPN/tunnel may own the default route. Infer its active underlying
        # transport from the physical interfaces rather than calling it LAN.
        try:
            connected = [path.name for path in root.iterdir()
                         if (_read(path / "operstate") == "up" or
                             _read(path / "carrier") == "1") and kind(path.name)]
        except OSError:
            connected = []
        for preferred in ("wifi", "ethernet"):
            if any(kind(name) == preferred for name in connected):
                return preferred
    return "offline"


def _run(args: list[str], *, timeout: float = 1.4) -> str | None:
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def read_sound() -> SoundState:
    """Prefer WirePlumber; fall back to PulseAudio with bounded subprocesses."""
    if shutil.which("wpctl"):
        raw = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
        if raw is not None:
            match = re.search(r"Volume:\s*([0-9.]+)", raw)
            if match:
                try:
                    percent = max(0, min(150, round(float(match.group(1)) * 100)))
                    return SoundState(percent, "[MUTED]" in raw)
                except ValueError:
                    pass
    if shutil.which("pactl"):
        volume = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
        mute = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
        if volume is not None and mute is not None:
            match = re.search(r"(\d+)%", volume)
            if match:
                return SoundState(int(match.group(1)), "yes" in mute.casefold())
    return SoundState(None, None)


def read_status() -> DesktopStatus:
    return DesktopStatus(read_battery(), read_network(), read_sound())


def _nmcli_fields(line: str) -> tuple[str, ...]:
    """Split nmcli terse records, respecting escaped colons and backslashes."""
    fields, current, escaped = [], [], False
    for char in line:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return tuple(fields)


def read_wifi_radio() -> bool | None:
    """Return actual NetworkManager Wi-Fi radio state, or unknown."""
    if not shutil.which("nmcli"):
        return None
    state = _run(["nmcli", "radio", "wifi"])
    return {"enabled": True, "disabled": False}.get((state or "").casefold())


def read_wifi_networks(*, rescan: bool = False) -> tuple[WifiNetwork, ...]:
    """Bounded, read-only Wi-Fi list. Hidden SSIDs are not actionable."""
    if not shutil.which("nmcli"):
        return ()
    raw = _run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
                "device", "wifi", "list", "--rescan", "yes" if rescan else "no"],
               timeout=7.0 if rescan else 1.8)
    if raw is None:
        return ()
    networks = {}
    for line in raw.splitlines():
        fields = _nmcli_fields(line)
        if len(fields) != 4 or not fields[1].strip():
            continue
        try:
            signal = max(0, min(100, int(fields[2])))
        except ValueError:
            continue
        entry = WifiNetwork(fields[1], signal, fields[3], fields[0] == "*")
        old = networks.get(entry.ssid)
        if old is None or (entry.connected, entry.signal) > (old.connected, old.signal):
            networks[entry.ssid] = entry
    return tuple(sorted(networks.values(),
                        key=lambda item: (not item.connected, -item.signal, item.ssid.casefold()))[:12])


def set_wifi_radio(enabled: bool) -> bool:
    """Make an explicit radio change and verify NetworkManager's read-back."""
    if not isinstance(enabled, bool):
        raise ValueError("Wi-Fi state must be boolean")
    if not shutil.which("nmcli"):
        raise RuntimeError("NetworkManager nmcli is not installed")
    try:
        result = subprocess.run(["nmcli", "radio", "wifi", "on" if enabled else "off"],
                                capture_output=True, text=True, timeout=6, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Wi-Fi radio request timed out or failed") from exc
    if result.returncode != 0 or read_wifi_radio() is not enabled:
        raise RuntimeError("NetworkManager could not verify the requested Wi-Fi state")
    return enabled


def disconnect_wifi() -> bool:
    """Explicitly disconnect the currently connected Wi-Fi device only."""
    if not shutil.which("nmcli"):
        raise RuntimeError("NetworkManager nmcli is not installed")
    raw = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device", "status"])
    connected = None
    for line in (raw or "").splitlines():
        fields = _nmcli_fields(line)
        if len(fields) == 3 and fields[1] == "wifi" and fields[2].startswith("connected"):
            connected = fields[0]
            break
    if connected is None:
        raise RuntimeError("There is no connected Wi-Fi interface")
    try:
        result = subprocess.run(["nmcli", "device", "disconnect", connected],
                                capture_output=True, text=True, timeout=8, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Wi-Fi disconnect timed out") from exc
    if result.returncode != 0:
        raise RuntimeError("NetworkManager could not disconnect Wi-Fi")
    return not any(item.connected for item in read_wifi_networks())


def connect_wifi(ssid: str) -> bool:
    """Join a user-selected SSID through NetworkManager, never through a shell.

    Saved credentials work immediately; unknown secured networks may require
    opening the graphical network editor for password entry.
    """
    if not isinstance(ssid, str) or not ssid.strip() or "\x00" in ssid:
        raise ValueError("Select a visible Wi-Fi network")
    if not shutil.which("nmcli"):
        raise RuntimeError("NetworkManager nmcli is not installed")
    try:
        result = subprocess.run(["nmcli", "--wait", "18", "device", "wifi", "connect", ssid],
                                capture_output=True, text=True, timeout=21, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Wi-Fi connection timed out") from exc
    if result.returncode:
        raise RuntimeError("Could not join this Wi-Fi network; saved credentials may be missing")
    return any(item.connected and item.ssid == ssid for item in read_wifi_networks())


def read_brightness(root: Path = Path("/sys/class/backlight")) -> int | None:
    """Read active backlight percentage without privileged commands."""
    try:
        paths = sorted(root.iterdir())
    except OSError:
        return None
    for path in paths:
        try:
            maximum = int(_read(path / "max_brightness") or "0")
            actual = int(_read(path / "brightness") or "0")
        except ValueError:
            continue
        if maximum > 0:
            return max(0, min(100, round(actual / maximum * 100)))
    return None


def set_brightness(percent: int) -> int:
    """Optional backlight write through existing brightnessctl permissions."""
    if isinstance(percent, bool) or not isinstance(percent, int) or not 1 <= percent <= 100:
        raise ValueError("Brightness must be between 1 and 100 percent")
    if not shutil.which("brightnessctl"):
        raise RuntimeError("brightnessctl is not installed")
    try:
        result = subprocess.run(["brightnessctl", "set", f"{percent}%"],
                                capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Brightness adjustment failed") from exc
    actual = read_brightness()
    if result.returncode or actual is None or abs(actual - percent) > 5:
        raise RuntimeError("Brightness change was not verified; check backlight permissions")
    return actual


def read_sound_outputs() -> tuple[SoundOutput, ...]:
    """List real PulseAudio/PipeWire output sinks; no invented labels."""
    if not shutil.which("pactl"):
        return ()
    raw = _run(["pactl", "list", "short", "sinks"])
    default = _run(["pactl", "get-default-sink"])
    if not raw:
        return ()
    outputs = []
    for line in raw.splitlines():
        fields = line.split("\t")
        if len(fields) < 2 or not fields[1].strip():
            continue
        name = fields[1].strip()
        # Keep the full identifier available by tooltip; the human readable
        # suffix is useful even on older pactl without JSON descriptions.
        label = name.rsplit(".", 1)[-1].replace("_", " ").replace("-", " ")
        outputs.append(SoundOutput(name, label, name == default))
    return tuple(outputs[:12])


def set_sound_output(name: str) -> SoundOutput:
    """Select only an enumerated sink and read back the effective default."""
    outputs = read_sound_outputs()
    if not name or name not in {entry.name for entry in outputs}:
        raise ValueError("Select an installed audio output")
    try:
        result = subprocess.run(["pactl", "set-default-sink", name],
                                capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Audio output selection failed") from exc
    selected = next((entry for entry in read_sound_outputs() if entry.name == name and
                     entry.active), None)
    if result.returncode or selected is None:
        raise RuntimeError("Audio output could not be verified")
    return selected


def read_power_profiles() -> tuple[str | None, tuple[str, ...]]:
    """Read optional power-profiles-daemon state (not universal on XFCE)."""
    if not shutil.which("powerprofilesctl"):
        return None, ()
    current = _run(["powerprofilesctl", "get"])
    listed = _run(["powerprofilesctl", "list"])
    supported = tuple(name for name in ("power-saver", "balanced", "performance")
                      if listed and re.search(r"(?m)^\s*\*?\s*" + re.escape(name) + r":", listed))
    return current if current in supported else None, supported


def set_power_profile(name: str) -> str:
    current, supported = read_power_profiles()
    if name not in supported:
        raise ValueError("Power profile is not supported by this device")
    try:
        result = subprocess.run(["powerprofilesctl", "set", name],
                                capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Power profile change failed") from exc
    actual, _supported = read_power_profiles()
    if result.returncode or actual != name:
        raise RuntimeError("Power profile change could not be verified")
    return name


def read_bluetooth() -> BluetoothState:
    if not shutil.which("bluetoothctl"):
        return BluetoothState(None, ())
    info = _run(["bluetoothctl", "show"], timeout=2.5)
    if not info:
        return BluetoothState(None, ())
    status = re.search(r"(?m)^\s*Powered:\s*(yes|no)\b", info)
    if not status:
        return BluetoothState(None, ())
    raw = _run(["bluetoothctl", "devices", "Connected"], timeout=2.5)
    devices = tuple(match.group(1).strip() for line in (raw or "").splitlines()
                    if (match := re.match(r"Device\s+[0-9a-fA-F:]{17}\s+(.+)", line)))[:10]
    return BluetoothState(status.group(1) == "yes", devices)


def set_bluetooth_power(enabled: bool) -> BluetoothState:
    if not isinstance(enabled, bool):
        raise ValueError("Bluetooth power must be boolean")
    if not shutil.which("bluetoothctl"):
        raise RuntimeError("BlueZ bluetoothctl is not installed")
    try:
        result = subprocess.run(["bluetoothctl", "power", "on" if enabled else "off"],
                                capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Bluetooth adapter action failed") from exc
    state = read_bluetooth()
    if result.returncode or state.powered is not enabled:
        raise RuntimeError("Bluetooth power change could not be verified")
    return state


def read_microphone() -> SoundState:
    """Read default microphone level and mute via PipeWire or PulseAudio."""
    if shutil.which("wpctl"):
        raw = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"])
        if raw is not None:
            match = re.search(r"Volume:\s*([0-9.]+)", raw)
            if match:
                try:
                    percent = max(0, min(150, round(float(match.group(1)) * 100)))
                    return SoundState(percent, "[MUTED]" in raw)
                except ValueError:
                    pass
    if shutil.which("pactl"):
        volume = _run(["pactl", "get-source-volume", "@DEFAULT_SOURCE@"])
        mute = _run(["pactl", "get-source-mute", "@DEFAULT_SOURCE@"])
        if volume is not None and mute is not None:
            match = re.search(r"(\d+)%", volume)
            if match:
                return SoundState(int(match.group(1)), "yes" in mute.casefold())
    return SoundState(None, None)


def set_microphone_volume(percent: int) -> SoundState:
    """Set microphone volume and verify the actual input level."""
    if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
        raise ValueError("Microphone volume must be between 0 and 100")
    errors = []
    for args in (["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", f"{percent / 100:.2f}"],
                 ["pactl", "set-source-volume", "@DEFAULT_SOURCE@", f"{percent}%"]):
        if not shutil.which(args[0]):
            continue
        try:
            result = subprocess.run(args, capture_output=True, text=True,
                                    timeout=2.0, check=False)
        except (OSError, subprocess.TimeoutExpired):
            errors.append(args[0] + ": unavailable")
            continue
        if result.returncode:
            errors.append(args[0] + ": rejected")
            continue
        state = read_microphone()
        if state.percent is not None and abs(state.percent - percent) <= 2:
            return state
        errors.append(args[0] + ": read-back mismatch")
    raise RuntimeError("Microphone level could not be verified" +
                       (": " + "; ".join(errors) if errors else " (no backend installed)"))


def set_microphone_mute(muted: bool) -> SoundState:
    """Set the microphone mute state; never use an optimistic UI update."""
    if not isinstance(muted, bool):
        raise ValueError("Microphone mute must be boolean")
    value = "1" if muted else "0"
    errors = []
    for args in (["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", value],
                 ["pactl", "set-source-mute", "@DEFAULT_SOURCE@", value]):
        if not shutil.which(args[0]):
            continue
        try:
            result = subprocess.run(args, capture_output=True, text=True,
                                    timeout=2.0, check=False)
        except (OSError, subprocess.TimeoutExpired):
            errors.append(args[0] + ": unavailable")
            continue
        if result.returncode:
            errors.append(args[0] + ": rejected")
            continue
        state = read_microphone()
        if state.muted is muted:
            return state
        errors.append(args[0] + ": read-back mismatch")
    raise RuntimeError("Microphone mute could not be verified" +
                       (": " + "; ".join(errors) if errors else " (no backend installed)"))


def set_sound_volume(percent: int) -> SoundState:
    """Set the default sink to a bounded value and verify the actual backend.

    Never report success based only on an exit code; a mismatch or unavailable
    backend is an explicit error so the UI can offer recovery.
    """
    if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
        raise ValueError("Audio volume must be an integer from 0 to 100")
    candidates = (
        ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent / 100:.2f}"],
        ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
    )
    errors = []
    for args in candidates:
        if not shutil.which(args[0]):
            continue
        try:
            result = subprocess.run(
                args, capture_output=True, text=True, timeout=2.0, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"{args[0]}: {type(exc).__name__}")
            continue
        if result.returncode:
            errors.append(f"{args[0]}: exit {result.returncode}")
            continue
        state = read_sound()
        if state.percent is not None and abs(state.percent - percent) <= 2:
            return state
        errors.append(f"{args[0]}: read-back mismatch")
    raise RuntimeError("Unable to set verified audio volume" +
                       (": " + "; ".join(errors) if errors else " (no backend available)"))


def set_sound_mute(muted: bool) -> SoundState:
    """Change default sink mute state and verify it, without shell execution."""
    if not isinstance(muted, bool):
        raise ValueError("Mute target must be a boolean")
    value = "1" if muted else "0"
    candidates = (
        ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", value],
        ["pactl", "set-sink-mute", "@DEFAULT_SINK@", value],
    )
    failures = []
    for args in candidates:
        if not shutil.which(args[0]):
            continue
        try:
            process = subprocess.run(
                args, capture_output=True, text=True, timeout=2.0, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append(f"{args[0]}: {type(exc).__name__}")
            continue
        if process.returncode:
            failures.append(f"{args[0]}: exit {process.returncode}")
            continue
        actual = read_sound()
        if actual.muted is muted:
            return actual
        failures.append(f"{args[0]}: read-back mismatch")
    raise RuntimeError("Unable to verify mute state" +
                       (": " + "; ".join(failures) if failures else " (no backend available)"))
