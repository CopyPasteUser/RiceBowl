"""On-demand, event-driven Frutiger Aero taskbar and searchable Start menu.

Only runs when explicitly launched or on login after selecting an Aero rice.
Uses the installed Gio .desktop catalog; does not poll the process table.
"""

from __future__ import annotations

from pathlib import Path


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
.aero-time { color: #fff; font-size: 12px; font-weight: bold; }
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

        def do_command_line(self, command_line):
            args = command_line.get_arguments()
            if "--quit" in args:
                if self.bar is not None:
                    self.quit()
                return 0
            self.activate()
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
            self._create_taskbar()
            self._create_menu()
            self._window_tracker = create_window_tracker(GLib.idle_add, self._windows_changed)
            self._catalog_monitor = Gio.AppInfoMonitor.get()
            self._catalog_monitor.connect("changed", self._catalog_changed)

        def _catalog_changed(self, *_args):
            self.apps = app_catalog(Gio)
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
            win.set_size_request(rect.width, 53)
            win.move(rect.x, rect.y + rect.height - 53)

            row = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8), "aero-taskbar")
            start = self._class(Gtk.Button(), "aero-start")
            contents = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            logo = project_root() / "assets/aero-penguin.svg"
            if logo.exists():
                img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(logo), 34, 34, True))
                contents.pack_start(img, False, False, 0)
            contents.pack_start(Gtk.Label(label="Start"), False, False, 0)
            start.add(contents)
            start.get_accessible().set_name("Toggle Aero Start menu")
            start.connect("clicked", lambda _button: self._toggle_menu())
            row.pack_start(start, False, False, 4)
            self.start_button = start
            for wanted in ("file manager", "browser", "terminal"):
                app = next((a for a in self.apps if wanted in (a.get_display_name() or "").casefold()), None)
                if not app:
                    continue
                btn = self._class(Gtk.Button(), "aero-pin")
                icon = app.get_icon()
                btn.set_image(Gtk.Image.new_from_gicon(icon, Gtk.IconSize.LARGE_TOOLBAR) if icon else
                              self._icon("application-x-executable"))
                btn.set_tooltip_text(app.get_display_name())
                btn.get_accessible().set_name("Launch " + app.get_display_name())
                btn.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                row.pack_start(btn, False, False, 0)
            self.tasks = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            self._task_capacity = max(2, min(9, (rect.width - 410) // 160))
            self.overflow_button = self._class(Gtk.Button(), "aero-task-overflow")
            self.overflow_button.get_accessible().set_name("Show other running windows")
            self.overflow_button.connect("clicked", self._show_overflow)
            row.pack_start(self.tasks, False, False, 4)
            row.pack_start(Gtk.Box(), True, True, 0)
            clock = self._class(Gtk.Label(), "aero-time")
            row.pack_end(clock, False, False, 12)
            def update_clock():
                clock.set_text(GLib.DateTime.new_now_local().format("%a %H:%M"))
                return True
            update_clock()
            GLib.timeout_add_seconds(30, update_clock)
            win.add(row)
            win.show_all()
            win.move(rect.x, rect.y + rect.height - 53)
            self.bar = win

        def _windows_changed(self, windows, active):
            """Keep task buttons stable across title, state and focus changes."""
            visible = list(windows[:self._task_capacity])
            if active in windows and active not in visible:
                visible[-1] = active
            visible_ids = tuple(window.get_xid() for window in visible)
            self._overflow_windows = tuple(window for window in windows if window not in visible)
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
            menu.set_default_size(490, 505)
            body = self._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL), "aero-menu-root")
            main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            main.set_margin_start(14)
            main.set_margin_top(14)
            main.set_margin_bottom(10)
            main.set_margin_end(10)
            main.set_size_request(320, -1)
            main.pack_start(self._class(Gtk.Label(label="Programs", xalign=0), "aero-menu-heading"), False, False, 0)
            search = self._class(Gtk.SearchEntry(), "aero-menu-search")
            search.set_placeholder_text("Search programs")
            search.get_accessible().set_name("Search installed programs")
            main.pack_start(search, False, False, 0)
            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroller.set_min_content_height(340)
            self.results = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            scroller.add(self.results)
            main.pack_start(scroller, True, True, 0)
            body.pack_start(main, True, True, 0)
            side = self._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12), "aero-menu-side")
            logo = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(project_root() / "assets/aero-penguin.svg"), 70, 70, True))
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
            body.pack_start(side, False, False, 0)
            menu.add(body)
            menu.connect("focus-in-event", self._menu_focus_in)
            menu.connect("focus-out-event", self._menu_focus_out)
            search.connect("search-changed", lambda *_: self._populate(search.get_text()))
            search.connect("key-press-event", lambda _widget, event: self._search_key(event))
            self.menu = menu
            self.search = search
            self._populate("")

        def _populate(self, query):
            for child in self.results.get_children():
                self.results.remove(child)
            matches = [app for app in self.apps if query.casefold().strip() in
                       (app.get_display_name() or app.get_name()).casefold()][:24]
            if not matches:
                self.results.pack_start(self._class(Gtk.Label(label="No matching applications", xalign=0),
                                                     "aero-menu-sub"), False, False, 8)
            for app in matches:
                btn = self._class(Gtk.Button(), "aero-menu-app")
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                icon = app.get_icon()
                row.pack_start(Gtk.Image.new_from_gicon(icon, Gtk.IconSize.MENU) if icon else
                               self._icon("applications-other", Gtk.IconSize.MENU), False, False, 0)
                row.pack_start(Gtk.Label(label=app.get_display_name(), xalign=0), True, True, 0)
                btn.add(row)
                btn.connect("clicked", lambda _btn, selected=app: self._launch(selected))
                self.results.pack_start(btn, False, False, 0)
            self.results.show_all()

        def _search_key(self, event):
            if event.keyval == Gdk.KEY_Escape:
                self._hide_menu()
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
            self.menu.show_all()
            self.menu.move(rect.x + 8, rect.y + rect.height - 53 - 505)
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

    return AeroShell().run(argv or ["ricehub-aero-shell"])
