"""ricePop: one XFCE-owned notification history for all future rice UIs.

No replacement org.freedesktop.Notifications owner, duplicate log, or daemon.
Never replay stale third-party notification actions from the history log.
"""

from __future__ import annotations

import shutil
import subprocess

from .. import chrome_notification_backend as xfce

Notification = xfce.LoggedNotification
NotificationUnavailable = xfce.NotificationUnavailable


def history() -> tuple[Notification, ...]:
    return xfce.list_notifications()


def unread() -> bool:
    return xfce.has_unread()


def quiet_mode() -> bool | None:
    return xfce.read_dnd()


def set_quiet_mode(enabled: bool) -> bool:
    return xfce.set_dnd(enabled)


def mark_read(ids: tuple[str, ...] | None = None) -> None:
    xfce.mark_read(ids)


def dismiss(identifier: str) -> None:
    xfce.delete_notification(identifier)


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
