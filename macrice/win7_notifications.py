"""Windows 7 Aero-owned device balloons; XFCE still owns third-party delivery.

No freedesktop notification bus takeover or duplicate third-party popups. The
balloon only represents actual RiceBowl-observed hardware transitions.
"""

from __future__ import annotations

from .luna_notifications import LunaBalloon, event_messages, removable_mount_message


class Win7Balloon(LunaBalloon):
    css_prefix = "win7-balloon"
    heading_text = "RiceBowl · Windows 7"


__all__ = ("Win7Balloon", "event_messages", "removable_mount_message")
