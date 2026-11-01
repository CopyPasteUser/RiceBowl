"""Installed applications via GIO: no parsing or executing untrusted Exec strings."""

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio

from .model import AppEntry, category_for

try:
    gi.require_version("GioUnix", "2.0")
    from gi.repository import GioUnix
except (ValueError, ImportError):  # Older Mint / GLib still provides Gio.DesktopAppInfo.
    GioUnix = None


def _categories(app: object, app_id: str) -> str:
    if hasattr(app, "get_categories"):
        return app.get_categories() or ""
    desktop = None
    if GioUnix is not None:
        desktop = GioUnix.DesktopAppInfo.new(app_id)
    elif hasattr(Gio, "DesktopAppInfo"):
        desktop = Gio.DesktopAppInfo.new(app_id)
    return desktop.get_categories() or "" if desktop else ""


def installed_apps() -> list[AppEntry]:
    entries = {}
    for app in Gio.AppInfo.get_all():
        app_id = app.get_id()
        if not app_id or not app.should_show():
            continue
        details = None
        if hasattr(app, "get_keywords"):
            details = app
        elif GioUnix is not None:
            details = GioUnix.DesktopAppInfo.new(app_id)
        elif hasattr(Gio, "DesktopAppInfo"):
            details = Gio.DesktopAppInfo.new(app_id)
        keywords = ""
        if details is not None:
            if hasattr(details, "get_generic_name"):
                keywords += " " + (details.get_generic_name() or "")
            if hasattr(details, "get_keywords"):
                keywords += " " + " ".join(details.get_keywords() or [])
        entries[app_id] = AppEntry(
            app_id=app_id,
            name=app.get_display_name() or app.get_name() or app_id,
            description=app.get_description() or "",
            category=category_for(_categories(app, app_id)),
            keywords=keywords.strip(),
            icon=app.get_icon(),
            launcher=app,
        )
    return sorted(entries.values(), key=lambda entry: entry.name.casefold())
