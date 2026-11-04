"""ricePop: one XFCE-owned notification history for all future rice UIs.

No replacement org.freedesktop.Notifications owner, duplicate log, or daemon.
Never replay stale third-party notification actions from the history log.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

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
