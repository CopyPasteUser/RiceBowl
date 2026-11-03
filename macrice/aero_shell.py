"""On-demand, event-driven Frutiger Aero taskbar and searchable Start menu.

Only runs when explicitly launched or on login after selecting an Aero rice.
Uses the installed Gio .desktop catalog; does not poll the process table.
"""

from __future__ import annotations

from pathlib import Path
import ctypes
import ctypes.util
import logging
import os
import shutil
import subprocess
import threading

from .aero_layout import PANEL_HEIGHT, bottom_strut, menu_geometry, select_windows, task_capacity
from .aero_pins import PIN_LIMIT, PinConfigError, load_pins, pin_file, save_pins


APP_ID = "io.github.copypasteuser.RiceHub.AeroShell"


def app_catalog(Gio):
    """Keep only visible, distinct real application launchers."""
    candidates = (app for app in Gio.AppInfo.get_all() if app.should_show())
    result = {}
    for app in candidates:
        name = app.get_display_name() or app.get_name()
        if name and name.casefold() not in result:
            result[name.casefold()] = app
    return tuple(sorted(result.values(), key=lambda app: (app.get_display_name() or app.get_name()).casefold()))


def default_pins(apps) -> tuple[str, ...]:
    """Prefer the user's installed file manager, browser and terminal."""
    selected = []
    for keyword in ("file manager", "browser", "terminal"):
        for app in apps:
            identifier = app.get_id()
            label = (app.get_display_name() or app.get_name() or "").casefold()
            if keyword in label and identifier and identifier not in selected:
                selected.append(identifier)
                break
    return tuple(selected)


def matching_apps(apps, query: str):
    needle = query.casefold().strip()
    return tuple(app for app in apps if needle in
                 (app.get_display_name() or app.get_name() or "").casefold())


def luna_programs(apps, pins: tuple[str, ...], query: str, limit: int = 8):
    """Pick real installed apps for the XP pin band and the recent-program area."""
    if query.strip():
        return (), matching_apps(apps, query)[:limit]
    featured = []
    for category in ("WebBrowser", "Email"):
        for app in apps:
            classifier = getattr(app, "get_categories", None)
            categories = (classifier() or "").split(";") if callable(classifier) else ()
            if category in categories and app not in featured:
                featured.append(app)
                break
    for identifier in pins:
        if len(featured) >= 2:
            break
        for app in apps:
            if app.get_id() == identifier and app not in featured:
                featured.append(app)
                break
    featured = featured[:2]
    return tuple(featured), tuple(app for app in apps if app not in featured)[:limit]


CSS = b"""
.aero-taskbar {
  background-image: linear-gradient(to bottom, rgba(193,232,255,.95), rgba(91,161,211,.96) 48%, rgba(24,74,133,.98));
  border-top: 1px solid #d6f5ff; color: #fff; padding: 3px 12px;
}
.aero-start {
  background-image: linear-gradient(to bottom, #ddffff, #48b4e7 55%, #1474b8);
  border: 1px solid #e8ffff; border-radius: 23px;
  padding: 2px 14px 2px 4px; color: #fff; font-weight: bold;
  box-shadow: 0 1px 4px rgba(11,51,84,.55);
}
.aero-start:hover { background-image: linear-gradient(to bottom, #ffffff, #74d1f1 60%, #1985c5); }
.aero-start:focus { border: 2px solid #ffffff; }
.aero-pin { background: transparent; border: 1px solid transparent; padding: 5px 13px; border-radius: 3px; }
.aero-pin:hover { background: rgba(235,251,255,.25); border-color: rgba(255,255,255,.48); }
.aero-task { background: rgba(255,255,255,.10); border: 1px solid rgba(216,244,255,.36);
  border-bottom: 2px solid rgba(180,237,255,.65); border-radius: 4px;
  padding: 4px 6px; color: white; box-shadow: inset 0 1px rgba(255,255,255,.15); }
.aero-task:hover { background: rgba(224,250,255,.27); border-color: rgba(255,255,255,.75); }
.aero-task-active { background: rgba(221,247,255,.39); border-color: #e5faff;
  border-bottom: 2px solid #ffffff; }
.aero-task-overflow { background: transparent; color: #fff; border: 1px solid rgba(255,255,255,.30);
  border-radius: 4px; padding: 4px 8px; }
.aero-tray-icon { background: transparent; border: 0; padding: 3px; }
.aero-tray-icon:hover { background: rgba(255,255,255,.22); border-radius: 4px; }
.aero-glass { background-image: linear-gradient(to bottom, rgba(205,242,255,.79), rgba(94,172,221,.83) 48%, rgba(26,81,139,.90)); }
.aero-time { color: #fff; font-size: 11px; font-weight: bold; }
.aero-quick { background: transparent; border: 1px solid transparent; color: white; border-radius: 4px; padding: 4px; }
.aero-quick:hover, .aero-quick:focus { border-color: #d0f4ff; background: rgba(255,255,255,.24); }
.aero-desktop { background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.5); border-radius: 2px; min-width: 11px; padding: 2px; }
.aero-desktop:hover, .aero-desktop:focus { background: rgba(255,255,255,.47); }
.aero-menu-footer { border-top: 1px solid #96c1dd; padding-top: 8px; }
.aero-menu-power { color: #fff; border-radius: 4px; border: 1px solid #f4b99e; background-image: linear-gradient(to bottom, #fa946c, #c65530); padding: 6px 10px; }
.aero-menu-root { background: #eaf4fb; border: 1px solid #5e9bcc; border-radius: 8px; }
.aero-menu-heading { color: #244e6e; font-size: 20px; font-weight: bold; }
.aero-menu-sub { color: #577d9c; font-size: 12px; }
.aero-menu-search { border: 1px solid #6badd8; background: #fff; color: #193f60; border-radius: 4px; padding: 8px; }
.aero-menu-app { background: transparent; border: 1px solid transparent; box-shadow: none; color: #1a415f; border-radius: 3px; padding: 7px; }
.aero-menu-app:hover, .aero-menu-app:focus { background: #c4e6f9; border-color: #91c7e7; }
.aero-menu-side {
  background-image: linear-gradient(to bottom, #dff5ff, #a8d5f1 52%, #71acd6);
  border-left: 1px solid #83b6db; padding: 12px;
}
.aero-control-root { background-image: linear-gradient(to bottom, #f6fcff, #d6eaf8);
  color: #244e6e; border: 1px solid #6eabd4; border-radius: 7px; padding: 14px; }
.aero-control-quick { background-image: linear-gradient(to bottom, #ffffff, #c0dff3);
  color: #244e6e; border: 1px solid #82b3d6; border-radius: 5px; padding: 10px 8px; }
.aero-control-quick:hover, .aero-control-quick:focus { background: #eefaff;
  border-color: #338cd0; }
.aero-menu-side button { background: transparent; border: 1px solid transparent; color: #194467; box-shadow: none; }
.aero-menu-side button:hover { background: rgba(255,255,255,.55); border-color: #74a7cb; }

/* Windows 7 Aero right notification cluster. */
.rice-status { background: rgba(255,255,255,.12); border: 1px solid rgba(245,254,255,.2); border-radius: 4px; color: #fff; padding: 4px 5px; box-shadow: inset 0 1px rgba(255,255,255,.18); }
.rice-status:hover, .rice-status:focus { background: rgba(230,250,255,.33); border-color: #e3faff; }
.rice-status label { color: #fff; font-size: 11px; }
.rice-status-summary { color: #315c7f; font-size: 11px; }
"""


