"""On-demand MPRIS media controls over the existing user session D-Bus.

No player is spawned, no metadata is retained, and no extra monitor runs.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass


_PREFIX = "org.mpris.MediaPlayer2."
_VALID_NAME = re.compile(r"^org\.mpris\.MediaPlayer2\.[A-Za-z0-9_.-]+$")
_COMMANDS = frozenset(("PlayPause", "Next", "Previous"))


@dataclass(frozen=True)
class MediaPlayer:
    bus_name: str
    label: str
    title: str
    artist: str
    status: str
    can_play_pause: bool
    can_next: bool
    can_previous: bool


def _gio():
    import gi

    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib
    return Gio, GLib


def _call(connection, Gio, GLib, bus_name, interface, method, parameters=None,
          signature=None, *, timeout=1200):
    reply = connection.call_sync(bus_name, "/org/mpris/MediaPlayer2" if
                                 bus_name.startswith(_PREFIX) else "/org/freedesktop/DBus",
                                 interface, method, parameters,
                                 GLib.VariantType(signature) if signature else None,
                                 Gio.DBusCallFlags.NONE, timeout, None)
    return reply.unpack() if reply is not None else ()


def _unpack(value):
    return value.unpack() if hasattr(value, "unpack") else value


def _read_one(connection, Gio, GLib, bus_name):
    props = _call(connection, Gio, GLib, bus_name, "org.freedesktop.DBus.Properties",
                  "GetAll", GLib.Variant("(s)", ("org.mpris.MediaPlayer2.Player",)),
                  "(a{sv})", timeout=900)[0]
    def get(key, default=None):
        return _unpack(props.get(key, default))
    metadata = get("Metadata", {}) or {}
    title = str(_unpack(metadata.get("xesam:title", "")))[:90]
    artists = _unpack(metadata.get("xesam:artist", [])) or []
    artist = ", ".join(str(item) for item in artists[:2])[:75] if isinstance(artists, (list, tuple)) else ""
    status = str(get("PlaybackStatus", "Unknown"))[:18]
    can_control = bool(get("CanControl", False))
    return MediaPlayer(
        bus_name=bus_name, label=bus_name[len(_PREFIX):].split(".", 1)[0][:32],
        title=title or "Unknown track", artist=artist,
        status=status,
        can_play_pause=can_control and (bool(get("CanPause", False)) if status == "Playing"
                                        else bool(get("CanPlay", False))),
        can_next=can_control and bool(get("CanGoNext", False)),
        can_previous=can_control and bool(get("CanGoPrevious", False)),
    )


def read_media_players() -> tuple[MediaPlayer, ...]:
    """Read at most five session players; failures of one do not hide others."""
    try:
        Gio, GLib = _gio()
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        names = connection.call_sync(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
            "ListNames", None, GLib.VariantType("(as)"), Gio.DBusCallFlags.NONE,
            1200, None).unpack()[0]
    except Exception as exc:
        raise RuntimeError("Session media bus is not available") from exc
    players = []
    for name in sorted(name for name in names if _VALID_NAME.fullmatch(name))[:5]:
        try:
            players.append(_read_one(connection, Gio, GLib, name))
        except Exception:
            # Browser media sessions may disappear between ListNames and GetAll.
            continue
    return tuple(sorted(players, key=lambda item: item.status != "Playing"))


def media_action(bus_name: str, command: str) -> tuple[MediaPlayer, ...]:
    """Dispatch only allowlisted MPRIS actions; re-read for immediate feedback."""
    if not isinstance(bus_name, str) or not _VALID_NAME.fullmatch(bus_name):
        raise ValueError("Choose a known media player")
    if command not in _COMMANDS:
        raise ValueError("Unsupported media action")
    Gio, GLib = _gio()
    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        before = _read_one(connection, Gio, GLib, bus_name)
        allowed = {"PlayPause": before.can_play_pause, "Next": before.can_next,
                   "Previous": before.can_previous}[command]
        if not allowed:
            raise RuntimeError("The player does not permit this media action")
        _call(connection, Gio, GLib, bus_name, "org.mpris.MediaPlayer2.Player",
              command, timeout=1500)
        after = _read_one(connection, Gio, GLib, bus_name)
        if command == "PlayPause" and before.status in ("Playing", "Paused"):
            for _attempt in range(3):
                if after.status != before.status:
                    break
                time.sleep(0.12)  # Bounded, in the shared worker, not GTK's main loop.
                after = _read_one(connection, Gio, GLib, bus_name)
            else:
                raise RuntimeError("Player did not confirm the playback-state change")
        return (after,)
    except (OSError, RuntimeError, ValueError):
        raise
    except Exception as exc:
        raise RuntimeError("Media player command failed or player disappeared") from exc
