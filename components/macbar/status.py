"""Small, GTK-independent readers for MacBar's local system indicators."""

from __future__ import annotations

import re
import datetime as dt
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Battery:
    percent: int
    state: str


@dataclass(frozen=True)
class Volume:
    percent: int
    muted: bool


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def clock_text(now: dt.datetime, width: int) -> str:
    """Preserve a useful clock on narrow laptop screens."""
    if width < 480:
        return f"{now:%H:%M}"
    if width < 680:
        return f"{WEEKDAYS[now.weekday()]}  {now:%H:%M}"
    return f"{WEEKDAYS[now.weekday()]} {now.day:02d} {MONTHS[now.month - 1]}  {now:%H:%M}"


def network_status(state: int, connection_type: str, active_types: tuple[str, ...] = ()) -> tuple[str, str]:
    """Use the active physical connection when VPN is the default route."""
    if state < 40:
        return "network-offline-symbolic", "Network disconnected"
    if state < 50:
        return "network-transmit-receive-symbolic", "Connecting…"

    physical_type = connection_type
    if physical_type not in ("802-11-wireless", "802-3-ethernet"):
        physical_type = next((kind for kind in active_types if kind in ("802-11-wireless", "802-3-ethernet")), "")

    if physical_type == "802-11-wireless":
        icon, description = "network-wireless-symbolic", "Wi-Fi connected"
    elif physical_type == "802-3-ethernet":
        icon, description = "network-wired-symbolic", "Ethernet connected"
    else:
        icon, description = "network-transmit-receive-symbolic", "Network connected"
    return icon, description + (" (limited)" if state < 70 else "")


def read_battery(root: Path = Path("/sys/class/power_supply")) -> Battery | None:
    try:
        batteries = sorted(
            p for p in root.iterdir()
            if p.is_dir() and (p / "type").is_file() and (p / "type").read_text().strip() == "Battery"
        )
    except (OSError, ValueError):
        return None
    for path in batteries:
        try:
            percent = int((path / "capacity").read_text().strip())
            state = (path / "status").read_text().strip()
            return Battery(max(0, min(100, percent)), state)
        except (OSError, ValueError):
            continue
    return None


def parse_wpctl(text: str) -> Volume | None:
    match = re.search(r"Volume:\s*([0-9]+(?:\.[0-9]+)?)", text)
    if not match:
        return None
    percent = round(float(match.group(1)) * 100)
    return Volume(max(0, min(150, percent)), "[MUTED]" in text)


def parse_pactl(text: str, mute_text: str = "") -> Volume | None:
    match = re.search(r"/\s*([0-9]+)%", text)
    if not match:
        return None
    return Volume(min(150, int(match.group(1))), "yes" in mute_text.lower())

