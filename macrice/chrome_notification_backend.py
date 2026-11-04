"""Read Xfce's genuine notification log without becoming a notification daemon.

The stable Xfce 0.9.7 `org.xfce.Notifyd.Log` D-Bus interface owns persistence,
read flags and deletion. RiceBowl never intercepts notification delivery or
keeps its own history. Calls must run off GTK's main thread.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import html
import re
import shutil
import subprocess


BUS_NAME = "org.xfce.Notifyd"
OBJECT_PATH = "/org/xfce/Notifyd"
LOG_INTERFACE = "org.xfce.Notifyd.Log"
MAX_ITEMS = 40


class NotificationUnavailable(RuntimeError):
    """The real Xfce notification-log interface is not available."""


@dataclass(frozen=True)
class LoggedNotification:
    identifier: str
    timestamp: str
    application: str
    icon: str
    summary: str
    body: str
    is_read: bool


def plain_text(raw: str, *, limit: int = 480) -> str:
    """Render untrusted notification markup as plain, bounded GTK label text."""
    text = re.sub(r"<[^>]*>", "", str(raw))
    text = html.unescape(text)
    return "".join(c for c in text if c.isprintable() or c in "\n\t")[:limit].strip()


def format_timestamp(timestamp_us: int) -> str:
    try:
        return datetime.fromtimestamp(timestamp_us / 1_000_000).strftime("%d %b · %H:%M")
    except (OSError, OverflowError, ValueError):
        return "Time unavailable"


def parse_entries(rows) -> tuple[LoggedNotification, ...]:
    """Use the official (sxssssssa(ss)ib) layout; reject unexpected payloads."""
    parsed = []
    for row in tuple(rows)[:MAX_ITEMS]:
        if not isinstance(row, (tuple, list)) or len(row) != 11:
            continue
        identifier, timestamp_us, _timezone, _app_id, app_name, icon, summary, body, _actions, _timeout, read = row
        if not isinstance(identifier, str) or not identifier or len(identifier) > 192:
            continue
        try:
            displayed_time = format_timestamp(int(timestamp_us))
        except (TypeError, ValueError):
            displayed_time = "Time unavailable"
        # A log may retain action labels after the corresponding notification
        # closed. Replaying them would invoke the wrong app or silently fail.
        safe_icon = icon if isinstance(icon, str) and re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", icon) else "dialog-information"
        parsed.append(LoggedNotification(
            identifier, displayed_time,
            plain_text(app_name, limit=80) or "Application", safe_icon,
            plain_text(summary, limit=160) or "Notification",
            plain_text(body), bool(read)))
    return tuple(parsed)


def _call(method, parameters=None):
    from gi.repository import Gio, GLib

    try:
        connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        result = connection.call_sync(
            BUS_NAME, OBJECT_PATH, LOG_INTERFACE, method, parameters, None,
            Gio.DBusCallFlags.NONE, 3000, None)
        return result.unpack() if result else ()
    except (GLib.Error, OSError, RuntimeError) as exc:
        raise NotificationUnavailable("Xfce's notification history is unavailable") from exc


def list_notifications() -> tuple[LoggedNotification, ...]:
    from gi.repository import GLib

    result = _call("List", GLib.Variant("(sub)", ("", MAX_ITEMS, False)))
    if len(result) != 1:
        raise NotificationUnavailable("Xfce returned an unexpected notification-log format")
    return parse_entries(result[0])


def has_unread() -> bool:
    result = _call("HasUnread")
    if len(result) != 1 or not isinstance(result[0], bool):
        raise NotificationUnavailable("Xfce returned an unexpected unread status")
    return result[0]


def mark_read(ids: tuple[str, ...] | None = None):
    if ids is None:
        _call("MarkAllRead")
    elif ids:
        from gi.repository import GLib

        _call("MarkRead", GLib.Variant("(as)", (list(ids),)))


def delete_notification(identifier: str):
    from gi.repository import GLib

    if not isinstance(identifier, str) or not identifier:
        raise ValueError("Invalid notification ID")
    _call("Delete", GLib.Variant("(as)", ([identifier],)))


def clear_notifications():
    _call("Clear")


def read_dnd() -> bool | None:
    """Query xfconf's actual persisted DND value (None means unknown)."""
    if not shutil.which("xfconf-query"):
        return None
    try:
        proc = subprocess.run(
            ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb"],
            capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode:
        return None
    value = proc.stdout.strip().casefold()
    return {"true": True, "false": False}.get(value)


def set_dnd(enabled: bool) -> bool:
    if not isinstance(enabled, bool) or read_dnd() is None:
        raise NotificationUnavailable("Xfce Do Not Disturb is not configurable")
    try:
        proc = subprocess.run(
            ["xfconf-query", "-c", "xfce4-notifyd", "-p", "/do-not-disturb",
             "-s", "true" if enabled else "false"],
            capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NotificationUnavailable("Could not update Do Not Disturb") from exc
    if proc.returncode or read_dnd() is not enabled:
        raise NotificationUnavailable("Do Not Disturb change could not be verified")
    return enabled
