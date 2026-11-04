"""Bounded, read-only Linux probes for Aqua Control Center detail pages.

All subprocesses use explicit argument vectors, short timeouts and capped
output. User-visible data is never cached to disk or sent to a network.
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeResult:
    title: str
    lines: tuple[str, ...]
    error: str | None = None


def _run(args: tuple[str, ...], *, which=shutil.which, runner=subprocess.run):
    if not which(args[0]):
        return None, args[0] + " is not installed"
    try:
        result = runner(args, capture_output=True, text=True, check=False, timeout=2.5)
    except subprocess.TimeoutExpired:
        return None, "Reading device information timed out"
    except OSError:
        return None, "Device information is unavailable"
    if result.returncode:
        return None, "The system service did not provide device information"
    return result.stdout[:16_384], None


def split_nmcli_fields(line: str) -> tuple[str, ...]:
    """Parse `nmcli -t` escaped colons without splitting SSID names."""
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


def wifi_networks(*, run=_run):
    raw, failure = run(("nmcli", "--terse", "--fields", "ACTIVE,SSID,SIGNAL,SECURITY",
                        "device", "wifi", "list", "--rescan", "no"))
    if failure:
        return ProbeResult("Nearby Wi-Fi", (), failure)
    entries = {}
    for line in (raw or "").splitlines():
        fields = split_nmcli_fields(line)
        if len(fields) != 4 or not fields[1]:
            continue
        active, ssid, strength, security = fields
        try:
            signal = max(0, min(100, int(strength)))
        except ValueError:
            continue
        # Preserve the real SSID but avoid unbounded content in this popup.
        ssid = ssid[:65]
        entry = (active.casefold() == "yes", signal, ssid, security[:35])
        previous = entries.get(ssid)
        if previous is None or (entry[0], entry[1]) > (previous[0], previous[1]):
            entries[ssid] = entry
    sorted_entries = sorted(entries.values(), key=lambda item: (-int(item[0]), -item[1], item[2]))
    visible = tuple(("Connected · " if active else "") +
                    f"{ssid} · {signal}% · {security or 'Open'}"
                    for active, signal, ssid, security in sorted_entries[:12])
    return ProbeResult("Nearby Wi-Fi", visible or ("No access points reported",))


def bluetooth_adapter(*, run=_run):
    raw, failure = run(("bluetoothctl", "show"))
    if failure:
        return ProbeResult("Bluetooth adapter", (), failure)
    name = next((line.partition(":")[2].strip() for line in (raw or "").splitlines()
                 if line.strip().startswith("Name:")), "Unknown")
    powered = next((line.partition(":")[2].strip() for line in (raw or "").splitlines()
                    if line.strip().startswith("Powered:")), None)
    if powered is None:
        return ProbeResult("Bluetooth adapter", (), "No Bluetooth controller detected")
    return ProbeResult("Bluetooth adapter", ("Adapter: " + name[:70],
                                               "Power: " + ("On" if powered == "yes" else "Off")))


def audio_outputs(*, run=_run):
    raw, failure = run(("pactl", "list", "short", "sinks"))
    if failure:
        return ProbeResult("Available sound outputs", (), failure)
    lines = []
    for line in (raw or "").splitlines()[:12]:
        parts = line.split("\t")
        if len(parts) >= 5:
            lines.append(parts[1][:72] + " · " + parts[4][:20])
    return ProbeResult("Available sound outputs", tuple(lines) or ("No output devices reported",))


def connected_displays(*, run=_run):
    raw, failure = run(("xrandr", "--query"))
    if failure:
        return ProbeResult("Connected displays", (), failure)
    lines = []
    for line in (raw or "").splitlines():
        found = re.match(r"^([\w-]+) connected(?: primary)?(?: (\d+x\d+)[+\d]*)?", line)
        if found:
            lines.append(found[1] + " · " + (found[2] or "resolution unavailable"))
    return ProbeResult("Connected displays", tuple(lines) or ("No connected displays reported",))


def system_info():
    try:
        disk = shutil.disk_usage("/")
        disk_line = f"Root storage: {disk.free // (1024**3)} GiB free of {disk.total // (1024**3)} GiB"
    except OSError:
        disk_line = "Root storage: unavailable"
    return ProbeResult("Linux system", (platform.system() + " " + platform.release(),
                                         "Architecture: " + platform.machine(), disk_line))


def probe(kind: str) -> ProbeResult:
    """Only the explicitly supported read-only device probes are dispatched."""
    handlers = {"wifi": wifi_networks, "bluetooth": bluetooth_adapter,
                "audio": audio_outputs, "display": connected_displays,
                "system": system_info}
    if kind not in handlers:
        return ProbeResult("Device information", (), "Unsupported device information request")
    return handlers[kind]()
