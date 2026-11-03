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


def _run(args: list[str]) -> str | None:
    try:
        result = subprocess.run(args, capture_output=True, text=True,
                                timeout=1.4, check=False)
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
