"""Bounded read-only RandR topology for Aqua's native Display page.

Resolution/position mutations stay with XFCE Display Settings, which owns the
screen-confirmation and rollback flow. An unverified UI must not risk blacking
out a laptop or a remote session.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass


_OUTPUT = re.compile(
    r"^([A-Za-z0-9_.-]+) connected(?P<primary> primary)?"
    r"(?: (?P<mode>\d{2,5}x\d{2,5})\+(?P<x>-?\d+)\+(?P<y>-?\d+))?"
)
_MODE = re.compile(r"^\s+(\d{2,5}x\d{2,5})\s+(.+)$")


@dataclass(frozen=True)
class DisplayOutput:
    name: str
    current_mode: str | None
    position: tuple[int, int] | None
    primary: bool
    modes: tuple[str, ...]


def parse_randr(raw: str) -> tuple[DisplayOutput, ...]:
    """Only enumerate connected outputs and real enumerated modes (max 8)."""
    if not isinstance(raw, str):
        raise ValueError("RandR query must be text")
    results = []
    current = None
    for line in raw.splitlines()[:350]:
        found = _OUTPUT.match(line)
        if found:
            if current is not None:
                results.append(current)
            if len(results) >= 8:
                current = None
                break
            mode = found.group("mode")
            current = {"name": found.group(1), "mode": mode,
                       "pos": (int(found.group("x")), int(found.group("y")))
                       if found.group("x") is not None else None,
                       "primary": bool(found.group("primary")), "modes": []}
            continue
        if line and not line.startswith(" "):
            if current is not None:
                results.append(current)
                current = None
            continue
        if current is None:
            continue
        mode = _MODE.match(line)
        if mode and mode.group(1) not in current["modes"] and len(current["modes"]) < 10:
            current["modes"].append(mode.group(1))
            if current["mode"] is None and "*" in mode.group(2):
                current["mode"] = mode.group(1)
    if current is not None and len(results) < 8:
        results.append(current)
    return tuple(DisplayOutput(item["name"], item["mode"], item["pos"],
                               item["primary"], tuple(item["modes"]))
                 for item in results[:8])


def read_monitor_layout() -> tuple[DisplayOutput, ...]:
    """Read actual X11 layout; never issue a resolution-changing command."""
    if os.environ.get("XDG_SESSION_TYPE", "").casefold() == "wayland":
        raise RuntimeError("RandR layout is unavailable in a Wayland session")
    if not os.environ.get("DISPLAY"):
        raise RuntimeError("No X11 display is available")
    if not shutil.which("xrandr"):
        raise RuntimeError("xrandr is not installed")
    try:
        result = subprocess.run(("xrandr", "--query"), capture_output=True,
                                text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Could not read the X11 monitor layout") from exc
    if result.returncode:
        raise RuntimeError("X11 monitor query failed")
    return parse_randr(result.stdout)
