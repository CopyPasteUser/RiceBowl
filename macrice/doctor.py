"""Read-only, on-demand environment checks for a recoverable XFCE desktop.

Never enumerate nearby networks, private files, notification bodies or tokens.
No process is started and no desktop setting is changed by these checks.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from .environment import bin_home, data_home
from .installer import MANAGED_MARKER


@dataclass(frozen=True)
class Check:
    key: str
    status: str  # ok, warning, info
    message: str
    advice: str = ""

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def diagnose(*, environment: Mapping[str, str] | None = None,
             which=None, data_root: Path | None = None,
             bin_root: Path | None = None, gi_available: bool | None = None) -> tuple[Check, ...]:
    """Inspect prerequisites without subprocess calls or hardware mutations."""
    env = os.environ if environment is None else environment
    available = shutil.which if which is None else which
    root = data_home() if data_root is None else data_root
    binaries = bin_home() if bin_root is None else bin_root
    found = []

    def add(key, good, success, failure, advice="", *, optional=False):
        found.append(Check(key, "ok" if good else "info" if optional else "warning",
                           success if good else failure, "" if good else advice))

    x11 = bool(env.get("DISPLAY")) and env.get("XDG_SESSION_TYPE", "x11").lower() != "wayland"
    add("x11", x11, "X11 display is available", "No supported X11 display detected",
        "Log into an XFCE on X11 session before applying a rice.")
    desktop = " ".join(env.get(name, "") for name in ("XDG_CURRENT_DESKTOP", "DESKTOP_SESSION"))
    add("xfce", "xfce" in desktop.casefold(), "XFCE session detected",
        "XFCE session not confirmed", "RiceBowl requires XFCE/X11 for supported session switching.")
    if gi_available is None:
        try:
            gi_available = importlib.util.find_spec("gi") is not None
        except (ValueError, ImportError):
            gi_available = False
    add("gtk", gi_available, "Python GTK introspection available",
        "Python GTK bindings unavailable", "Install python3-gi and gir1.2-gtk-3.0.")
    for name in ("xfconf-query", "xfce4-panel", "xfwm4"):
        add(name, bool(available(name)), f"{name} detected", f"{name} not found",
            "Install the corresponding XFCE package before switching desktop shells.")

    manager = root / "macrice"
    add("installed", (manager / MANAGED_MARKER).is_file() and not manager.is_symlink(),
        "User-local managed RiceBowl installation detected",
        "Managed RiceBowl installation not detected",
        "Run bash install.sh --dry-run, then install as your regular user.")
    add("launcher", (binaries / "ricebowl").is_file(), "RiceBowl launcher present",
        "RiceBowl launcher not found", "Install the user-local RiceBowl launcher.")
    add("toggle", (binaries / "ricehub-toggle").is_file(),
        "RiceBowl keyboard launcher available", "RiceBowl keyboard launcher missing",
        "Reinstall the managed launchers before replacing the XFCE panel.")
    # No xfconf or keyboard write is needed to check the local recovery record.
    shortcut_state = root / "macrice-state/session-shortcuts.json"
    if shortcut_state.is_symlink() or shortcut_state.parent.is_symlink():
        add("shortcuts", False, "Keyboard recovery record is healthy",
            "Keyboard recovery state contains a symlink",
            "Do not overwrite it; inspect the path before restoring shortcuts.")
    elif not shortcut_state.exists():
        add("shortcuts", False, "Keyboard recovery record is healthy",
            "No managed shortcut backup is currently needed",
            "RiceBowl creates one when you explicitly apply a rice.", optional=True)
    else:
        try:
            metadata = shortcut_state.stat()
            if (not shortcut_state.is_file() or metadata.st_uid != os.getuid()
                    or metadata.st_mode & 0o077 or metadata.st_size > 8192):
                raise ValueError("Untrusted recovery record")
            record = json.loads(shortcut_state.read_text(encoding="utf-8"))
            if (record.get("version") != 1 or
                    set(record.get("original", {})) != {"Super_L", "Control_R"} or
                    set(record.get("managed", {})) != {"Super_L", "Control_R"}):
                raise ValueError("Recovery record schema mismatch")
            add("shortcuts", True, "Keyboard recovery record is valid",
                "Keyboard recovery record is invalid")
        except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
            add("shortcuts", False, "Keyboard recovery record is valid",
                "Keyboard shortcut recovery record is unreadable or unsafe",
                "Inspect the record and restore it from your private backup; never delete it blindly.")
    for key, commands, label, advice in (
        ("network", ("nmcli",), "NetworkManager device controls",
         "Install NetworkManager CLI if you want native Wi-Fi controls."),
        ("audio", ("pactl", "wpctl"), "PulseAudio/PipeWire device controls",
         "Install pactl or wpctl for native volume integration."),
        ("bluetooth", ("bluetoothctl",), "Bluetooth device controls",
         "Install BlueZ if you have a Bluetooth adapter."),
        ("power", ("powerprofilesctl",), "Optional power profiles",
         "Power profiles are optional; not every desktop supports them."),
        ("plank", ("plank",), "Optional Plank dock",
         "Plank is optional and remains user-controlled."),
    ):
        add(key, any(available(command) for command in commands), label + " available",
            label + " unavailable", advice, optional=True)
    return tuple(found)


def summary(checks: tuple[Check, ...]) -> tuple[int, int, int]:
    return tuple(sum(item.status == status for item in checks)
                 for status in ("ok", "warning", "info"))