def run(argv: list[str] | None = None, *, profile: str = "aero") -> int:
    from .heritage import PROFILES
    if profile not in ("aero", "windows10", *PROFILES):
        raise ValueError("Unknown RiceBowl shell profile")
    ten = profile == "windows10"
    heritage = PROFILES.get(profile)
    tiles = ten or profile == "chromeos"
    panel_height = 40 if profile == "winxp" else PANEL_HEIGHT
    if ten:
        from .ten_shell import APP_ID as TEN_APP_ID, CSS as TEN_CSS
    if heritage:
        from .heritage_shell import CSS as HERITAGE_CSS
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

    from .aero_layout import actual_popup_y
    from .aero_windows import create_window_tracker, toggle_window_id
    from .installer import project_root

    class AeroShell(Gtk.Application):
        def __init__(self):
            app_id = (TEN_APP_ID if ten else
                      f"io.github.copypasteuser.RiceHub.{profile.title()}Shell" if heritage else APP_ID)
            super().__init__(application_id=app_id,
                             flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
            self.bar = None
            self.menu = None
            self.apps = ()
            self.window_buttons = {}
            self._visible_window_ids = ()
            self._overflow_windows = ()
            self._menu_focused = False
            self._tray = None
            self._status_pending = False
            self._status_widgets = {}
            self._last_status = None
            self._volume_programmatic = False
            self._volume_write_source = 0
            self._volume_writing = False
            self._volume_queued = None
            self._mute_writing = False
            self._pin_count = 0
            self._pinned_ids = ()
            self._pin_config_path = pin_file("windows10" if ten else profile)
            self._task_capacity = 0
            self.show_desktop_button = None
            self._app_page_size = 24
            self._smoke = False
            self._smoke_failed = False
            self._capture_gallery = False
            self._capture_variant = ""
            self._popup_hide_sources = {"menu": 0, "control": 0}

        def do_startup(self):
            Gtk.Application.do_startup(self)
            for name in ("toggle-menu", "toggle-control"):
                action = Gio.SimpleAction.new(name, None)
                action.connect("activate", self._on_fast_action, name)
                self.add_action(action)

        def _on_fast_action(self, _action, _parameter, name):
            self._remote_toggle(name)

        def _remote_toggle(self, name):
            if self.bar is None:
                self.activate()
            if name == "toggle-control":
                self._toggle_actions()
            else:
                self._toggle_menu()

        def do_command_line(self, command_line):
            args = command_line.get_arguments()
            if "--quit" in args:
                if self.bar is not None:
                    self.quit()
                return 0
            if "--toggle-menu" in args or "--control" in args or (ten and "--actions" in args):
                self._remote_toggle("toggle-control" if "--control" in args or (ten and "--actions" in args)
                                    else "toggle-menu")
                return 0
            self._smoke = "--smoke-test" in args
            self._capture_gallery = "--capture-gallery" in args
            self._capture_variant = "-1024" if (
                profile == "winxp" and os.environ.get("RICEBOWL_CAPTURE_SIZE") == "1024") else ""
            self.activate()
            if self._smoke:
                GLib.timeout_add(850, self._smoke_check)
            if self._capture_gallery:
                GLib.timeout_add(950, self._capture_start)
            return 0

        def do_activate(self):
            if self.bar is not None:
                self._toggle_menu()
                return
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS + (TEN_CSS if ten else HERITAGE_CSS[profile] if heritage else b""))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            self._provider = provider
            self.apps = app_catalog(Gio)
            try:
                saved = load_pins(self._pin_config_path)
            except (PinConfigError, OSError) as exc:
                logging.getLogger(__name__).warning("Aero pins are unavailable: %s", exc)
                saved = None
            self._pinned_ids = default_pins(self.apps) if saved is None else saved
            if self._capture_gallery:
                self._capture_background()
            self._create_taskbar()
            self._create_menu()
            self._create_actions()
            self.connect("shutdown", self._shutdown)
            self._window_tracker = create_window_tracker(GLib.idle_add, self._windows_changed)
            if self.show_desktop_button is not None:
                self.show_desktop_button.set_sensitive(self._window_tracker is not None)
            screen = Gdk.Screen.get_default()
            screen.connect("monitors-changed", self._screen_changed)
            screen.connect("size-changed", self._screen_changed)
            self._catalog_monitor = Gio.AppInfoMonitor.get()
            self._catalog_monitor.connect("changed", self._catalog_changed)

        def _publish_ready(self, *_args):
            """Expose readiness on D-Bus only when GTK maps the actual taskbar."""
            if self.lookup_action("ricebowl-ready") is None:
                self.add_action(Gio.SimpleAction.new("ricebowl-ready", None))
            return False

        def _smoke_check(self):
            """Exercise actual GTK construction, menu open/search and close under Xvfb."""
            try:
                assert self.bar is not None and self.bar.get_visible()
                assert self.menu is not None and not self.menu.get_visible()
                self._toggle_menu()
                assert self.menu.get_visible()
                self.search.set_text("unlikely-app-id-ricehub-smoke-39083")
                assert self.results.get_children()
                self._hide_menu()
                assert not self.menu.get_visible()
                assert self.lookup_action("toggle-menu") is not None
                assert self.lookup_action("toggle-control") is not None
                self.lookup_action("toggle-menu").activate(None)
                assert self.menu.get_visible()
                self.lookup_action("toggle-menu").activate(None)
                assert not self.menu.get_visible()
                self._toggle_actions()
                assert self.actions.get_visible()
                self._toggle_actions()
                assert not self.actions.get_visible()
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _capture_background(self):
            """A disposable wallpaper fixture for virtual-X11 screenshots only."""
            rect = self._desktop_rect()
            fixture = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            fixture.set_title("Virtual XFCE wallpaper fixture")
            fixture.set_decorated(False)
            fixture.set_skip_taskbar_hint(True)
            fixture.set_skip_pager_hint(True)
            fixture.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
            fixture.set_keep_below(True)
            image = project_root() / "assets/wallpapers" / (heritage.wallpaper if heritage else "ten-blue.jpg" if ten else "aero-cascade.jpg")
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(image), rect.width, rect.height, False)
            fixture.add(Gtk.Image.new_from_pixbuf(pixbuf))
            fixture.set_default_size(rect.width, rect.height)
            fixture.move(rect.x, rect.y)
            fixture.show_all()
            fixture.get_window().lower()
            self._capture_fixture = fixture

        def _capture_start(self):
            try:
                self._toggle_menu()
                assert self.menu.get_visible()
                GLib.timeout_add(450, self._capture_menu)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_screen(self, name):
            root = Gdk.get_default_root_window()
            bounds = root.get_geometry()
            pixels = Gdk.pixbuf_get_from_window(root, 0, 0, bounds.width, bounds.height)
            if pixels is None:
                raise RuntimeError("Virtual X11 screen could not be captured")
            destination = project_root() / "screenshots" / name
            pixels.savev(str(destination), "png", [], [])

        def _capture_menu(self):
            try:
                self._assert_popup_on_monitor(self.menu)
                self._capture_screen(f"ricebowl-{profile}-start-0.9.1{self._capture_variant}.png")
                self._hide_menu()
                self._toggle_actions()
                assert self.actions.get_visible()
                GLib.timeout_add(400, self._capture_actions)
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
                self.quit()
            return False

        def _capture_actions(self):
            try:
                self._assert_popup_on_monitor(self.actions)
                self._capture_screen(f"ricebowl-{profile}-controls-0.9.1{self._capture_variant}.png")
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _assert_popup_on_monitor(self, popup):
            """An on-screen image is insufficient if its controls overlap the bar."""
            rect = self._desktop_rect()
            actual_w, actual_h = popup.get_size()
            actual_x, actual_y = popup.get_window().get_root_origin()
            if not (rect.x <= actual_x and rect.y <= actual_y and
                    actual_x + actual_w <= rect.x + rect.width and
                    actual_y + actual_h <= rect.y + rect.height - panel_height):
                raise AssertionError(
                    f"{profile} popup outside usable monitor: "
                    f"{actual_x},{actual_y} {actual_w}x{actual_h}, "
                    f"monitor={rect.x},{rect.y} {rect.width}x{rect.height}")

        def _shutdown(self, *_args):
            for name in self._popup_hide_sources:
                self._cancel_popup_hide(name)
            if self._tray is not None:
                self._tray.close()
                self._tray = None
            if hasattr(self, "actions"):
                self.actions.destroy()

        def _screen_changed(self, *_args):
            rect = self._desktop_rect()
            self.bar.resize(rect.width, panel_height)
            self.bar.move(rect.x, rect.y + rect.height - panel_height)
            if self.bar.get_realized():
                self._reserve_workarea(self.bar)
            self._task_capacity = task_capacity(rect.width, self._pin_count, 340 if tiles else 185)
            if self._window_tracker is not None:
                self._window_tracker.refresh()
            if self.menu.get_visible():
                self._hide_menu()
            if self.actions.get_visible():
                self._hide_actions()

        def _render_pins(self):
            for child in self.pinned_box.get_children():
                self.pinned_box.remove(child)
            by_id = {app.get_id(): app for app in self.apps if app.get_id()}
            for identifier in self._pinned_ids:
                app = by_id.get(identifier)
                if app is None:
                    continue
                btn = self._class(Gtk.Button(), "aero-pin")
                icon = app.get_icon()
                btn.set_image(Gtk.Image.new_from_gicon(icon, Gtk.IconSize.LARGE_TOOLBAR) if icon else
                              self._icon("application-x-executable"))
                name = app.get_display_name() or app.get_name() or identifier
                btn.set_tooltip_text(name)
                btn.get_accessible().set_name("Launch " + name)
                btn.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                btn.connect("button-press-event", lambda widget, event, selected=app:
                            self._pin_context(widget, selected, event))
                self.pinned_box.pack_start(btn, False, False, 0)
            self.pinned_box.show_all()

        def _pin_context(self, widget, app, event=None):
            if event is not None and event.button != 3:
                return False
            identifier = app.get_id()
            if not identifier:
                return False
            menu = Gtk.Menu()
            pinned = identifier in self._pinned_ids
            label = "Unpin from taskbar" if pinned else "Pin to taskbar"
            item = Gtk.MenuItem(label=label)
            item.set_sensitive(pinned or len(self._pinned_ids) < PIN_LIMIT)
            item.connect("activate", lambda _item: self._change_pin(identifier, not pinned))
            menu.append(item)
            menu.show_all()
            if event is not None:
                menu.popup_at_pointer(event)
            else:
                menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)
            return True

        def _change_pin(self, identifier, add):
            candidate = list(self._pinned_ids)
            if add and identifier not in candidate:
                candidate.append(identifier)
            elif not add and identifier in candidate:
                candidate.remove(identifier)
            else:
                return
            try:
                save_pins(self._pin_config_path, candidate)
            except (PinConfigError, OSError) as exc:
                self._error("Unable to save taskbar pins: " + str(exc))
                return
            self._pinned_ids = tuple(candidate)
            self._render_pins()
            if tiles:
                self._render_ten_tiles()
            self._pin_count = len(candidate)
            self._task_capacity = task_capacity(self._desktop_rect().width, self._pin_count,
                                                340 if tiles else 185)
            if self._window_tracker is not None:
                self._window_tracker.refresh()

        def _reserve_workarea(self, widget, *_args):
            """Reserve the bottom strip on X11, but never change XFCE panel settings."""
            option = "RICEHUB_TEN_RESERVE" if ten else f"RICEHUB_{profile.upper()}_RESERVE"
            if os.environ.get(option, "1") == "0":
                return
            try:
                gi.require_version("GdkX11", "3.0")
                from gi.repository import GdkX11
                rect = self._desktop_rect()
                props = bottom_strut(rect.x, rect.y, rect.width, rect.height,
                                     Gdk.Screen.get_default().get_height(), panel_height)
                library = ctypes.util.find_library("X11")
                if not library:
                    return
                lib = ctypes.CDLL(library)
                lib.XOpenDisplay.restype = ctypes.c_void_p
                lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
                lib.XInternAtom.restype = ctypes.c_ulong
                lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
                lib.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                                ctypes.c_ulong, ctypes.c_int, ctypes.c_int,
                                                ctypes.c_void_p, ctypes.c_int]
                lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
                lib.XFlush.argtypes = [ctypes.c_void_p]
                display = lib.XOpenDisplay(None)
                if not display:
                    return
                try:
                    xid = GdkX11.X11Window.get_xid(widget.get_window())
                    cardinal = lib.XInternAtom(display, b"CARDINAL", 0)
                    for name, values in zip(("_NET_WM_STRUT", "_NET_WM_STRUT_PARTIAL"), props):
                        atom = lib.XInternAtom(display, name.encode("ascii"), 0)
                        data = (ctypes.c_ulong * len(values))(*values)
                        lib.XChangeProperty(display, xid, atom, cardinal, 32, 0, data, len(values))
                    lib.XFlush(display)
                finally:
                    lib.XCloseDisplay(display)
            except (OSError, AttributeError, RuntimeError, TypeError, ValueError) as exc:
                logging.getLogger(__name__).warning("RiceBowl workarea reservation unavailable: %s", exc)

        def _open_tool(self, command):
            """Open a known XFCE utility without a shell or implicit system changes."""
            allowed = ("xfce4-settings-manager", "xfce4-session-logout",
                       "nm-connection-editor", "pavucontrol", "xfce4-display-settings",
                       "blueman-manager", "xfce4-appearance-settings",
                       "xfce4-power-manager-settings", "system-config-printer")
            if command not in allowed:
                return
            executable = shutil.which(command)
            if not executable:
                self._error(command + " is not installed.")
                return
            try:
                subprocess.Popen([executable], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
                self._hide_menu()
            except OSError as exc:
                self._error(str(exc))

        def _show_desktop(self, *_args):
            if self._window_tracker is not None:
                screen = self._window_tracker.screen
                screen.toggle_showing_desktop(not screen.get_showing_desktop())
                self._hide_menu()

        def _catalog_changed(self, *_args):
            self.apps = app_catalog(Gio)
            self._render_pins()
            self._populate(self.search.get_text())
            if tiles:
                self._render_ten_tiles()

        def _class(self, widget, name):
            widget.get_style_context().add_class(name)
            return widget

        def _desktop_rect(self):
            screen = Gdk.Screen.get_default()
            monitor = screen.get_primary_monitor()
            return screen.get_monitor_geometry(monitor if monitor >= 0 else 0)

        def _icon(self, name, size=Gtk.IconSize.LARGE_TOOLBAR):
            return Gtk.Image.new_from_icon_name(name, size)

        def _set_status_icon(self, image, kind):
            """Use Rice-specific vector artwork, with a GTK icon fallback."""
            path = project_root() / "assets/status" / profile / (kind + ".svg")
            fallback = ("audio-volume-muted" if kind == "muted" else
                        "audio-volume-high" if kind == "sound" else
                        "network-wireless" if kind == "wifi" else
                        "network-wired" if kind == "ethernet" else
                        "network-offline" if kind == "offline" else
                        "battery-good-symbolic")
            try:
                image.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(path), 20, 20, True))
            except (GLib.Error, OSError):
                image.set_from_icon_name(fallback, Gtk.IconSize.MENU)

        def _status_action(self, name):
            """Open usable controls for audio/power; network settings for Wi-Fi."""
            if name in ("audio", "battery"):
                self._toggle_actions()
                return
            options = {
                "network": ("nm-connection-editor", "xfce4-settings-manager"),
                "audio": ("pavucontrol", "xfce4-settings-manager"),
                "battery": ("xfce4-power-manager-settings", "xfce4-settings-manager"),
            }[name]
            for candidate in options:
                if shutil.which(candidate):
                    self._open_tool(candidate)
                    return
            self._error("No suitable " + name + " settings application was found.")

        def _install_status_widgets(self, row):
            for name in ("battery", "network", "audio"):
                button = self._class(Gtk.Button(), "rice-status")
                button.get_style_context().add_class("rice-status-" + name)
                contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
                image = Gtk.Image()
                contents.pack_start(image, False, False, 0)
                label = Gtk.Label()
                contents.pack_start(label, False, False, 0)
                button.add(contents)
                button.get_accessible().set_name(name.capitalize() + " status")
                button.connect("clicked", lambda _button, selected=name:
                               self._status_action(selected))
                row.pack_end(button, False, False, 0)
                self._status_widgets[name] = (button, image, label)
            self._refresh_status_async()
            GLib.timeout_add_seconds(20, self._refresh_status_async)

        def _refresh_status_async(self):
            if self._status_pending:
                return True
            self._status_pending = True
            def worker():
                try:
                    from .hardware_status import read_status
                    status = read_status()
                except Exception as exc:
                    logging.getLogger(__name__).warning("Hardware status probe failed: %s", exc)
                    status = None
                GLib.idle_add(self._apply_status, status)
            threading.Thread(target=worker, name="ricebowl-status", daemon=True).start()
            return True

        def _apply_status(self, status):
            self._status_pending = False
            if status is None:
                for button, _image, _label in self._status_widgets.values():
                    button.set_sensitive(False)
                    button.set_tooltip_text("Hardware status temporarily unavailable")
                return False
            self._last_status = status
            if hasattr(self, "control_network_label"):
                self.control_network_label.set_text(
                    "Network: " + {"wifi": "Wi-Fi", "ethernet": "Ethernet",
                                   "offline": "No active route"}[status.network])
                battery = status.battery
                self.control_battery_label.set_text(
                    f"Battery: {battery.percent}% — {battery.label}" if battery else
                    "Battery: not detected")
                if battery:
                    self.control_battery_level.set_value(battery.percent)
                    self.control_battery_level.show()
                else:
                    self.control_battery_level.hide()
                if status.sound.muted is not None and not self._mute_writing:
                    self.mute_button.set_sensitive(True)
                    self.mute_button.set_active(status.sound.muted)
                elif status.sound.muted is None:
                    self.mute_button.set_sensitive(False)
                if status.sound.percent is not None:
                    self.volume_scale.set_sensitive(True)
                    self.volume_status_label.set_text(
                        f"Volume: {status.sound.percent}%"
                        + (" (muted)" if status.sound.muted else ""))
                    if not self._volume_writing and self._volume_queued is None:
                        self._volume_programmatic = True
                        try:
                            self.volume_scale.set_value(
                                min(100, status.sound.percent))
                        finally:
                            self._volume_programmatic = False
                else:
                    self.volume_scale.set_sensitive(False)
                    self.volume_status_label.set_text(
                        "Volume backend unavailable")
            battery_button, battery_icon, battery_label = self._status_widgets["battery"]
            battery = status.battery
            if battery is None:
                battery_button.hide()
            else:
                battery_button.show_all()
                level = min(100, (battery.percent + 12) // 25 * 25)
                self._set_status_icon(battery_icon, "battery-charging" if battery.charging
                                      else "battery-" + str(level))
                battery_label.set_text(str(battery.percent) + "%")
                battery_button.set_sensitive(True)
                battery_button.set_tooltip_text(
                    f"Battery {battery.percent}% — {battery.label}. Open power settings")
                battery_button.get_accessible().set_name(
                    f"Battery {battery.percent} percent, {battery.label}")
            network_button, network_icon, network_label = self._status_widgets["network"]
            self._set_status_icon(network_icon, status.network)
            network_label.set_text("" if profile != "chromeos" else
                                   "Wi-Fi" if status.network == "wifi" else
                                   "LAN" if status.network == "ethernet" else "Offline")
            network_button.set_tooltip_text({
                "wifi": "Wi-Fi is the default route; open network settings",
                "ethernet": "Ethernet / other default route; open network settings",
                "offline": "No IPv4 default route; open network settings",
            }[status.network])
            network_button.get_accessible().set_name("Network " + status.network)
            sound_button, sound_icon, sound_label = self._status_widgets["audio"]
            sound = status.sound
            self._set_status_icon(sound_icon, "muted" if sound.muted else "sound")
            sound_label.set_text("" if sound.percent is None or profile != "chromeos"
                                 else str(sound.percent) + "%")
            sound_button.set_tooltip_text(
                "Volume unknown; open sound settings" if sound.percent is None else
                f"Audio {sound.percent}% — {'muted' if sound.muted else 'unmuted'}; open sound settings")
            sound_button.get_accessible().set_name(
                "Audio status unknown" if sound.percent is None else
                f"Audio {sound.percent} percent" + (", muted" if sound.muted else ""))
            if hasattr(self, "status_summary"):
                self.status_summary.set_text(
                    ("Battery " + str(battery.percent) + "% · " if battery else "") +
                    status.network.upper() + " · " +
                    ("Audio unavailable" if sound.percent is None else
                     "Audio " + str(sound.percent) + "%"))
            return False

        def _queue_volume_change(self, slider):
            if self._volume_programmatic:
                return
            self._volume_queued = int(round(slider.get_value()))
            if self._volume_write_source:
                GLib.source_remove(self._volume_write_source)
            self._volume_write_source = GLib.timeout_add(
                260, self._commit_volume_change)

        def _commit_volume_change(self):
            self._volume_write_source = 0
            if self._volume_writing or self._volume_queued is None:
                return False
            value = self._volume_queued
            self._volume_queued = None
            self._volume_writing = True
            self.volume_status_label.set_text(f"Adjusting volume to {value}%…")
            def worker():
                from .hardware_status import set_sound_volume
                try:
                    state = set_sound_volume(value)
                    error = None
                except (OSError, RuntimeError, ValueError) as exc:
                    state, error = None, str(exc)
                GLib.idle_add(self._volume_change_complete, state, error)
            threading.Thread(target=worker, daemon=True,
                             name="ricebowl-set-volume").start()
            return False

        def _volume_change_complete(self, state, error):
            self._volume_writing = False
            if error:
                self.volume_status_label.set_text("Volume unavailable — " + error)
            elif state is not None:
                self.volume_status_label.set_text(
                    f"Volume {state.percent}%"
                    + (" (muted)" if state.muted else ""))
            if self._volume_queued is not None and not self._volume_write_source:
                self._volume_write_source = GLib.timeout_add(
                    180, self._commit_volume_change)
            else:
                self._refresh_status_async()
            return False

        def _toggle_output_mute(self, button):
            if self._mute_writing or self._last_status is None:
                return
            sound = self._last_status.sound
            if sound.muted is None:
                return
            requested = bool(button.get_active())
            # GTK ToggleButton is optimistic; display the real state until
            # the backend confirms the change.
            button.set_active(sound.muted)
            button.set_sensitive(False)
            self._mute_writing = True

            def worker():
                from .hardware_status import set_sound_mute
                try:
                    state = set_sound_mute(requested)
                    error = None
                except (OSError, ValueError, RuntimeError) as exc:
                    state, error = None, str(exc)
                GLib.idle_add(self._mute_change_complete, state, error)

            threading.Thread(target=worker, daemon=True,
                             name="ricebowl-set-mute").start()

        def _mute_change_complete(self, state, error):
            self._mute_writing = False
            if error:
                self.volume_status_label.set_text("Mute action failed: " + error)
            else:
                self.mute_button.set_active(bool(state.muted))
                self.volume_status_label.set_text(
                    "Audio muted" if state.muted else "Audio unmuted")
            self._refresh_status_async()
            return False

        def _create_taskbar(self):
            rect = self._desktop_rect()
            win = Gtk.ApplicationWindow(application=self)
            win.set_title("RiceBowl Windows 10 Taskbar" if ten else
                          f"RiceBowl {heritage.name} Taskbar" if heritage else "RiceBowl Aero Taskbar")
            win.set_decorated(False)
            win.set_resizable(False)
            win.set_skip_taskbar_hint(True)
            win.set_skip_pager_hint(True)
            win.set_type_hint(Gdk.WindowTypeHint.DOCK)
            win.set_keep_above(True)
            win.set_accept_focus(False)
            win.set_default_size(rect.width, panel_height)
            win.move(rect.x, rect.y + rect.height - panel_height)

            row = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                      spacing=4 if profile == "winxp" else 8), "aero-taskbar")
            if not ten and os.environ.get("RICEHUB_AERO_GLASS") == "1":
                row.get_style_context().add_class("aero-glass")
            start = self._class(Gtk.Button(), "aero-start")
            contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            logo = project_root() / ("assets/ten-start.svg" if ten else
                                     "assets/" + heritage.logo if heritage else "assets/aero-penguin.svg")
            try:
                img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo), 26 if ten or profile == "winxp" else 34,
                    26 if ten or profile == "winxp" else 34, True))
            except (GLib.Error, OSError):
                img = self._icon("start-here", Gtk.IconSize.LARGE_TOOLBAR)
            contents.pack_start(img, False, False, 0)
            if not ten and profile != "chromeos":
                contents.pack_start(Gtk.Label(label=heritage.start_label if heritage else "Start"), False, False, 0)
            start.add(contents)
            start.get_accessible().set_name("Toggle " + (heritage.name if heritage else
                "Windows 10" if ten else "Aero") + " application menu")
            start.connect("clicked", lambda _button: self._toggle_menu())
            row.pack_start(start, False, False, 0 if profile == "winxp" else 4)
            if profile == "chromeos":
                # Three independent visual zones: launcher, centered shelf,
                # and the device-status pill at the far right.
                row.pack_start(Gtk.Box(), True, True, 0)
                shelf_box = self._class(
                    Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
                    "chrome-app-shelf")
                row.pack_start(shelf_box, False, False, 0)
            else:
                shelf_box = row
            self.start_button = start
            if ten:
                search_button = self._class(Gtk.Button(label="⌕  Type here to search"), "ten-search")
                search_button.get_accessible().set_name("Search installed applications")
                search_button.connect("clicked", lambda _button: self._open_search())
                if rect.width < 940:
                    search_button.set_label("⌕")
                row.pack_start(search_button, False, False, 0)
            self.pinned_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            shelf_box.pack_start(self.pinned_box, False, False, 0)
            self._render_pins()
            self._pin_count = len(self._pinned_ids)
            self.tasks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            self._task_capacity = task_capacity(rect.width, self._pin_count, 340 if tiles else 185)
            self.overflow_button = self._class(Gtk.Button(), "aero-task-overflow")
            self.overflow_button.get_accessible().set_name("Show other running windows")
            self.overflow_button.connect("clicked", self._show_overflow)
            shelf_box.pack_start(self.tasks, False, False, 4)
            row.pack_start(Gtk.Box(), True, True, 0)
            right_area = row
            if profile in ("chromeos", "winxp"):
                right_area = self._class(
                    Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5),
                    "chrome-status-pill" if profile == "chromeos" else "luna-tray")
                row.pack_end(right_area, False, False, 0 if profile == "winxp" else 4)
            desktop = self._class(Gtk.Button(), "aero-desktop")
            desktop.set_tooltip_text("Show desktop / restore windows")
            desktop.get_accessible().set_name("Show desktop or restore windows")
            desktop.connect("clicked", self._show_desktop)
            right_area.pack_end(desktop, False, False, 0)
            self.show_desktop_button = desktop
            clock = self._class(Gtk.Label(), "aero-time")
            clock.set_justify(Gtk.Justification.CENTER)
            right_area.pack_end(clock, False, False, 6)
            if tiles:
                action = self._class(Gtk.Button(label="▤"), "aero-quick")
                action.get_accessible().set_name("Toggle " + (heritage.control_heading if heritage else "Windows 10 Action Center"))
                action.set_tooltip_text("Quick settings and notification information")
                action.connect("clicked", lambda _button: self._toggle_actions())
                right_area.pack_end(action, False, False, 0)
            else:
                control = self._class(Gtk.Button(), "aero-quick")
                control.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
                control.set_tooltip_text("Control Panel")
                control.get_accessible().set_name("Toggle " + (heritage.control_heading if heritage else "Windows 7 Control Panel"))
                control.connect("clicked", lambda _button: self._toggle_actions())
                right_area.pack_end(control, False, False, 0)
            self._install_status_widgets(right_area)
            tray_option = "RICEHUB_TEN_TRAY" if ten else f"RICEHUB_{profile.upper()}_TRAY"
            if os.environ.get(tray_option, "1") != "0":
                tray_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                right_area.pack_end(tray_box, False, False, 4)
                try:
                    from .aero_tray import StatusNotifierTray
                    self._tray = StatusNotifierTray(tray_box, Gtk, Gio, GLib, GdkPixbuf)
                except (GLib.Error, RuntimeError, OSError) as exc:
                    logging.getLogger(__name__).warning("Optional Aero tray unavailable: %s", exc)
            def update_clock():
                clock.set_text(GLib.DateTime.new_now_local().format(
                    "%H:%M" if profile == "winxp" else
                    "%H:%M\n%d %b" if not ten else "%H:%M\n%d/%m/%Y"))
                if profile == "winxp":
                    clock.set_tooltip_text(GLib.DateTime.new_now_local().format("%A, %d %B %Y"))
                return True
            update_clock()
            GLib.timeout_add_seconds(30, update_clock)
            win.add(row)
            win.connect("realize", self._reserve_workarea)
            win.connect("map-event", self._publish_ready)
            win.show_all()
            win.move(rect.x, rect.y + rect.height - panel_height)
            self.bar = win

        def _windows_changed(self, windows, active):
            """Render copied task data without retaining native WnckWindow objects."""
            visible, self._overflow_windows = select_windows(tuple(windows), active, self._task_capacity)
            visible_ids = tuple(window.xid for window in visible)
            if visible_ids != self._visible_window_ids:
                for child in self.tasks.get_children():
                    self.tasks.remove(child)
                previous = self.window_buttons
                self.window_buttons = {}
                for window in visible:
                    xid = window.xid
                    if xid in previous:
                        button, icon, label = previous[xid]
                    else:
                        button = self._class(Gtk.Button(), "aero-task")
                        button.set_size_request(42 if profile == "chromeos" else 135, 35)
                        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                        label = Gtk.Label(xalign=0)
                        label.set_max_width_chars(12)
                        label.set_ellipsize(Pango.EllipsizeMode.END)
                        if profile == "chromeos":
                            label.set_no_show_all(True)
                            label.hide()
                        content.pack_start(icon, False, False, 0)
                        content.pack_start(label, True, True, 0)
                        button.add(content)
                        button.connect("clicked", lambda _btn, target=xid: self._activate_task(target))
                    self.window_buttons[xid] = (button, icon, label)
                    self.tasks.pack_start(button, False, False, 0)
                self._visible_window_ids = visible_ids
            for window in visible:
                button, icon, label = self.window_buttons[window.xid]
                title = window.title
                if label.get_text() != title:
                    label.set_text(title)
                    button.set_tooltip_text(title)
                    button.get_accessible().set_name("Switch to " + title)
                pixbuf = window.mini_icon
                if pixbuf is not None:
                    icon.set_from_pixbuf(pixbuf)
                context = button.get_style_context()
                if window == active and not window.minimized:
                    context.add_class("aero-task-active")
                else:
                    context.remove_class("aero-task-active")
            if self._overflow_windows:
                self.overflow_button.set_label(f"+{len(self._overflow_windows)}")
                if self.overflow_button.get_parent() is None:
                    self.tasks.pack_start(self.overflow_button, False, False, 0)
            elif self.overflow_button.get_parent() is self.tasks:
                self.tasks.remove(self.overflow_button)
            self.tasks.show_all()

        def _activate_task(self, xid):
            if self._window_tracker:
                # Resolve a live object only for this click; never capture it in
                # a button closure after the application window is closed.
                toggle_window_id(self._window_tracker.wnck, self._window_tracker.screen,
                                 xid, Gtk.get_current_event_time())
            self._hide_menu()

        def _show_overflow(self, button):
            menu = Gtk.Menu()
            for window in self._overflow_windows:
                item = Gtk.MenuItem(label=window.title)
                item.connect("activate", lambda _item, target=window.xid: self._activate_task(target))
                menu.append(item)
            menu.show_all()
            menu.popup_at_widget(button, Gdk.Gravity.NORTH_WEST, Gdk.Gravity.SOUTH_WEST, None)

        def _create_menu(self):
            if profile == "winxp":
                self._create_luna_menu()
                return
            if profile == "winclassic":
                self._create_classic_menu()
                return
            if profile == "frutiger":
                self._create_frutiger_menu()
                return
            if tiles:
                self._create_ten_menu()
                return
            classic = profile == "winclassic"
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl " + (heritage.name if heritage else "Aero") + " Start")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _, _, menu_w, menu_h = menu_geometry(rect.x, rect.y, rect.width, rect.height,
                                                 preferred_width=355 if classic else 490,
                                                 preferred_height=465 if classic else 505)
            menu.set_default_size(menu_w, menu_h)
            body = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "aero-menu-root")
            if classic:
                # Unlike Luna's two-column Start menu, Windows 98/2000 used
                # a narrow program list with a vertical branded side rail.
                badge = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "classic-brand")
                badge.set_size_request(38, -1)
                brand = self._class(Gtk.Label(label="RiceBowl   98 / 2000"), "classic-brand-label")
                brand.set_angle(90)
                badge.pack_end(brand, False, False, 18)
                body.pack_start(badge, False, False, 0)
            main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7 if classic else 10)
            main.set_margin_start(8 if classic else 14)
            main.set_margin_top(8 if classic else 14)
            main.set_margin_bottom(8 if classic else 10)
            main.set_margin_end(8 if classic else 10)
            main.set_size_request(min(310, max(150, menu_w - (60 if classic else 36))), -1)
            main.pack_start(self._class(Gtk.Label(label=heritage.menu_heading if heritage else "Programs", xalign=0), "aero-menu-heading"), False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search programs")
            search.get_accessible().set_name("Search installed programs")
            main.pack_start(search, False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(max(85, min(340, menu_h - 160)))
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            scroller.add(self.results)
            main.pack_start(scroller, True, True, 0)
            body.pack_start(main, True, True, 0)
            if not classic:
                side = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12), "aero-menu-side")
                try:
                    logo = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(project_root() / "assets/aero-penguin.svg"), 70, 70, True))
                except (GLib.Error, OSError):
                    logo = self._icon("start-here", Gtk.IconSize.DIALOG)
                side.pack_start(logo, False, False, 0)
                for title, icon, uri in (
                    ("Home", "user-home", Path.home().as_uri()),
                    ("Computer", "computer", "file:///"),
                    ("Documents", "folder-documents", (Path.home() / "Documents").as_uri()),
                ):
                    btn = self._class(Gtk.Button(label=title), "aero-menu-app")
                    btn.set_image(self._icon(icon, Gtk.IconSize.MENU))
                    btn.set_always_show_image(True)
                    btn.connect("clicked", lambda _btn, address=uri: self._open_uri(address))
                    side.pack_start(btn, False, False, 0)
                if menu_w >= 470:
                    body.pack_start(side, False, False, 0)
            footer = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8), "aero-menu-footer")
            footer.set_margin_top(6)
            if shutil.which("xfce4-settings-manager"):
                settings = self._class(Gtk.Button(label="Control Panel"), "aero-menu-app")
                settings.connect("clicked", lambda _btn: self._open_tool("xfce4-settings-manager"))
                footer.pack_start(settings, True, True, 0)
            if shutil.which("xfce4-session-logout"):
                power = self._class(Gtk.Button(label="Shut down…" if classic else "Log off…"), "aero-menu-power")
                power.set_tooltip_text("Open XFCE's session dialog; no immediate logout")
                power.connect("clicked", lambda _btn: self._open_tool("xfce4-session-logout"))
                footer.pack_end(power, False, False, 0)
            main.pack_end(footer, False, False, 0)
            menu.add(body)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            def update_search(*_args):
                self._app_page_size = 24
                self._populate(search.get_text())
            search.connect("search-changed", update_search)
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu = menu
            self.search = search
            self._populate("")

        def _place_button(self, title, icon_name, path, css_class="rice-place"):
            """Use real XDG folders, never a placeholder filesystem action."""
            button = self._class(Gtk.Button(), css_class)
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            content.pack_start(self._icon(icon_name, Gtk.IconSize.MENU), False, False, 0)
            content.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
            button.add(content)
            button.get_accessible().set_name("Open " + title)
            exists = path.is_dir()
            button.set_sensitive(exists)
            button.set_tooltip_text("Open " + str(path) if exists else
                                    "Folder does not exist: " + str(path))
            button.connect("clicked", lambda _button, target=path:
                           self._open_uri(target.as_uri()))
            return button

        def _finish_heritage_menu(self, menu, search):
            """Same keyboard, focus and installed-app lifecycle for each identity."""
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            def changed(*_args):
                self._app_page_size = 24
                self._populate(search.get_text())
            search.connect("search-changed", changed)
            self.menu, self.search = menu, search
            self._populate("")

        def _programs_cascade(self, reveal_search):
            """One real .desktop category flyout for XP and Classic, no fake items."""
            groups = (
                ("Accessories", ("Utility", "Accessories", "TextEditor")),
                ("Games", ("Game",)),
                ("Graphics", ("Graphics", "Photography")),
                ("Internet", ("Network", "WebBrowser", "Email")),
                ("Multimedia", ("Audio", "Video", "Player")),
                ("Office", ("Office", "Spreadsheet", "WordProcessor")),
                ("System Tools", ("System", "Settings", "FileManager", "Terminal")),
            )
            programs_menu = Gtk.Menu()
            for title, categories in groups:
                submenu = Gtk.Menu()
                count = 0
                for app in self.apps:
                    classifier = getattr(app, "get_categories", None)
                    names = (classifier() or "").split(";") if callable(classifier) else []
                    if not any(category in names for category in categories):
                        continue
                    item = Gtk.MenuItem(label=app.get_display_name() or app.get_name())
                    item.connect("activate", lambda _item, selected=app: self._launch(selected))
                    submenu.append(item)
                    count += 1
                    if count >= 20:
                        break
                if count:
                    parent = Gtk.MenuItem(label=title)
                    parent.set_submenu(submenu)
                    programs_menu.append(parent)
            if programs_menu.get_children():
                programs_menu.append(Gtk.SeparatorMenuItem())
            all_item = Gtk.MenuItem(label="Search all installed programs…")
            all_item.connect("activate", lambda *_args: reveal_search())
            programs_menu.append(all_item)
            programs_menu.show_all()
            return programs_menu

        def _luna_navigation(self, label, icon_name, *, path=None, command=None, callback=None):
            """XP right-column link; never enable unavailable system operations."""
            button = self._class(Gtk.Button(), "luna-place")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            row.pack_start(self._icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
            row.pack_start(Gtk.Label(label=label, xalign=0), True, True, 0)
            button.add(row)
            button.get_accessible().set_name(label)
            if path is not None:
                button.set_sensitive(path.is_dir())
                button.set_tooltip_text("Open " + str(path) if path.is_dir() else
                                        "Folder not available: " + str(path))
                button.connect("clicked", lambda _button: self._open_uri(path.as_uri()))
            elif command is not None:
                candidates = (command,) if isinstance(command, str) else command
                installed = next((name for name in candidates if shutil.which(name)), None)
                button.set_sensitive(installed is not None)
                button.set_tooltip_text("Open " + label if installed else
                                        "Requires " + " or ".join(candidates))
                if installed:
                    button.connect("clicked", lambda _button, executable=installed:
                                   self._open_tool(executable))
            elif callback is not None:
                button.connect("clicked", lambda _button: callback())
            return button

        def _luna_recent_documents(self):
            """Real XDG recent files, only when GTK knows about them."""
            button = self._class(Gtk.MenuButton(label="My Recent Documents   ▸"), "luna-place")
            button.get_accessible().set_name("Recent documents")
            menu = Gtk.Menu()
            try:
                items = (item for item in Gtk.RecentManager.get_default().get_items()
                         if item.exists() and item.get_uri().startswith("file:"))
                for item in list(items)[:10]:
                    entry = Gtk.MenuItem(label=item.get_display_name())
                    entry.connect("activate", lambda _entry, uri=item.get_uri():
                                  self._open_uri(uri))
                    menu.append(entry)
            except (GLib.Error, OSError) as exc:
                logging.getLogger(__name__).debug("Recent documents unavailable: %s", exc)
            if not menu.get_children():
                entry = Gtk.MenuItem(label="No recent documents")
                entry.set_sensitive(False)
                menu.append(entry)
            menu.show_all()
            button.set_popup(menu)
            return button

        def _reveal_luna_search(self):
            self.search.set_no_show_all(False)
            self.search.show()
            self.search.grab_focus()

        def _create_luna_menu(self):
            """XP Luna: blue user band, ivory apps list, blue places and power footer."""
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl XP Luna Start")
            menu.set_decorated(False)
            # GTK's natural height may exceed the requested menu height.
            # Keep the scrollable app list shrinkable and the window movable.
            menu.set_resizable(True)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            menu.set_default_size(480, 540)

            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                               "luna-menu")
            header = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10),
                                 "luna-user")
            avatar = self._class(Gtk.Image(), "luna-avatar")
            try:
                avatar.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(project_root() / "assets/ricebowl-xp-user.svg"), 44, 44, True))
            except (GLib.Error, OSError):
                avatar.set_from_icon_name("computer", Gtk.IconSize.DIALOG)
            header.pack_start(avatar, False, False, 0)
            user_label = self._class(
                Gtk.Label(label=os.environ.get("USER", "Desktop"), xalign=0),
                "luna-user-name")
            header.pack_start(user_label, True, True, 0)
            root.pack_start(header, False, False, 0)

            columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            apps = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2),
                               "luna-apps")
            apps.set_size_request(247, -1)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search programs")
            search.get_accessible().set_name("Search installed programs")
            search.set_no_show_all(True)
            apps.pack_start(search, False, False, 2)
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(140)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            scroll.add(self.results)
            apps.pack_start(scroll, True, True, 0)
            browse = self._class(Gtk.MenuButton(label="All Programs  ▸"), "luna-all-programs")
            browse.set_popup(self._programs_cascade(self._reveal_luna_search))
            browse.get_accessible().set_name("Browse all installed programs")
            apps.pack_end(browse, False, False, 3)
            columns.pack_start(apps, True, True, 0)

            places = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                                 "luna-places")
            places.set_size_request(205, -1)
            home = Path.home()
            for name, icon, folder in (
                ("My Documents", "folder-documents", home / "Documents"),
                ("My Pictures", "folder-pictures", home / "Pictures"),
                ("My Music", "folder-music", home / "Music"),
                ("My Computer", "computer", Path("/")),
            ):
                places.pack_start(self._luna_navigation(name, icon, path=folder), False, False, 0)
            places.pack_start(self._luna_recent_documents(), False, False, 0)
            places.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
            for name, icon, cmd in (
                ("Control Panel", "preferences-system", "xfce4-settings-manager"),
                ("Network Connections", "network-workgroup", "nm-connection-editor"),
                ("Printers and Faxes", "printer", "system-config-printer"),
            ):
                places.pack_start(self._luna_navigation(name, icon, command=cmd), False, False, 0)
            places.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 5)
            places.pack_start(self._luna_navigation("Help and Support", "help-browser",
                                                     command=("xfhelp4", "yelp")), False, False, 0)
            places.pack_start(self._luna_navigation("Search", "system-search",
                                                     command="catfish" if shutil.which("catfish") else None,
                                                     callback=self._reveal_luna_search), False, False, 0)
            places.pack_start(self._luna_navigation("Run…", "system-run",
                                                     command="xfce4-appfinder"), False, False, 0)
            place_scroll = Gtk.ScrolledWindow()
            place_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            place_scroll.set_min_content_height(120)
            place_scroll.set_min_content_width(205)
            place_scroll.add(places)
            columns.pack_start(place_scroll, False, False, 0)
            root.pack_start(columns, True, True, 0)

            footer = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                                 "luna-footer")
            footer.pack_start(Gtk.Box(), True, True, 0)
            for name, icon, css in (("Log Off", "system-log-out", "luna-logoff"),
                                    ("Turn Off Computer", "system-shutdown", "luna-shutdown")):
                button = self._class(Gtk.Button(label=name), "luna-power")
                button.get_style_context().add_class(css)
                button.set_image(self._icon(icon, Gtk.IconSize.MENU))
                button.set_always_show_image(True)
                button.set_tooltip_text("Open XFCE session dialog; no immediate logout")
                button.set_sensitive(shutil.which("xfce4-session-logout") is not None)
                button.connect("clicked", lambda _button:
                               self._open_tool("xfce4-session-logout"))
                footer.pack_start(button, False, False, 0)
            root.pack_end(footer, False, False, 0)
            menu.add(root)
            self._finish_heritage_menu(menu, search)

        def _create_classic_menu(self):
            """Win9x: a narrow fly-out Programs hierarchy backed by installed apps."""
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl 98 / 2000 Start")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            menu.set_default_size(285, 430)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL),
                               "classic-menu")
            rail = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "classic-brand")
            rail.set_size_request(34, -1)
            word = self._class(Gtk.Label(label="RiceBowl  98 / 2000"), "classic-brand-label")
            word.set_angle(90)
            rail.pack_end(word, False, False, 14)
            root.pack_start(rail, False, False, 0)
            main = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                               "classic-menu-list")

            programs = self._class(Gtk.MenuButton(label="Programs   ▸"), "classic-menu-item")
            programs.set_popup(self._programs_cascade(self._reveal_classic_search))
            main.pack_start(programs, False, False, 0)

            for title, icon, target in (
                ("Documents", "folder-documents", Path.home() / "Documents"),
                ("Home", "user-home", Path.home()),
                ("Computer", "computer", Path("/")),
            ):
                button = self._place_button(title + "   ▸", icon, target, "classic-menu-item")
                main.pack_start(button, False, False, 0)
            divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
            main.pack_start(divider, False, False, 4)
            tools = self._class(Gtk.Button(label="Settings   ▸"), "classic-menu-item")
            tools.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
            tools.set_always_show_image(True)
            tools.set_sensitive(shutil.which("xfce4-settings-manager") is not None)
            tools.connect("clicked", lambda _button:
                          self._open_tool("xfce4-settings-manager"))
            main.pack_start(tools, False, False, 0)

            find = self._class(Gtk.Button(label="Find…"), "classic-menu-item")
            find.set_image(self._icon("edit-find", Gtk.IconSize.MENU))
            find.set_always_show_image(True)
            find.connect("clicked", lambda *_args: self._reveal_classic_search())
            main.pack_start(find, False, False, 0)
            self.classic_search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            self.classic_search.set_placeholder_text("Find programs")
            self.classic_search.set_no_show_all(True)
            main.pack_start(self.classic_search, False, False, 3)
            self.classic_results_scroll = Gtk.ScrolledWindow()
            self.classic_results_scroll.set_policy(Gtk.PolicyType.NEVER,
                                                    Gtk.PolicyType.AUTOMATIC)
            self.classic_results_scroll.set_min_content_height(125)
            self.classic_results_scroll.set_no_show_all(True)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.classic_results_scroll.add(self.results)
            main.pack_start(self.classic_results_scroll, True, True, 0)

            footer = self._class(Gtk.Button(label="Shut Down…"), "classic-menu-item")
            footer.set_image(self._icon("system-shutdown", Gtk.IconSize.MENU))
            footer.set_always_show_image(True)
            footer.set_sensitive(shutil.which("xfce4-session-logout") is not None)
            footer.connect("clicked", lambda _button:
                           self._open_tool("xfce4-session-logout"))
            main.pack_end(footer, False, False, 3)
            root.pack_start(main, True, True, 0)
            menu.add(root)
            self._finish_heritage_menu(menu, self.classic_search)

        def _reveal_classic_search(self):
            self.classic_search.set_no_show_all(False)
            self.classic_results_scroll.set_no_show_all(False)
            self.classic_search.show()
            self.classic_results_scroll.show_all()
            self.classic_search.grab_focus()

        def _create_frutiger_menu(self):
            """An airy Y2K/Frutiger dashboard, intentionally unlike Aero Start."""
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl Frutiger Aero — Your World")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _x, _y, width, height = menu_geometry(
                rect.x, rect.y, rect.width, rect.height,
                preferred_width=535, preferred_height=540)
            menu.set_default_size(width, height)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11),
                               "aqua-dashboard")
            root.get_style_context().add_class("aero-menu-root")
            root.set_border_width(15)
            heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            mark = Gtk.Image()
            self._set_status_icon(mark, "wifi")
            heading.pack_start(mark, False, False, 0)
            heading.pack_start(self._class(
                Gtk.Label(label="Your World", xalign=0), "aero-menu-heading"),
                True, True, 0)
            gear = self._class(Gtk.Button(), "aqua-gear")
            gear.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
            gear.get_accessible().set_name("Open desktop settings")
            gear.set_tooltip_text("Desktop settings")
            gear.connect("clicked", lambda _button:
                         self._open_tool("xfce4-settings-manager"))
            heading.pack_end(gear, False, False, 0)
            root.pack_start(heading, False, False, 0)
            root.pack_start(self._class(
                Gtk.Label(label="Explore  •  Connect  •  Create", xalign=0),
                "aero-menu-sub"), False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search your applications")
            search.get_accessible().set_name("Search applications")
            root.pack_start(search, False, False, 0)
            shortcuts = Gtk.Grid(column_spacing=8, row_spacing=6)
            for i, (name, icon_name, uri) in enumerate((
                ("Home", "user-home", Path.home().as_uri()),
                ("Files", "system-file-manager", "file:///"),
                ("Documents", "folder-documents", (Path.home() / "Documents").as_uri()),
                ("Music", "folder-music", (Path.home() / "Music").as_uri()),
            )):
                button = self._class(Gtk.Button(), "aqua-shortcut")
                col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                col.pack_start(self._icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR),
                               False, False, 0)
                col.pack_start(Gtk.Label(label=name), False, False, 0)
                button.add(col)
                button.get_accessible().set_name("Open " + name)
                button.connect("clicked", lambda _button, address=uri:
                               self._open_uri(address))
                shortcuts.attach(button, i, 0, 1, 1)
            root.pack_start(shortcuts, False, False, 0)
            # Three live pages mirror the reference: Apps / Places / Settings.
            tabs = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7),
                               "aqua-tabs")
            self.aqua_stack = Gtk.Stack()
            self.aqua_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            self.aqua_stack.set_transition_duration(140)
            buttons = {}
            for name in ("Apps", "Places", "Settings"):
                button = self._class(Gtk.ToggleButton(label=name), "aqua-tab")
                button.set_hexpand(True)
                button.get_accessible().set_name("Show " + name + " page")
                tabs.pack_start(button, True, True, 0)
                buttons[name] = button
            root.pack_start(tabs, False, False, 0)
            def switch_to(name):
                self.aqua_stack.set_visible_child_name(name)
                for key, button in buttons.items():
                    button.set_active(key == name)
                if name == "Apps":
                    search.grab_focus()
            for name, button in buttons.items():
                button.connect("clicked", lambda _button, chosen=name: switch_to(chosen))

            apps_scroll = Gtk.ScrolledWindow()
            apps_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            apps_scroll.set_min_content_height(140)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            apps_scroll.add(self.results)
            self.aqua_stack.add_named(apps_scroll, "Apps")

            places_page = Gtk.ScrolledWindow()
            places_page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            places_grid = Gtk.Grid(column_spacing=9, row_spacing=8)
            places_grid.set_margin_top(7)
            places_grid.set_margin_bottom(7)
            home = Path.home()
            entries = (
                ("Home", "user-home", home),
                ("Documents", "folder-documents", home / "Documents"),
                ("Downloads", "folder-download", home / "Downloads"),
                ("Music", "folder-music", home / "Music"),
                ("Pictures", "folder-pictures", home / "Pictures"),
                ("Videos", "folder-videos", home / "Videos"),
            )
            for index, (title, icon_name, path) in enumerate(entries):
                button = self._place_button(title, icon_name, path, "aqua-place")
                places_grid.attach(button, index % 2, index // 2, 1, 1)
            places_page.add(places_grid)
            self.aqua_stack.add_named(places_page, "Places")

            settings_page = Gtk.ScrolledWindow()
            settings_page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            for title, icon_name, command in (
                ("Network connections", "network-wireless", "nm-connection-editor"),
                ("Sound & media", "audio-volume-high", "pavucontrol"),
                ("Appearance & themes", "preferences-desktop-theme", "xfce4-appearance-settings"),
                ("Display", "video-display", "xfce4-display-settings"),
                ("System settings", "preferences-system", "xfce4-settings-manager"),
            ):
                btn = self._class(Gtk.Button(), "aqua-place")
                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11)
                content.pack_start(self._icon(icon_name, Gtk.IconSize.MENU), False, False, 0)
                content.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
                btn.add(content)
                btn.set_sensitive(shutil.which(command) is not None)
                btn.set_tooltip_text("Open " + title if shutil.which(command) else
                                    command + " is not installed")
                btn.connect("clicked", lambda _button, app=command: self._open_tool(app))
                settings_box.pack_start(btn, False, False, 0)
            settings_page.add(settings_box)
            self.aqua_stack.add_named(settings_page, "Settings")

            root.pack_start(self.aqua_stack, True, True, 0)
            footer = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                                 "aqua-footer")
            footer.pack_start(self._class(Gtk.Label(label="RiceBowl  •  your desktop"),
                                          "aqua-caption"), True, True, 0)
            for icon_name, name in (("preferences-system", "Settings"),
                                    ("system-shutdown", "Power")):
                btn = self._class(Gtk.Button(), "aqua-footer-action")
                btn.set_image(self._icon(icon_name, Gtk.IconSize.MENU))
                btn.set_tooltip_text("Open " + name)
                btn.get_accessible().set_name("Open " + name)
                command = "xfce4-settings-manager" if name == "Settings" else "xfce4-session-logout"
                btn.set_sensitive(shutil.which(command) is not None)
                btn.connect("clicked", lambda _button, app=command: self._open_tool(app))
                footer.pack_start(btn, False, False, 0)
            root.pack_start(footer, False, False, 0)
            buttons["Apps"].set_active(True)
            self.aqua_stack.set_visible_child_name("Apps")
            menu.add(root)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            def search_changed(*_args):
                self._app_page_size = 24
                self._populate(search.get_text())
            search.connect("search-changed", search_changed)
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu, self.search = menu, search
            self._populate("")

        def _create_ten_menu(self):
            """Real application list and pinned app tiles, with shared search/launch logic."""
            if profile == "chromeos":
                self._create_chrome_launcher()
                return
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl " + (heritage.name if heritage else "Windows 10") + " Launcher")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _, _, menu_w, menu_h = menu_geometry(rect.x, rect.y, rect.width, rect.height,
                                                 preferred_width=690 if profile == "chromeos" else 735,
                                                 preferred_height=540 if profile == "chromeos" else 565)
            menu.set_default_size(menu_w, menu_h)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "aero-menu-root")
            rail = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11), "ten-rail")
            rail.set_size_request(58, -1)
            rail.pack_start(self._class(Gtk.Label(label="≡"), "aero-menu-heading"), False, False, 6)
            rail.pack_start(Gtk.Box(), True, True, 0)
            for text, icon, command in (("Settings", "preferences-system", "xfce4-settings-manager"),
                                        ("Power", "system-shutdown", "xfce4-session-logout")):
                button = self._class(Gtk.Button(), "aero-menu-app")
                button.set_image(self._icon(icon, Gtk.IconSize.MENU))
                button.set_tooltip_text(text)
                button.get_accessible().set_name(text + " (opens XFCE dialog)")
                button.connect("clicked", lambda _button, cmd=command: self._open_tool(cmd))
                rail.pack_start(button, False, False, 0)
            root.pack_start(rail, False, False, 0)

            main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            for side in ("start", "end"):
                getattr(main, "set_margin_" + side)(14)
            main.set_margin_top(15)
            main.set_margin_bottom(14)
            main.pack_start(self._class(Gtk.Label(label=heritage.menu_heading if heritage else "Start", xalign=0), "aero-menu-heading"), False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search apps")
            search.get_accessible().set_name("Search installed applications")
            main.pack_start(search, False, False, 0)

            columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            main.pack_start(columns, True, True, 0)
            apps_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            apps_column.set_size_request(max(175, min(250, menu_w - 320)), -1)
            apps_column.pack_start(self._class(Gtk.Label(label="All apps", xalign=0), "aero-menu-sub"),
                                   False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            scroller.add(self.results)
            apps_column.pack_start(scroller, True, True, 0)
            columns.pack_start(apps_column, True, True, 0)

            tile_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            tile_column.pack_start(self._class(Gtk.Label(label="Pinned", xalign=0), "aero-menu-sub"),
                                   False, False, 0)
            self.tile_grid = Gtk.Grid(row_spacing=5, column_spacing=5)
            tile_column.pack_start(self.tile_grid, False, False, 0)
            if menu_w > 510:
                columns.pack_start(tile_column, False, False, 0)
            root.pack_start(main, True, True, 0)

            menu.add(root)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)

            def search_changed(*_args):
                self._app_page_size = 24
                self._populate(search.get_text())
            search.connect("search-changed", search_changed)
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu, self.search = menu, search
            self._render_ten_tiles()
            self._populate("")

        def _create_chrome_launcher(self):
            """ChromeOS-inspired centered search and app grid, not a Windows tile menu."""
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceBowl ChromeOS App Launcher")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _x, _y, menu_w, menu_h = menu_geometry(
                rect.x, rect.y, rect.width, rect.height,
                preferred_width=650, preferred_height=548)
            menu.set_default_size(menu_w, menu_h)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12),
                               "chrome-launcher")
            root.get_style_context().add_class("aero-menu-root")
            root.set_border_width(18)
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            emblem = self._icon("start-here", Gtk.IconSize.DIALOG)
            header.pack_start(emblem, False, False, 0)
            header.pack_start(self._class(
                Gtk.Label(label="Apps", xalign=0), "aero-menu-heading"), True, True, 0)
            settings = self._class(Gtk.Button(), "chrome-launcher-settings")
            settings.set_image(self._icon("preferences-system", Gtk.IconSize.MENU))
            settings.set_tooltip_text("Open device settings")
            settings.get_accessible().set_name("Open device settings")
            settings.connect("clicked", lambda _button:
                             self._open_tool("xfce4-settings-manager"))
            header.pack_end(settings, False, False, 0)
            root.pack_start(header, False, False, 0)

            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search apps on this device")
            search.get_accessible().set_name("Search all installed applications")
            root.pack_start(search, False, False, 0)

            pinned_label = self._class(
                Gtk.Label(label="Your apps", xalign=0), "aero-menu-sub")
            root.pack_start(pinned_label, False, False, 0)
            self.tile_grid = Gtk.Grid(row_spacing=7, column_spacing=8)
            self.tile_grid.set_halign(Gtk.Align.CENTER)
            root.pack_start(self.tile_grid, False, False, 0)
            all_apps_label = self._class(
                Gtk.Label(label="Search results", xalign=0), "aero-menu-sub")
            all_apps_label.set_no_show_all(True)
            root.pack_start(all_apps_label, False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(120)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            scroller.add(self.results)
            root.pack_start(scroller, True, True, 0)
            menu.add(root)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            def search_changed(*_args):
                self._app_page_size = 24
                needle = search.get_text().strip()
                self.tile_grid.set_visible(not bool(needle))
                pinned_label.set_visible(not bool(needle))
                all_apps_label.set_visible(bool(needle))
                scroller.set_visible(bool(needle))
                self._populate(needle)
            search.connect("search-changed", search_changed)
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            menu.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu, self.search = menu, search
            self._render_ten_tiles()
            self._populate("")
            scroller.set_no_show_all(True)
            scroller.hide()
            all_apps_label.hide()

        def _render_ten_tiles(self):
            if not hasattr(self, "tile_grid"):
                return
            for child in self.tile_grid.get_children():
                self.tile_grid.remove(child)
            lookup = {app.get_id(): app for app in self.apps if app.get_id()}
            pinned = [lookup[identifier] for identifier in self._pinned_ids
                      if identifier in lookup][:12 if profile == "chromeos" else 6]
            if profile == "chromeos":
                # A Chromebook launcher must work without manually pinning apps.
                # Fill the grid with REAL installed apps, never mocked tiles.
                pinned_ids = {app.get_id() for app in pinned}
                for app in self.apps:
                    identifier = app.get_id()
                    if identifier and identifier not in pinned_ids:
                        pinned.append(app)
                        pinned_ids.add(identifier)
                    if len(pinned) >= 12:
                        break
            if not pinned:
                self.tile_grid.attach(self._class(Gtk.Label(label="Pin an app from the list", xalign=0),
                                                  "ten-muted"), 0, 0, 2, 1)
            for index, app in enumerate(pinned):
                button = self._class(Gtk.Button(), "ten-tile")
                button.set_size_request(110 if profile == "chromeos" else 116,
                                        80 if profile == "chromeos" else 87)
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
                icon = app.get_icon()
                box.pack_start(Gtk.Image.new_from_gicon(
                    icon, Gtk.IconSize.DIALOG if profile == "chromeos" else Gtk.IconSize.LARGE_TOOLBAR
                ) if icon else self._icon("applications-other",
                    Gtk.IconSize.DIALOG if profile == "chromeos" else Gtk.IconSize.LARGE_TOOLBAR),
                    True, True, 0)
                name = app.get_display_name() or app.get_name() or "Application"
                caption = self._class(Gtk.Label(label=name, xalign=0), "ten-tile-label")
                caption.set_max_width_chars(15)
                caption.set_ellipsize(Pango.EllipsizeMode.END)
                box.pack_start(caption, False, False, 0)
                button.add(box)
                button.get_accessible().set_name("Launch " + name)
                button.connect("clicked", lambda _button, selected=app: self._launch(selected))
                self.tile_grid.attach(button, index % (4 if profile == "chromeos" else 2),
                                      index // (4 if profile == "chromeos" else 2), 1, 1)
            self.tile_grid.show_all()

        def _create_actions(self):
            """Profile-aware controls; never simulate state-changing toggles."""
            actions = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            heading = heritage.control_heading if heritage else ("Action Center" if ten else "Aero Control Panel")
            actions.set_title("RiceBowl " + heading)
            actions.set_decorated(False)
            # GtkScrolledWindow has no useful implicit minimum height.
            # A non-resizable utility window collapses to its first header,
            # making the controls look like a clipped title strip.
            actions.set_resizable(True)
            actions.set_default_size(330, 430)
            actions.set_skip_taskbar_hint(True)
            actions.set_skip_pager_hint(True)
            actions.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            actions.set_transient_for(self.bar)
            actions.set_keep_above(True)
            root = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10),
                               "ten-action-root" if tiles else "aero-control-root")
            root.set_size_request(300, 265)

            title = self._class(Gtk.Label(label=heading, xalign=0), "aero-menu-heading")
            root.pack_start(title, False, False, 0)
            descriptions = {
                "winxp": "Pick a category to configure your computer",
                "winclassic": "Settings  •  Control Panel",
                "chromeos": "Device controls and preferences",
                "frutiger": "Your connected desktop",
                "aero": "Adjust your computer's settings",
                "windows10": "Quick actions and system settings",
            }
            subtitle = self._class(Gtk.Label(label=descriptions.get(profile, ""), xalign=0),
                                   "aero-menu-sub")
            subtitle.set_line_wrap(True)
            root.pack_start(subtitle, False, False, 0)

            if profile == "chromeos":
                sections = (
                    ("Connectivity", (("Wi-Fi & network", "network-wireless", "nm-connection-editor"),
                                      ("Bluetooth", "bluetooth", "blueman-manager"))),
                    ("Device", (("Audio", "audio-volume-high", "pavucontrol"),
                                ("Display", "video-display", "xfce4-display-settings"),
                                ("Preferences", "preferences-system", "xfce4-settings-manager"))),
                )
            elif profile == "winxp":
                sections = (
                    ("Pick a category", (("Network and Internet", "network-workgroup", "nm-connection-editor"),
                                         ("Sounds and Audio", "audio-card", "pavucontrol"),
                                         ("Appearance and Themes", "preferences-desktop-theme", "xfce4-appearance-settings"),
                                         ("Printers and Hardware", "printer", "system-config-printer"))),
                    ("Other settings", (("Control Panel", "preferences-system", "xfce4-settings-manager"),)),
                )
            elif profile == "winclassic":
                sections = (
                    ("Control Panel", (("Display", "video-display", "xfce4-display-settings"),
                                       ("Multimedia", "audio-card", "pavucontrol"),
                                       ("Network", "network-workgroup", "nm-connection-editor"),
                                       ("System", "computer", "xfce4-settings-manager"))),
                )
            elif profile == "frutiger":
                sections = (
                    ("Connections", (("Network", "network-wireless", "nm-connection-editor"),
                                      ("Bluetooth", "bluetooth", "blueman-manager"))),
                    ("Personalize", (("Appearance", "preferences-desktop-theme", "xfce4-appearance-settings"),
                                     ("Sound", "audio-volume-high", "pavucontrol"),
                                     ("Display", "video-display", "xfce4-display-settings"))),
                )
            else:
                sections = (
                    ("Quick settings" if tiles else "System tools",
                     (("Network", "network-wireless", "nm-connection-editor"),
                      ("Sound", "audio-volume-high", "pavucontrol"),
                      ("Display", "video-display", "xfce4-display-settings"),
                      ("Settings", "preferences-system", "xfce4-settings-manager"))),
                )

            for section_title, entries in sections:
                section = self._class(Gtk.Label(label=section_title, xalign=0), "aero-menu-sub")
                root.pack_start(section, False, False, 0)
                grid = Gtk.Grid(row_spacing=5, column_spacing=5)
                for index, (label, icon_name, command) in enumerate(entries):
                    button = self._class(Gtk.Button(), "ten-quick" if tiles else "aero-control-quick")
                    contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
                    contents.pack_start(self._icon(icon_name, Gtk.IconSize.MENU), False, False, 0)
                    caption = Gtk.Label(label=label, xalign=0)
                    caption.set_line_wrap(True)
                    caption.set_max_width_chars(27 if profile == "winxp" else 20)
                    contents.pack_start(caption, True, True, 0)
                    button.add(contents)
                    button.set_tooltip_text("Open " + label if shutil.which(command) else
                                            label + " is not installed")
                    button.get_accessible().set_name("Open " + label)
                    button.set_sensitive(shutil.which(command) is not None)
                    button.connect("clicked", lambda _button, cmd=command: self._open_tool(cmd))
                    # XP category names are full-length navigation entries, not
                    # tiny quick-action tiles: a two-column layout overflows 330px.
                    if profile == "winxp":
                        grid.attach(button, 0, index, 1, 1)
                    else:
                        grid.attach(button, index % 2, index // 2, 1, 1)
                root.pack_start(grid, False, False, 0)

            # Actual hardware information and a VERIFIED volume slider make
            # this a usable control panel rather than decorative quick tiles.
            hardware = self._class(
                Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7),
                "rice-hardware-panel")
            hardware.pack_start(self._class(
                Gtk.Label(label="Device status", xalign=0), "aero-menu-sub"),
                False, False, 0)
            self.control_network_label = self._class(
                Gtk.Label(label="Network: reading…", xalign=0),
                "rice-control-detail")
            self.control_network_label.set_line_wrap(True)
            hardware.pack_start(self.control_network_label, False, False, 0)
            self.control_battery_label = self._class(
                Gtk.Label(label="Battery: reading…", xalign=0),
                "rice-control-detail")
            hardware.pack_start(self.control_battery_label, False, False, 0)
            self.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
            self.control_battery_level.set_value(0)
            self.control_battery_level.set_no_show_all(True)
            hardware.pack_start(self.control_battery_level, False, False, 0)
            self.volume_status_label = self._class(
                Gtk.Label(label="Volume: reading…", xalign=0),
                "rice-control-detail")
            hardware.pack_start(self.volume_status_label, False, False, 0)
            self.volume_scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 0, 100, 5)
            self.volume_scale.set_draw_value(False)
            self.volume_scale.set_sensitive(False)
            self.volume_scale.get_accessible().set_name("System output volume")
            self.volume_scale.set_tooltip_text(
                "Adjust actual PipeWire/PulseAudio output volume, verified after changing")
            self.volume_scale.connect("value-changed", self._queue_volume_change)
            hardware.pack_start(self.volume_scale, False, False, 0)
            self.mute_button = self._class(
                Gtk.ToggleButton(label="Mute output"), "rice-mute")
            self.mute_button.set_sensitive(False)
            self.mute_button.get_accessible().set_name("Mute or unmute output")
            self.mute_button.connect("clicked", self._toggle_output_mute)
            hardware.pack_start(self.mute_button, False, False, 0)
            root.pack_end(hardware, False, False, 4)

            self.status_summary = self._class(
                Gtk.Label(label="Reading hardware status…", xalign=0),
                "rice-status-summary")
            self.status_summary.set_line_wrap(True)
            root.pack_end(self.status_summary, False, False, 2)
            actions_scroll = Gtk.ScrolledWindow()
            actions_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            actions_scroll.set_min_content_width(300)
            actions_scroll.set_min_content_height(260)
            actions_scroll.add(root)
            actions.add(actions_scroll)
            actions.connect("focus-out-event", lambda *_args: self._schedule_popup_hide("control"))
            actions.connect("key-press-event", lambda _widget, event: self._action_key(event))
            self.actions = actions

        def _action_key(self, event):
            if event.keyval == Gdk.KEY_Escape:
                self._hide_actions()
                return True
            return False

        def _cancel_popup_hide(self, name):
            source = self._popup_hide_sources[name]
            self._popup_hide_sources[name] = 0
            if source:
                GLib.source_remove(source)

        def _schedule_popup_hide(self, name):
            # XFCE briefly transfers focus when executing a shortcut. A delayed
            # dismissal lets the explicit remote toggle take precedence.
            self._cancel_popup_hide(name)
            self._popup_hide_sources[name] = GLib.timeout_add(650, self._hide_if_unfocused, name)
            return False

        def _hide_if_unfocused(self, name):
            self._popup_hide_sources[name] = 0
            window = self.menu if name == "menu" else self.actions
            if window.get_visible() and not window.is_active():
                if name == "menu":
                    self._hide_menu()
                else:
                    self._hide_actions()
            return False

        def _hide_actions(self):
            self._cancel_popup_hide("control")
            self.actions.hide()

        def _toggle_actions(self):
            self._cancel_popup_hide("control")
            if self.actions.get_visible():
                self._hide_actions()
                return
            self._hide_menu()
            rect = self._desktop_rect()
            width = min(330, max(0, rect.width - 16))
            height = min(430, max(0, rect.height - panel_height - 16))
            if width < 235 or height < 250:
                self._error("The display is too small for " + ("Action Center." if ten else "Control Panel."))
                return
            self.actions.show_all()
            self.actions.resize(width, height)
            self.actions.move(rect.x + rect.width - width - 8,
                              rect.y + rect.height - panel_height - height - 8)
            self.actions.present()

        def _open_search(self):
            if not self.menu.get_visible():
                self._toggle_menu()
            if self.menu.get_visible():
                if profile == "winxp":
                    self._reveal_luna_search()
                elif profile == "winclassic":
                    self._reveal_classic_search()
                else:
                    self.search.grab_focus()

        def _populate(self, query):
            for child in self.results.get_children():
                self.results.remove(child)
            if profile == "winxp":
                self._populate_luna(query)
                return
            matches = matching_apps(self.apps, query)
            if not matches:
                self.results.pack_start(self._class(Gtk.Label(label="No matching applications", xalign=0),
                                                     "aero-menu-sub"), False, False, 8)
            for app in matches[:self._app_page_size]:
                btn = self._class(Gtk.Button(), "aero-menu-app")
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                icon = app.get_icon()
                row.pack_start(Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU) if icon else
                               self._icon("applications-other", Gtk.IconSize.MENU), False, False, 0)
                row.pack_start(Gtk.Label(label=app.get_display_name(), xalign=0), True, True, 0)
                btn.add(row)
                btn.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                btn.connect("button-press-event", lambda widget, event, selected=app:
                            self._pin_context(widget, selected, event))
                btn.connect("popup-menu", lambda widget, selected=app: self._pin_context(widget, selected))
                self.results.pack_start(btn, False, False, 0)
            if len(matches) > self._app_page_size:
                more = self._class(Gtk.Button(label="All Programs · Show more"), "aero-menu-app")
                more.get_accessible().set_name("Show more installed applications")
                def expand(_button):
                    self._app_page_size += 24
                    self._populate(self.search.get_text())
                more.connect("clicked", expand)
                self.results.pack_start(more, False, False, 0)
            self.results.show_all()

        def _populate_luna(self, query):
            """XP: 2 prominent favorites, a separator and actual installed apps."""
            featured, regular = luna_programs(
                self.apps, self._pinned_ids, query,
                self._app_page_size if query.strip() else 6)

            def add_app(app, *, large=False):
                button = self._class(Gtk.Button(), "luna-program")
                if large:
                    button.get_style_context().add_class("luna-featured")
                content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
                icon = app.get_icon()
                size = Gtk.IconSize.LARGE_TOOLBAR if large else Gtk.IconSize.MENU
                content.pack_start(Gtk.Image.new_from_gicon(icon, size) if icon else
                                   self._icon("applications-other", size), False, False, 0)
                caption = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                if large:
                    classifier = getattr(app, "get_categories", None)
                    category = (classifier() or "").split(";") if callable(classifier) else ()
                    headline = "Internet" if "WebBrowser" in category else (
                        "E-mail" if "Email" in category else "Favorite program")
                    title = self._class(Gtk.Label(label=headline, xalign=0), "luna-program-category")
                    caption.pack_start(title, False, False, 0)
                label = Gtk.Label(label=app.get_display_name() or app.get_name(), xalign=0)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                caption.pack_start(label, False, False, 0)
                content.pack_start(caption, True, True, 0)
                button.add(content)
                button.get_accessible().set_name("Launch " + (app.get_display_name() or app.get_name()))
                button.connect("clicked", lambda _button, selected=app: self._launch(selected))
                button.connect("button-press-event", lambda widget, event, selected=app:
                               self._pin_context(widget, selected, event))
                button.connect("popup-menu", lambda widget, selected=app:
                               self._pin_context(widget, selected))
                self.results.pack_start(button, False, False, 0)

            for app in featured:
                add_app(app, large=True)
            if featured and regular:
                self.results.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                                        False, False, 5)
            for app in regular:
                add_app(app)
            if not featured and not regular:
                self.results.pack_start(self._class(
                    Gtk.Label(label="No installed programs match", xalign=0),
                    "luna-empty"), False, False, 12)
            if query.strip() and len(matching_apps(self.apps, query)) > self._app_page_size:
                more = self._class(Gtk.Button(label="Show more results…"), "luna-program")
                more.connect("clicked", lambda *_args: self._expand_luna_results(query))
                self.results.pack_start(more, False, False, 0)
            self.results.show_all()

        def _expand_luna_results(self, query):
            self._app_page_size += 24
            self._populate(query)

        def _search_key(self, event):
            if event.keyval == Gdk.KEY_Escape:
                self._hide_menu()
                return True
            if self.search.is_focus() and event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
                apps = matching_apps(self.apps, self.search.get_text())
                if apps:
                    self._launch(apps[0])
                    return True
            if event.keyval == Gdk.KEY_Down and self.results.get_children():
                self.results.get_children()[0].grab_focus()
                return True
            return False

        def _hide_menu(self):
            self._cancel_popup_hide("menu")
            self._menu_focused = False
            if self.menu:
                self.menu.hide()
            return False

        def _menu_focus_in(self, *_args):
            self._menu_focused = True
            return False

        def _menu_focus_out(self, *_args):
            return self._schedule_popup_hide("menu")

        def _toggle_menu(self):
            self._cancel_popup_hide("menu")
            if self.menu.get_visible():
                self._hide_menu()
                return
            self._hide_actions()
            rect = self._desktop_rect()
            self._menu_focused = False
            self._menu_opened_at = GLib.get_monotonic_time()
            self.search.set_text("")
            preferred_sizes = {
                "winxp": (480, 540),
                "winclassic": (285, 430),
                "chromeos": (650, 548),
                "frutiger": (535, 540),
                "windows10": (735, 565),
                "aero": (490, 505),
            }
            preferred_width, preferred_height = preferred_sizes.get(profile, (490, 505))
            x, y, w, h = menu_geometry(
                rect.x, rect.y, rect.width, rect.height,
                preferred_width=preferred_width, preferred_height=preferred_height,
                panel_height=panel_height)
            if w < 180 or h < 180:
                self._error("The display is too small for the Start menu.")
                return
            if profile == "chromeos":
                x = rect.x + (rect.width - w) // 2
            if profile == "winxp":
                self.search.set_no_show_all(True)
                self.search.hide()
            self.menu.show_all()
            self.menu.resize(w, h)
            self.menu.move(x, y)
            self.menu.present()
            if profile == "winxp":
                GLib.idle_add(self._reanchor_luna_menu)
                first_app = next((widget for widget in self.results.get_children()
                                  if isinstance(widget, Gtk.Button)), None)
                if first_app:
                    first_app.grab_focus()
            else:
                self.search.grab_focus()

        def _reanchor_luna_menu(self):
            """Anchor using GTK's allocated height, not its requested height."""
            if not self.menu.get_visible():
                return False
            rect = self._desktop_rect()
            actual_w, actual_h = self.menu.get_size()
            self.menu.move(rect.x + 8, actual_popup_y(rect.y, rect.height, actual_h,
                                                       panel_height=panel_height))
            return False

        def _open_uri(self, uri):
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
                self._hide_menu()
            except GLib.Error as exc:
                self._error(str(exc))

        def _launch(self, app):
            try:
                app.launch([], None)
                self._hide_menu()
            except GLib.Error as exc:
                self._error(str(exc))

        def _error(self, message):
            dialog = Gtk.MessageDialog(transient_for=self.bar, flags=Gtk.DialogFlags.MODAL,
                                       message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
                                       text="Could not launch application")
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()

    app = AeroShell()
    result = app.run(argv or ["ricehub-aero-shell"])
    return 1 if app._smoke_failed else result
