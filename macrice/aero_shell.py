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
.aero-menu-side button { background: transparent; border: 1px solid transparent; color: #194467; box-shadow: none; }
.aero-menu-side button:hover { background: rgba(255,255,255,.55); border-color: #74a7cb; }
"""


def run(argv: list[str] | None = None) -> int:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

    from .aero_windows import create_window_tracker, toggle_window
    from .installer import project_root

    class AeroShell(Gtk.Application):
        def __init__(self):
            super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
            self.bar = None
            self.menu = None
            self.apps = ()
            self.window_buttons = {}
            self._visible_window_ids = ()
            self._overflow_windows = ()
            self._menu_focused = False
            self._tray = None
            self._pin_count = 0
            self._pinned_ids = ()
            self._pin_config_path = pin_file()
            self._task_capacity = 0
            self.show_desktop_button = None
            self._app_page_size = 24
            self._smoke = False
            self._smoke_failed = False

        def do_command_line(self, command_line):
            args = command_line.get_arguments()
            if "--quit" in args:
                if self.bar is not None:
                    self.quit()
                return 0
            self._smoke = "--smoke-test" in args
            self.activate()
            if self._smoke:
                GLib.timeout_add(850, self._smoke_check)
            return 0

        def do_activate(self):
            if self.bar is not None:
                self._toggle_menu()
                return
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
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
            self._create_taskbar()
            self._create_menu()
            self.connect("shutdown", self._shutdown)
            self._window_tracker = create_window_tracker(GLib.idle_add, self._windows_changed)
            if self.show_desktop_button is not None:
                self.show_desktop_button.set_sensitive(self._window_tracker is not None)
            screen = Gdk.Screen.get_default()
            screen.connect("monitors-changed", self._screen_changed)
            screen.connect("size-changed", self._screen_changed)
            self._catalog_monitor = Gio.AppInfoMonitor.get()
            self._catalog_monitor.connect("changed", self._catalog_changed)

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
            except Exception:
                import traceback
                traceback.print_exc()
                self._smoke_failed = True
            self.quit()
            return False

        def _shutdown(self, *_args):
            if self._tray is not None:
                self._tray.close()
                self._tray = None

        def _screen_changed(self, *_args):
            rect = self._desktop_rect()
            self.bar.resize(rect.width, PANEL_HEIGHT)
            self.bar.move(rect.x, rect.y + rect.height - PANEL_HEIGHT)
            if self.bar.get_realized():
                self._reserve_workarea(self.bar)
            self._task_capacity = task_capacity(rect.width, self._pin_count)
            if self._window_tracker is not None:
                from .aero_windows import is_task_window
                screen = self._window_tracker.screen
                self._windows_changed(tuple(
                    win for win in screen.get_windows()
                    if is_task_window(win, self._window_tracker.wnck)
                ), screen.get_active_window())
            if self.menu.get_visible():
                self._hide_menu()

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
            self._pin_count = len(candidate)
            self._task_capacity = task_capacity(self._desktop_rect().width, self._pin_count)
            if self._window_tracker is not None:
                from .aero_windows import is_task_window
                screen = self._window_tracker.screen
                self._windows_changed(tuple(
                    win for win in screen.get_windows()
                    if is_task_window(win, self._window_tracker.wnck)
                ), screen.get_active_window())

        def _reserve_workarea(self, widget, *_args):
            """Reserve the bottom strip on X11, but never change XFCE panel settings."""
            if os.environ.get("RICEHUB_AERO_RESERVE", "1") == "0":
                return
            try:
                gi.require_version("GdkX11", "3.0")
                from gi.repository import GdkX11
                rect = self._desktop_rect()
                props = bottom_strut(rect.x, rect.y, rect.width, rect.height,
                                     Gdk.Screen.get_default().get_height())
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
                logging.getLogger(__name__).warning("Aero workarea reservation unavailable: %s", exc)

        def _open_tool(self, command):
            """Open a known XFCE utility without a shell or implicit system changes."""
            allowed = ("xfce4-settings-manager", "xfce4-session-logout",
                       "nm-connection-editor", "pavucontrol", "xfce4-display-settings")
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

        def _class(self, widget, name):
            widget.get_style_context().add_class(name)
            return widget

        def _desktop_rect(self):
            screen = Gdk.Screen.get_default()
            monitor = screen.get_primary_monitor()
            return screen.get_monitor_geometry(monitor if monitor >= 0 else 0)

        def _icon(self, name, size=Gtk.IconSize.LARGE_TOOLBAR):
            return Gtk.Image.new_from_icon_name(name, size)

        def _create_taskbar(self):
            rect = self._desktop_rect()
            win = Gtk.ApplicationWindow(application=self)
            win.set_title("RiceHub Aero Taskbar")
            win.set_decorated(False)
            win.set_resizable(False)
            win.set_skip_taskbar_hint(True)
            win.set_skip_pager_hint(True)
            win.set_type_hint(Gdk.WindowTypeHint.DOCK)
            win.set_keep_above(True)
            win.set_accept_focus(False)
            win.set_default_size(rect.width, PANEL_HEIGHT)
            win.move(rect.x, rect.y + rect.height - PANEL_HEIGHT)

            row = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8), "aero-taskbar")
            if os.environ.get("RICEHUB_AERO_GLASS") == "1":
                row.get_style_context().add_class("aero-glass")
            start = self._class(Gtk.Button(), "aero-start")
            contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            logo = project_root() / "assets/aero-penguin.svg"
            try:
                img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo), 34, 34, True))
            except (GLib.Error, OSError):
                img = self._icon("start-here", Gtk.IconSize.LARGE_TOOLBAR)
            contents.pack_start(img, False, False, 0)
            contents.pack_start(Gtk.Label(label="Start"), False, False, 0)
            start.add(contents)
            start.get_accessible().set_name("Toggle Aero Start menu")
            start.connect("clicked", lambda _button: self._toggle_menu())
            row.pack_start(start, False, False, 4)
            self.start_button = start
            self.pinned_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            row.pack_start(self.pinned_box, False, False, 0)
            self._render_pins()
            self._pin_count = len(self._pinned_ids)
            self.tasks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            self._task_capacity = task_capacity(rect.width, self._pin_count)
            self.overflow_button = self._class(Gtk.Button(), "aero-task-overflow")
            self.overflow_button.get_accessible().set_name("Show other running windows")
            self.overflow_button.connect("clicked", self._show_overflow)
            row.pack_start(self.tasks, False, False, 4)
            row.pack_start(Gtk.Box(), True, True, 0)
            desktop = self._class(Gtk.Button(), "aero-desktop")
            desktop.set_tooltip_text("Show desktop / restore windows")
            desktop.get_accessible().set_name("Show desktop or restore windows")
            desktop.connect("clicked", self._show_desktop)
            row.pack_end(desktop, False, False, 0)
            self.show_desktop_button = desktop
            clock = self._class(Gtk.Label(), "aero-time")
            clock.set_justify(Gtk.Justification.CENTER)
            row.pack_end(clock, False, False, 6)
            for label, icon, command in (
                ("Network connections", "network-wireless", "nm-connection-editor"),
                ("Sound settings", "audio-volume-high", "pavucontrol"),
            ):
                if shutil.which(command):
                    quick = self._class(Gtk.Button(), "aero-quick")
                    quick.set_image(self._icon(icon, Gtk.IconSize.MENU))
                    quick.set_tooltip_text(label)
                    quick.get_accessible().set_name(label)
                    quick.connect("clicked", lambda _btn, cmd=command: self._open_tool(cmd))
                    row.pack_end(quick, False, False, 0)
            if os.environ.get("RICEHUB_AERO_TRAY", "1") != "0":
                tray_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                row.pack_end(tray_box, False, False, 4)
                try:
                    from .aero_tray import StatusNotifierTray
                    self._tray = StatusNotifierTray(tray_box, Gtk, Gio, GLib, GdkPixbuf)
                except (GLib.Error, RuntimeError, OSError) as exc:
                    logging.getLogger(__name__).warning("Optional Aero tray unavailable: %s", exc)
            def update_clock():
                clock.set_text(GLib.DateTime.new_now_local().format("%H:%M\n%d %b"))
                return True
            update_clock()
            GLib.timeout_add_seconds(30, update_clock)
            win.add(row)
            win.connect("realize", self._reserve_workarea)
            win.show_all()
            win.move(rect.x, rect.y + rect.height - PANEL_HEIGHT)
            self.bar = win

        def _windows_changed(self, windows, active):
            """Keep task buttons stable across title, state and focus changes."""
            visible, self._overflow_windows = select_windows(tuple(windows), active, self._task_capacity)
            visible_ids = tuple(window.get_xid() for window in visible)
            if visible_ids != self._visible_window_ids:
                for child in self.tasks.get_children():
                    self.tasks.remove(child)
                previous = self.window_buttons
                self.window_buttons = {}
                for window in visible:
                    xid = window.get_xid()
                    if xid in previous:
                        button, icon, label = previous[xid]
                    else:
                        button = self._class(Gtk.Button(), "aero-task")
                        button.set_size_request(135, 35)
                        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        icon = Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.MENU)
                        label = Gtk.Label(xalign=0)
                        label.set_max_width_chars(12)
                        label.set_ellipsize(Pango.EllipsizeMode.END)
                        content.pack_start(icon, False, False, 0)
                        content.pack_start(label, True, True, 0)
                        button.add(content)
                        button.connect("clicked", lambda _btn, target=window: self._activate_task(target))
                    self.window_buttons[xid] = (button, icon, label)
                    self.tasks.pack_start(button, False, False, 0)
                self._visible_window_ids = visible_ids
            for window in visible:
                button, icon, label = self.window_buttons[window.get_xid()]
                title = window.get_name() or "Application"
                if label.get_text() != title:
                    label.set_text(title)
                    button.set_tooltip_text(title)
                    button.get_accessible().set_name("Switch to " + title)
                pixbuf = window.get_mini_icon()
                if pixbuf is not None:
                    icon.set_from_pixbuf(pixbuf)
                context = button.get_style_context()
                if window == active and not window.is_minimized():
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

        def _activate_task(self, window):
            if self._window_tracker:
                toggle_window(window, self._window_tracker.screen.get_active_window(),
                              Gtk.get_current_event_time())
            self._hide_menu()

        def _show_overflow(self, button):
            menu = Gtk.Menu()
            for window in self._overflow_windows:
                item = Gtk.MenuItem(label=window.get_name() or "Application")
                item.connect("activate", lambda _item, target=window: self._activate_task(target))
                menu.append(item)
            menu.show_all()
            menu.popup_at_widget(button, Gdk.Gravity.NORTH_WEST, Gdk.Gravity.SOUTH_WEST, None)

        def _create_menu(self):
            menu = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            menu.set_title("RiceHub Aero Start")
            menu.set_decorated(False)
            menu.set_resizable(False)
            menu.set_skip_taskbar_hint(True)
            menu.set_skip_pager_hint(True)
            menu.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            menu.set_transient_for(self.bar)
            menu.set_keep_above(True)
            rect = self._desktop_rect()
            _, _, menu_w, menu_h = menu_geometry(rect.x, rect.y, rect.width, rect.height)
            menu.set_default_size(menu_w, menu_h)
            body = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "aero-menu-root")
            main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            main.set_margin_start(14)
            main.set_margin_top(14)
            main.set_margin_bottom(10)
            main.set_margin_end(10)
            main.set_size_request(min(320, max(180, menu_w - 36)), -1)
            main.pack_start(self._class(Gtk.Label(label="Programs", xalign=0), "aero-menu-heading"), False, False, 0)
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
                power = self._class(Gtk.Button(label="Log off…"), "aero-menu-power")
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

        def _populate(self, query):
            for child in self.results.get_children():
                self.results.remove(child)
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
            self._menu_focused = False
            if self.menu:
                self.menu.hide()
            return False

        def _menu_focus_in(self, *_args):
            self._menu_focused = True
            return False

        def _menu_focus_out(self, *_args):
            # Ignore the immediate focus shuffle when opening from an X11 DOCK.
            if self._menu_focused and GLib.get_monotonic_time() - self._menu_opened_at > 220_000:
                self._hide_menu()
            return False

        def _toggle_menu(self):
            if self.menu.get_visible():
                self._hide_menu()
                return
            rect = self._desktop_rect()
            self._menu_focused = False
            self._menu_opened_at = GLib.get_monotonic_time()
            self.search.set_text("")
            x, y, w, h = menu_geometry(rect.x, rect.y, rect.width, rect.height)
            if w < 180 or h < 180:
                self._error("The display is too small for the Aero Start menu.")
                return
            self.menu.show_all()
            self.menu.resize(w, h)
            self.menu.move(x, y)
            self.menu.present()
            self.search.grab_focus()

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
