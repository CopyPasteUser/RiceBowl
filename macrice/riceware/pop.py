"""ricePop: one XFCE-owned notification history for all future rice UIs.

No replacement org.freedesktop.Notifications owner, duplicate log, or daemon.
Never replay stale third-party notification actions from the history log.
"""

from __future__ import annotations

import shutil
import subprocess
import logging
from dataclasses import dataclass
from typing import Callable

from .. import chrome_notification_backend as xfce

Notification = xfce.LoggedNotification
NotificationUnavailable = xfce.NotificationUnavailable


@dataclass(frozen=True)
class NotificationStatus:
    history_available: bool
    unread: bool | None
    quiet: bool | None
    reason: str | None = None


def status() -> NotificationStatus:
    """Truthful capabilities even if the optional XFCE log is not exposed."""
    quiet = xfce.read_dnd()
    try:
        return NotificationStatus(True, xfce.has_unread(), quiet)
    except NotificationUnavailable as exc:
        return NotificationStatus(False, None, quiet, str(exc))


def _identifier(value: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 192 or not value.isprintable():
        raise ValueError("Invalid notification identifier")
    return value


def history() -> tuple[Notification, ...]:
    return xfce.list_notifications()


def unread() -> bool:
    return xfce.has_unread()


def quiet_mode() -> bool | None:
    return xfce.read_dnd()


def set_quiet_mode(enabled: bool) -> bool:
    return xfce.set_dnd(enabled)


def mark_read(ids: tuple[str, ...] | None = None) -> None:
    if ids is not None:
        if len(ids) > xfce.MAX_ITEMS:
            raise ValueError("Too many notification identifiers")
        ids = tuple(_identifier(item) for item in ids)
    xfce.mark_read(ids)


def dismiss(identifier: str) -> None:
    xfce.delete_notification(_identifier(identifier))


def clear_history() -> None:
    xfce.clear_notifications()


def send(summary: str, body: str = "") -> None:
    """Send a user-requested notification through the current native host."""
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 160:
        raise ValueError("Notification summary must contain 1–160 characters")
    if not isinstance(body, str) or len(body) > 2048 or "\x00" in summary + body:
        raise ValueError("Notification body is invalid or too long")
    command = shutil.which("notify-send")
    if command is None:
        raise NotificationUnavailable("notify-send is not installed")
    try:
        result = subprocess.run([command, "--app-name=RiceBowl", "--", summary, body],
                                capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise NotificationUnavailable("Native notification delivery failed") from exc
    if result.returncode:
        raise NotificationUnavailable("Native notification service rejected the message")


class NotificationWatch:
    """Event-driven XFCE log change signal, with explicit lifecycle cleanup.

    Create on the GTK/GLib main thread; callbacks run there. The XFCE service
    remains the sole notification owner and no worker/polling loop is started.
    """

    def __init__(self, callback: Callable[[], None], *, Gio=None):
        if not callable(callback):
            raise ValueError("Notification callback must be callable")
        if Gio is None:
            try:
                from gi.repository import Gio
            except ImportError as exc:
                raise NotificationUnavailable("Gio is not available") from exc
        self._gio = Gio
        self._callback = callback
        self._connection = None
        self._subscription = 0
        self._closed = False
        self.error: str | None = None
        try:
            Gio.bus_get(Gio.BusType.SESSION, None, self._ready)
        except (OSError, RuntimeError) as exc:
            raise NotificationUnavailable("Could not request the XFCE session bus") from exc

    def _ready(self, _source, result):
        if self._closed:
            return
        try:
            self._connection = self._gio.bus_get_finish(result)
            if self._closed:
                return
            self._subscription = self._connection.signal_subscribe(
                xfce.BUS_NAME, xfce.LOG_INTERFACE, None, xfce.OBJECT_PATH,
                None, self._gio.DBusSignalFlags.NONE, self._changed)
        except Exception as exc:
            self.error = f"XFCE notification signals unavailable: {type(exc).__name__}"
            logging.getLogger(__name__).debug(self.error)

    def _changed(self, *_args):
        if self._closed:
            return
        try:
            self._callback()
        except Exception:
            logging.getLogger(__name__).exception("Riceware notification observer failed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._connection is not None and self._subscription:
            self._connection.signal_unsubscribe(self._subscription)
            self._subscription = 0


def watch(callback: Callable[[], None], *, Gio=None) -> NotificationWatch:
    return NotificationWatch(callback, Gio=Gio)
