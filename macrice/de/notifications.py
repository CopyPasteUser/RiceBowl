"""On-demand, read-only RicePop bridge to the sole existing Wayland host.

In the experimental labwc session, mako owns org.freedesktop.Notifications.
This module never starts another daemon, mutates D-Bus state, replays actions,
persists messages or polls in the background.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


class NotificationBridgeError(ValueError):
    def __init__(self, message: str, code: str = "notifications_unavailable") -> None:
        super().__init__(message)
        self.code = code


def _records(raw: bytes) -> tuple[list[dict[str, Any]], bool]:
    if len(raw) > 128 * 1024:
        raise NotificationBridgeError("Notification host response is oversized",
                                      "invalid_notification_response")
    try:
        records = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise NotificationBridgeError("Notification host returned invalid JSON",
                                      "invalid_notification_response") from exc
    if type(records) is not list:
        raise NotificationBridgeError("Notification list must be an array",
                                      "invalid_notification_response")
    result = []
    for record in records[:64]:
        if type(record) is not dict or type(record.get("id")) is not int or not 0 < record["id"] <= 2**32 - 1:
            raise NotificationBridgeError("Notification entry is invalid",
                                          "invalid_notification_response")
        for key in ("summary", "body", "app_name", "urgency"):
            if record.get(key) is not None and type(record[key]) is not str:
                raise NotificationBridgeError("Notification text is invalid",
                                              "invalid_notification_response")
        result.append({
            "id": record["id"],
            "summary": (record.get("summary") or "")[:160],
            "body": (record.get("body") or "")[:2048],
            "app_name": (record.get("app_name") or "")[:80],
            "urgency": (record.get("urgency") or "unknown")[:32],
        })
    return result, len(records) > 64


def inspect() -> dict[str, Any]:
    """Query the active notification owner only on explicit CLI invocation."""
    command = shutil.which("makoctl")
    if command is None:
        raise NotificationBridgeError("makoctl is not installed")
    snapshots = {}
    truncated = False
    for source, action in (("active", "list"), ("history", "history")):
        try:
            process = subprocess.run([command, action, "-j"], capture_output=True,
                                     timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise NotificationBridgeError("Wayland notification host is unreachable") from exc
        if process.returncode:
            raise NotificationBridgeError("Wayland notification host rejected a read-only query")
        snapshots[source], limited = _records(process.stdout)
        truncated |= limited
    return {"ok": True, "backend": "mako", "active": snapshots["active"],
            "history": snapshots["history"], "truncated": truncated,
            "read_only": True, "actions_replayed": False,
            "mutates_active_desktop": False, "source_contains_private_messages": True}


def invalid(error: NotificationBridgeError) -> dict[str, Any]:
    return {"ok": False, "backend": "mako", "active": [], "history": [],
            "read_only": True, "error": {"code": error.code, "message": str(error)}}
