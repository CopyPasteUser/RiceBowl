"""Native ChromeOS-inspired shelf/launcher styling and small pure helpers.

The identity is Material You for Linux, with GTK3/X11 widgets and real Gio apps.
No proprietary Google icons, Android apps or simulated cloud integrations.
"""

from __future__ import annotations

import math
import os


def launcher_favorites(apps, pinned_ids, *, limit=4):
    """Choose real desktop apps deterministically, preferring saved shelf pins."""
    catalog = tuple(apps)
    lookup = {app.get_id(): app for app in catalog if app.get_id()}
    selected = []
    seen = set()

    def append(app):
        identifier = app.get_id()
        if identifier and identifier not in seen and len(selected) < limit:
            selected.append(app)
            seen.add(identifier)

    for identifier in pinned_ids:
        if identifier in lookup:
            append(lookup[identifier])
    for keyword in ("browser", "files", "settings", "terminal", "editor"):
        for app in catalog:
            if keyword in (app.get_display_name() or app.get_name() or "").casefold():
                append(app)
                break
    for app in catalog:
        append(app)
    return tuple(selected)


def apply_rounded_window_shape(window, radius=26):
    """Clip GTK popup corners under compositors *and* plain uncomposited X11.

    GTK border-radius only rounds the child background; without a compositor
    the native window's rectangular backing otherwise appears around it. X11
    shaping is an optional improvement, and gracefully fails where unsupported.
    """
    try:
        import cairo
        import gi
        # The PyGObject Cairo bridge registers cairo.Region as a foreign
        # GObject type. python3-cairo alone does not register it with Gdk.
        gi.require_foreign("cairo")
        native = window.get_window()
        if native is None:
            return False
        width, height = window.get_size()
        radius = min(radius, (width - 1) // 2, (height - 1) // 2)
        if radius <= 0:
            return False
        region = cairo.Region(cairo.RectangleInt(0, radius, width,
                                                height - 2 * radius))
        for y in range(radius):
            distance = radius - y - 0.5
            inset = math.ceil(radius - math.sqrt(radius * radius - distance * distance))
            strip = cairo.RectangleInt(inset, y, max(1, width - 2 * inset), 1)
            region.union(strip)
            region.union(cairo.RectangleInt(inset, height - y - 1,
                                             max(1, width - 2 * inset), 1))
        native.shape_combine_region(region, 0, 0)
        if os.environ.get("RICEBOWL_SHAPE_DEBUG") == "1":
            print("ChromeOS X11 popup mask", window.get_title(),
                  "size", (width, height), "origin", native.get_root_origin(),
                  "corner in mask", region.contains_point(0, 0), flush=True)
    except (ImportError, AttributeError, OSError, ValueError, TypeError, KeyError) as exc:
        if os.environ.get("RICEBOWL_SHAPE_DEBUG") == "1":
            print("ChromeOS X11 popup mask unavailable:", repr(exc), flush=True)
    return False


CSS = b"""
/* ChromeOS Material You, independently drawn for Linux/XFCE. The installed
   GTK theme uses the same iris/lavender color family. */
@define-color chrome-ink #252b43;
@define-color chrome-iris #4b66d7;
@define-color chrome-lilac #e5e9ff;
@define-color chrome-surface #f9faff;
@define-color chrome-muted #616d85;

.aero-taskbar { background: rgba(232,233,249,.94); border-top: 1px solid #f6f5ff;
  color: @chrome-ink; padding: 5px 14px; min-height: 55px;
  font-family: "Google Sans", "Noto Sans", sans-serif; }
.aero-start { background: #f8f8ff; border: 1px solid rgba(198,202,230,.85);
  color: @chrome-ink; border-radius: 26px; box-shadow: none;
  min-width: 44px; min-height: 42px; padding: 4px; }
.aero-start:hover, .aero-start:focus { background: #dce5ff; border-color: #a9b9fa; }
.chrome-app-shelf { background: transparent; border: 0; border-radius: 0; padding: 0 2px; }
.chrome-app-shelf .aero-pin, .chrome-app-shelf .aero-task {
  background: transparent; border: 1px solid transparent; border-radius: 24px;
  min-width: 38px; min-height: 38px; padding: 5px; color: @chrome-ink;
  box-shadow: none; }
.chrome-app-shelf .aero-pin:hover, .chrome-app-shelf .aero-task:hover,
.chrome-app-shelf .aero-pin:focus, .chrome-app-shelf .aero-task:focus {
  background: #d9e1fa; border-color: #c6d0f1; }
.chrome-app-shelf .aero-task-active { background: #d3ddff;
  border: 1px solid #c5cff3; border-bottom: 3px solid @chrome-iris; }
.chrome-status-pill { background: rgba(248,247,255,.91);
  border: 1px solid #c7cde8; border-radius: 28px; padding: 1px 6px; }
.chrome-status-pill .rice-status, .chrome-status-pill .aero-quick,
.chrome-status-pill .aero-time, .chrome-status-pill .aero-desktop {
  background: transparent; border: 1px solid transparent; border-radius: 17px;
  box-shadow: none; color: @chrome-ink; padding: 5px 6px; }
.chrome-status-pill .rice-status:hover, .chrome-status-pill .aero-quick:hover,
.chrome-status-pill .aero-quick:focus, .chrome-status-pill .rice-status:focus {
  background: #dce6ff; border-color: #c8d4f0; }
.chrome-status-pill .rice-status label { color: @chrome-ink; font-size: 10px; }
.chrome-status-pill .aero-time { font-size: 10px; font-weight: 600; }
.chrome-status-pill .aero-desktop { min-width: 14px; }
.chrome-clock-button { background: transparent; border: 0; border-radius: 16px;
  box-shadow: none; padding: 2px 4px; }
.chrome-clock-button:hover, .chrome-clock-button:focus { background: #dce6ff; }

.chrome-launcher, .chrome-quick-root {
  background: @chrome-surface; color: @chrome-ink;
  border: 1px solid #cfd4eb; border-radius: 26px;
  font-family: "Google Sans", "Noto Sans", sans-serif;
  box-shadow: none; }
.chrome-launcher { padding: 17px 18px 14px; }
.chrome-launcher-header { padding: 0 1px 4px; }
.chrome-launcher-title { font-size: 16px; font-weight: 700; color: @chrome-ink; }
.chrome-launcher .aero-menu-search {
  background: #edf0fb; color: @chrome-ink; border: 1px solid #d5dbef;
  border-radius: 24px; padding: 10px 15px; box-shadow: none; }
.chrome-launcher .aero-menu-search:focus {
  background: #fff; border: 2px solid @chrome-iris; padding: 9px 14px; }
.chrome-launcher-settings { background: #e6eafa; color: #354a8a;
  border: 1px solid transparent; border-radius: 19px;
  min-width: 34px; min-height: 34px; padding: 5px; box-shadow: none; }
.chrome-launcher-settings:hover, .chrome-launcher-settings:focus {
  background: #d5dfff; border-color: #a7b8f1; }
.chrome-section-heading { color: #424d6a; font-size: 12px; font-weight: 700; }
.chrome-divider { background: #dfe3f1; min-height: 1px; }
.chrome-launcher .ten-tile, .chrome-app-card {
  background: transparent; color: @chrome-ink; border: 1px solid transparent;
  border-radius: 16px; box-shadow: none; padding: 6px 5px; }
.chrome-launcher .ten-tile:hover, .chrome-app-card:hover,
.chrome-launcher .ten-tile:focus, .chrome-app-card:focus {
  background: #e3eaff; border-color: #cad5f6; }
.chrome-app-label { color: @chrome-ink; font-size: 11px; }
.chrome-empty { color: @chrome-muted; font-size: 13px; padding: 15px; }
.chrome-launcher scrollbar trough { background: #eef0f8; }
.chrome-launcher scrollbar slider { background: #c5cce4;
  border-radius: 6px; min-width: 7px; min-height: 13px; }
.chrome-launcher scrollbar slider:hover { background: #9daedf; }

.chrome-quick-root { padding: 16px; }
.chrome-quick-title { color: @chrome-ink; font-size: 17px; font-weight: 700; }
.chrome-quick-date { color: @chrome-muted; font-size: 11px; }
.chrome-section-caption { color: #4a5676; font-size: 11px; font-weight: 700; }
.chrome-quick-button { background: #e1e7fa; border: 1px solid #d4ddf3;
  color: @chrome-ink; border-radius: 19px; box-shadow: none;
  min-height: 55px; padding: 9px 12px; }
.chrome-quick-button:hover, .chrome-quick-button:focus {
  background: #d0dcfd; border-color: #a4b8ec; }
.chrome-quick-button:disabled { background: #eff0f5; color: #8990a3;
  border-color: #e0e3ec; }
.chrome-quick-action { color: @chrome-ink; font-size: 11px; font-weight: 600; }
.chrome-quick-detail { color: #596782; font-size: 10px; }
.chrome-quick-chevron { color: #536aa9; font-size: 21px; font-weight: 600; }
.chrome-quick-icon { color: #394f8f; }
.chrome-surface { background: #eef0fa; border: 1px solid #e3e6f2;
  border-radius: 19px; padding: 11px; }
.chrome-status-line { color: #465477; font-size: 11px; }
.chrome-quick-root scale trough { background: #cfd6ec;
  border-radius: 6px; min-height: 5px; }
.chrome-quick-root scale highlight { background: @chrome-iris; border-radius: 6px; }
.chrome-quick-root scale slider { background: #fff; border: 2px solid @chrome-iris;
  min-width: 14px; min-height: 14px; }
.chrome-quick-root levelbar block.filled { background: @chrome-iris; }
.chrome-quick-mute { background: #dfe6fa; color: @chrome-ink;
  border-radius: 17px; border: 1px solid #ccd5ed; padding: 7px 11px; }
.chrome-quick-mute:checked { background: #c4d2ff; color: #293d82; }
.chrome-quick-mute:disabled { color: #8b92a6; background: #eff0f5; }
.chrome-quick-back { background: #e1e7fa; border: 1px solid #cbd5ef;
  color: @chrome-ink; border-radius: 18px; min-width: 34px;
  min-height: 34px; font-size: 20px; box-shadow: none; }
.chrome-quick-back:hover, .chrome-quick-back:focus { background: #d0dcfd; }
.chrome-quick-page-status { background: #e1e7fa; border-radius: 18px;
  color: @chrome-ink; font-size: 13px; font-weight: 600; padding: 19px 15px; }
.chrome-quick-page-description { color: @chrome-muted; font-size: 12px;
  padding: 7px 5px; }
.chrome-quick-page-action { background: #e6eafa; border: 1px solid #d5ddf5;
  border-radius: 18px; color: @chrome-ink; padding: 13px 11px;
  box-shadow: none; }
.chrome-quick-page-action:hover, .chrome-quick-page-action:focus {
  background: #d5dfff; border-color: #a7b8f1; }
.chrome-quick-page-action:disabled { color: #838ba0; background: #f0f1f6; }
.chrome-quick-root .chrome-native-panel { background: #eef0fb;
  border: 1px solid #e0e6f6; border-radius: 18px; padding: 12px; }
.chrome-quick-root .chrome-native-title { color: #41588f; font-size: 11px;
  font-weight: 700; }
.chrome-quick-root .chrome-native-status { color: #445577; font-size: 11px; }
.chrome-quick-root .chrome-native-error { color: #a32e4f; }
.chrome-quick-root .chrome-native-label, .chrome-quick-root .chrome-native-section {
  color: @chrome-ink; font-size: 12px; font-weight: 600; }
.chrome-quick-root .chrome-native-hint { color: @chrome-muted; font-size: 11px; }
.chrome-quick-root .chrome-native-confirm { background: #fff1e7; color: #754328;
  border-radius: 12px; padding: 8px; }
.chrome-quick-root .chrome-native-action, .chrome-quick-root .chrome-native-mini {
  background: #e0e7fd; border: 1px solid #cbd7f2; border-radius: 15px;
  color: #293d79; padding: 7px 9px; box-shadow: none; }
.chrome-quick-root .chrome-native-action:hover, .chrome-quick-root .chrome-native-mini:hover {
  background: #cfdbfe; }
.chrome-quick-root .chrome-native-panel switch { background: #cbd4e8;
  border-radius: 20px; min-height: 20px; }
.chrome-quick-root .chrome-native-panel switch:checked { background: @chrome-iris; }
.chrome-quick-root .chrome-native-panel switch slider { background: #fff;
  min-width: 16px; min-height: 16px; border-radius: 20px; }
.chrome-quick-root .chrome-native-panel combobox button { background: #e0e7fd;
  color: @chrome-ink; border-radius: 12px; }

/* ChromeOS Settings is a separate, persistent app window, not an XFCE
   Control Panel reskin. All selectors stay in the ChromeOS namespace. */
.chrome-settings-root { background: #f9faff; color: @chrome-ink;
  font-family: "Google Sans", "Noto Sans", sans-serif; }
.chrome-settings-header { background: #e9edfc; border-bottom: 1px solid #cfd7ef;
  padding: 13px 22px; }
.chrome-settings-header button { background: #dce5fc; border: 1px solid #ced8f2;
  border-radius: 18px; color: #33477d; padding: 8px 16px; box-shadow: none; }
.chrome-settings-title { font-size: 19px; font-weight: 700; color: @chrome-ink; }
.chrome-settings-root searchentry { background: #edf0fb; color: @chrome-ink;
  border: 1px solid #d1d9ef; border-radius: 24px; padding: 11px 17px;
  margin: 14px 22px; box-shadow: none; }
.chrome-settings-root searchentry:focus { background: white; border-color: @chrome-iris; }
.chrome-settings-sidebar { background: #f0f2fc; border-right: 1px solid #e2e5f2;
  padding: 12px 11px; }
.chrome-settings-nav { background: transparent; border: 1px solid transparent;
  box-shadow: none; border-radius: 20px; padding: 11px 12px;
  color: @chrome-ink; font-size: 12px; }
.chrome-settings-nav:hover, .chrome-settings-nav:focus { background: #dce5ff;
  border-color: #ccd7fa; }
.chrome-settings-nav-selected { background: #d4ddff; border-color: #becbfa;
  font-weight: 700; }
.chrome-settings-content { padding: 22px 26px; }
.chrome-settings-page-title { color: #252b43; font-size: 22px; font-weight: 700; }
.chrome-settings-subtitle { color: @chrome-muted; font-size: 12px; }
.chrome-settings-row { background: #edf0fb; color: @chrome-ink;
  border: 1px solid #e0e5f5; border-radius: 15px; box-shadow: none;
  padding: 12px 15px; }
.chrome-settings-row:hover, .chrome-settings-row:focus { background: #dfe8ff;
  border-color: #b2c4f4; }
.chrome-settings-action { color: @chrome-ink; font-size: 13px; font-weight: 600; }
.chrome-settings-state { background: #e5eafe; border-radius: 15px;
  color: #354b83; font-size: 13px; padding: 14px 16px; }
.chrome-settings-primary { background: #3c5ac9; color: white;
  border: 1px solid #3550b7; border-radius: 24px;
  box-shadow: none; padding: 12px 17px; }
.chrome-settings-primary:hover, .chrome-settings-primary:focus { background: #496add; }
.chrome-settings-primary:disabled { background: #e2e5f0; color: #6d778d;
  border-color: #d4d9e7; }
.chrome-quick-root scrollbar slider { background: #bcc8e8;
  border-radius: 6px; min-width: 7px; min-height: 13px; }
button:focus { outline: 2px solid #6583e9; outline-offset: -2px; }
"""
