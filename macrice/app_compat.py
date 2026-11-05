"""Read-only X11 evidence for cross-application rice compatibility.

XFWM themes window frames, not application-rendered content. This inspector
never reads window titles, arguments, profiles or application preferences.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable, Mapping


_PROPERTIES = ("WM_CLASS", "_GTK_FRAME_EXTENTS", "_MOTIF_WM_HINTS", "_NET_WM_WINDOW_TYPE")
_SAFE_LABEL = re.compile(r"[A-Za-z0-9_. +\-]{1,80}\Z")
_WINDOW_ID = re.compile(r"(?:0x)?[0-9a-fA-F]{1,12}\Z")
_APP_GUIDANCE = {
    "photocraft": (
        "PhotoCraft uses a self-drawn egui interface. Its interior cannot be "
        "restyled by XFWM or GTK. In PhotoCraft, enable Preferences > Interface "
        "> System Title Bar to allow the rice's XFWM window decoration."
    ),
    "thunderbird": (
        "Thunderbird owns much of its application interface. In Settings > "
        "General > Language & Appearance, disable 'Hide system window titlebar' "
        "to expose the rice's XFWM decoration. GTK/XFWM cannot guarantee "
        "complete Thunderbird interior theming."
    ),
}


def _safe_label(raw: str) -> str:
    """Prevent arbitrary X properties or theme names from leaking to reports."""
    value = raw.strip()
    return value if _SAFE_LABEL.fullmatch(value) else "<redacted>"


def parse_properties(output: str) -> dict[str, object]:
    """Parse only requested properties; never include unexpected X11 data."""
    entries: dict[str, str | None] = {name: None for name in _PROPERTIES}
    for line in output.splitlines():
        name, separator, value = line.partition(" = ")
        if name in entries and separator:
            entries[name] = value

    raw_classes = entries["WM_CLASS"]
    names = re.findall(r'"([^"\r\n]*)"', raw_classes) if raw_classes else []
    classes = [_safe_label(name) for name in names[:2]]
    # _GTK_FRAME_EXTENTS is a hint, not conclusive proof of CSD.
    return {
        "wm_class": classes,
        "gtk_frame_extents_hint": entries["_GTK_FRAME_EXTENTS"] is not None,
        "motif_hints_present": entries["_MOTIF_WM_HINTS"] is not None,
        "window_type_present": entries["_NET_WM_WINDOW_TYPE"] is not None,
    }


def inspect_window(
    *,
    window_id: str | None = None,
    environment: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    """Inspect one selected X11 window without modifying its state.

    An explicit ID is validated before passing it to xprop. Interactive
    selection is bounded to 25 seconds, and the output is bounded to 8 KiB.
    """
    env = os.environ if environment is None else environment
    if env.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        raise ValueError("This inspector needs an XFCE/X11 session; Wayland is not supported.")
    if not env.get("DISPLAY"):
        raise ValueError("No X11 DISPLAY available. Sign in to your XFCE/X11 desktop.")
    if not which("xprop"):
        raise ValueError("Missing xprop; install the x11-utils package to inspect X11 windows.")
    if window_id is not None and not _WINDOW_ID.fullmatch(window_id):
        raise ValueError("--window-id must be a hexadecimal X11 window ID (for example 0x12345).")

    command = ["xprop", "-notype"]
    if window_id is not None:
        command.extend(("-id", window_id))
    command.extend(_PROPERTIES)
    try:
        result = run(command, capture_output=True, text=True, timeout=3 if window_id else 25,
                     check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("X11 selection timed out; try --window-id with an existing window.") from exc
    if result.returncode:
        raise ValueError("xprop could not inspect that X11 window (selection cancelled or window closed).")
    if len(result.stdout) > 8192:
        raise ValueError("X11 window properties exceeded the safe inspection size limit.")
    properties = parse_properties(result.stdout)
    classes = properties["wm_class"]
    app = next((name for name in _APP_GUIDANCE if any(name in item.lower() for item in classes)), None)

    def theme(channel: str, property_name: str) -> str | None:
        if not which("xfconf-query"):
            return None
        try:
            response = run(["xfconf-query", "-c", channel, "-p", property_name],
                           capture_output=True, text=True, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if response.returncode:
            return None
        return _safe_label(response.stdout[:256])

    return {
        "application": app or "unknown",
        "window": properties,
        "active_gtk_theme": theme("xsettings", "/Net/ThemeName"),
        "active_xfwm_theme": theme("xfwm4", "/general/theme"),
        "scope": (
            "XFWM styles server-side window decorations; GTK styles GTK widgets. "
            "Qt, Electron, browser chrome and custom-drawn interiors have their own styling boundaries. "
            "The X11 hints above do not conclusively establish whether a window uses client-side decorations."
        ),
        "next_step": _APP_GUIDANCE.get(
            app,
            "Check whether this application offers a system/native title-bar setting. "
            "Compare the window frame with the active XFWM theme; custom-rendered content "
            "cannot be forced to use the rice's GTK theme.",
        ),
    }


def format_report(report: Mapping[str, object]) -> str:
    props = report["window"]
    assert isinstance(props, dict)
    classes = props["wm_class"]
    assert isinstance(classes, list)
    return "\n".join((
        "RiceBowl application compatibility (read-only)",
        "WM_CLASS: " + (", ".join(classes) if classes else "unavailable"),
        "Detected app: " + str(report["application"]),
        "GTK theme: " + str(report["active_gtk_theme"] or "unavailable"),
        "XFWM theme: " + str(report["active_xfwm_theme"] or "unavailable"),
        "GTK frame-extents hint: " + ("present" if props["gtk_frame_extents_hint"] else "absent"),
        "Motif decoration hints: " + ("present" if props["motif_hints_present"] else "absent"),
        "Window type hint: " + ("present" if props["window_type_present"] else "absent"),
        "Scope: " + str(report["scope"]),
        "Next step: " + str(report["next_step"]),
    ))
