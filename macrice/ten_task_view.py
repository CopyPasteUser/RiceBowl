"""Windows 10 Task View over existing Wnck/XFCE workspaces and real windows."""

from __future__ import annotations

from .aero_windows import is_task_window

MAX_VISIBLE_WINDOWS = 60


def card_position(index: int) -> tuple[int, int]:
    """Use two readable desktop-preview columns with bounded vertical scroll."""
    if not isinstance(index, int) or index < 0:
        raise ValueError("Invalid Task View window index")
    return index % 2, index // 2


def manageable_workspace_count(count: int, *, maximum: int = 12) -> bool:
    return isinstance(count, int) and 1 <= count < maximum


class TenTaskView:
    """A renderer only: XFWM4, Wnck and the user's workspaces remain owners."""

    def __init__(self, shell, Gtk, Gdk, GLib):
        self.shell, self.Gtk, self.GLib = shell, Gtk, GLib
        self.closed = False
        self._screen_signals = []
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Windows 10 · Task View")
        self.window.set_decorated(False)
        self.window.set_resizable(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_transient_for(shell.bar)
        self.window.set_keep_above(True)
        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=13),
                            "ten-taskview-root")
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.pack_start(shell._class(Gtk.Label(label="Task View", xalign=0),
                                      "ten-action-title"), True, True, 0)
        close = shell._class(Gtk.Button(label="×"), "ten-rail-button")
        close.get_accessible().set_name("Close Task View")
        close.connect("clicked", lambda _button: self.hide())
        header.pack_end(close, False, False, 0)
        root.pack_start(header, False, False, 0)
        self.message = shell._class(Gtk.Label(label="", xalign=0), "ten-action-feedback")
        self.message.set_line_wrap(True)
        root.pack_start(self.message, False, False, 0)
        workspace_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        workspace_header.pack_start(shell._class(Gtk.Label(label="Desktops", xalign=0),
                                                 "ten-section-heading"), True, True, 0)
        self.add_button = shell._class(Gtk.Button(label="+ New desktop"),
                                       "ten-settings-action")
        self.add_button.get_accessible().set_name("Create an XFCE desktop")
        self.add_button.connect("clicked", lambda _button: self._new_desktop())
        workspace_header.pack_end(self.add_button, False, False, 0)
        root.pack_start(workspace_header, False, False, 0)
        self.desktops = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        root.pack_start(self.desktops, False, False, 0)
        root.pack_start(shell._class(Gtk.Label(label="Open windows", xalign=0),
                                    "ten-section-heading"), False, False, 0)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.windows = Gtk.Grid(row_spacing=9, column_spacing=9)
        self.windows.set_column_homogeneous(True)
        scroller.add(self.windows)
        root.pack_start(scroller, True, True, 0)
        self.window.add(root)
        self.window.connect("key-press-event", self._key)
        self.window.connect("delete-event", lambda *_args: self._on_delete())
        screen = self._screen()
        if screen is not None:
            for signal in ("active-workspace-changed", "workspace-created",
                           "workspace-destroyed"):
                self._screen_signals.append(screen.connect(signal, lambda *_args: self.refresh()))

    def _on_delete(self):
        self.hide()
        return True

    def _key(self, _widget, event):
        if event.keyval == self.Gtk.accelerator_parse("Escape")[0]:
            self.hide()
            return True
        return False

    def show(self):
        if self.closed:
            return
        rect = self.shell._desktop_rect()
        width, height = min(790, rect.width - 24), min(570, rect.height - 64)
        if width < 320 or height < 230:
            self.shell._error("The display is too small for Task View.")
            return
        self.window.show_all()
        self.window.resize(width, height)
        self.window.move(rect.x + (rect.width - width) // 2,
                         rect.y + (rect.height - height - 40) // 2)
        self.refresh()
        self.window.present()

    def hide(self):
        self.window.hide()
        for box in (self.desktops, self.windows):
            for child in box.get_children():
                box.remove(child)

    def _screen(self):
        tracker = getattr(self.shell, "_window_tracker", None)
        return tracker.screen if tracker is not None else None

    def refresh(self):
        if self.closed or not self.window.get_visible():
            return
        for child in self.desktops.get_children():
            self.desktops.remove(child)
        for child in self.windows.get_children():
            self.windows.remove(child)
        screen = self._screen()
        if screen is None:
            self.message.set_text("Task View requires libwnck and an XFCE/X11 session")
            self.add_button.set_sensitive(False)
            return
        screen.force_update()
        workspaces = tuple(screen.get_workspaces())
        active = screen.get_active_workspace()
        active_index = active.get_number() if active else 0
        can_change_count = callable(getattr(screen, "change_workspace_count", None))
        self.add_button.set_sensitive(can_change_count and
                                      manageable_workspace_count(len(workspaces)))
        self.message.set_text("" if workspaces else "No X11 workspaces reported")
        Gtk = self.Gtk
        for workspace in workspaces[:12]:
            index = workspace.get_number()
            cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            button = self.shell._class(Gtk.Button(label=f"Desktop {index + 1}"),
                                       "ten-taskview-desktop")
            if index == active_index:
                button.get_style_context().add_class("ten-taskview-active")
            button.get_accessible().set_name(f"Switch to desktop {index + 1}")
            button.connect("clicked", lambda _button, target=index:
                           self._switch_desktop(target))
            cell.pack_start(button, False, False, 0)
            if index == len(workspaces) - 1 and len(workspaces) > 1 and can_change_count:
                close = self.shell._class(Gtk.Button(label="×"), "ten-taskview-desktop")
                close.get_accessible().set_name("Close last empty desktop")
                close.set_tooltip_text("Only empty last desktops can be removed")
                # A hidden/utility window still belongs to the workspace. Do
                # not silently relocate it by removing that workspace.
                close.set_sensitive(not any(
                    window.get_workspace() == workspace
                    for window in screen.get_windows()))
                close.connect("clicked", lambda _button: self._close_last())
                cell.pack_start(close, False, False, 0)
            self.desktops.pack_start(cell, False, False, 0)

        wnck = self.shell._window_tracker.wnck
        live_windows = tuple(window for window in screen.get_windows()
                             if is_task_window(window, wnck))
        if len(live_windows) > MAX_VISIBLE_WINDOWS:
            self.message.set_text(
                f"Showing first {MAX_VISIBLE_WINDOWS} of {len(live_windows)} windows")
        for card_index, window in enumerate(live_windows[:MAX_VISIBLE_WINDOWS]):
            xid = int(window.get_xid())
            workspace = window.get_workspace()
            index = workspace.get_number() if workspace else active_index
            row = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6),
                                    "ten-taskview-window")
            if window.is_active():
                row.get_style_context().add_class("ten-taskview-window-active")
            title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            icon = window.get_icon()
            if icon is not None:
                image = Gtk.Image.new_from_pixbuf(icon.scale_simple(32, 32, 2))
            else:
                image = self.shell._icon("application-x-executable", Gtk.IconSize.DIALOG)
            title_row.pack_start(image, False, False, 0)
            name = window.get_name() or "Application"
            title = self.shell._class(Gtk.Label(label=name, xalign=0), "ten-network-name")
            title.set_ellipsize(3)
            title.set_max_width_chars(28)
            title_row.pack_start(title, True, True, 0)
            close = self.shell._class(Gtk.Button(label="×"), "ten-taskview-close")
            close.set_tooltip_text("Close this window")
            close.get_accessible().set_name("Close window " + name)
            close.connect("clicked", lambda _button, target=xid: self._close_window(target))
            title_row.pack_end(close, False, False, 0)
            row.pack_start(title_row, False, False, 0)
            actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
            actions.pack_start(self.shell._class(
                Gtk.Label(label=f"Desktop {index+1}"), "ten-muted"), True, True, 0)
            activate = self.shell._class(Gtk.Button(label="Open window"),
                                         "ten-settings-action")
            activate.get_accessible().set_name("Activate " + name)
            activate.connect("clicked", lambda _button, target=xid: self._activate(target))
            actions.pack_end(activate, False, False, 0)
            if len(workspaces) > 1:
                move = Gtk.ComboBoxText()
                move.append("-", "Move to…")
                for ws in workspaces:
                    move.append(str(ws.get_number()), f"Desktop {ws.get_number()+1}")
                move.set_active_id("-")
                move.get_accessible().set_name("Move window to another desktop")
                move.connect("changed", lambda combo, target=xid:
                             self._move(target, combo.get_active_id()))
                actions.pack_end(move, False, False, 0)
            row.pack_end(actions, False, False, 0)
            column, grid_row = card_position(card_index)
            self.windows.attach(row, column, grid_row, 1, 1)
        if not live_windows:
            self.windows.attach(self.shell._class(
                Gtk.Label(label="No open application windows", xalign=0), "ten-muted"),
                0, 0, 2, 1)
        self.desktops.show_all()
        self.windows.show_all()

    def _switch_desktop(self, number):
        screen = self._screen()
        workspace = screen.get_workspace(number) if screen else None
        if workspace is None:
            self.message.set_text("Desktop is no longer available")
            return
        workspace.activate(self.Gtk.get_current_event_time())
        self.hide()

    def _activate(self, xid):
        tracker = getattr(self.shell, "_window_tracker", None)
        window = tracker.wnck.Window.get(xid) if tracker else None
        if window is None:
            self.refresh()
            return
        now = self.Gtk.get_current_event_time()
        workspace = window.get_workspace()
        if workspace is not None:
            workspace.activate(now)
        if window.is_minimized():
            window.unminimize(now)
        window.activate(now)
        self.hide()

    def _move(self, xid, target):
        if target is None or not target.isdecimal():
            return
        tracker = getattr(self.shell, "_window_tracker", None)
        if tracker is None:
            return
        window = tracker.wnck.Window.get(xid)
        workspace = tracker.screen.get_workspace(int(target))
        if window is None or workspace is None or not is_task_window(window, tracker.wnck):
            self.message.set_text("The window or desktop is no longer available")
            return
        window.move_to_workspace(workspace)
        self.refresh()

    def _close_window(self, xid):
        """Only close a still-live, tasklist-visible Wnck window on click."""
        tracker = getattr(self.shell, "_window_tracker", None)
        window = tracker.wnck.Window.get(xid) if tracker else None
        if window is None or not is_task_window(window, tracker.wnck):
            self.message.set_text("This window is no longer available")
            self.refresh()
            return
        window.close(self.Gtk.get_current_event_time())
        self.GLib.timeout_add(250, self._refresh_after_close)

    def _refresh_after_close(self):
        self.refresh()
        return False

    def _new_desktop(self):
        screen = self._screen()
        if screen is None:
            return
        count = len(screen.get_workspaces())
        if not manageable_workspace_count(count):
            self.message.set_text("Maximum of 12 desktops reached")
            return
        screen.change_workspace_count(count + 1)
        self.GLib.timeout_add(350, self._verify_count, count + 1)

    def _close_last(self):
        screen = self._screen()
        if screen is None:
            return
        workspaces = tuple(screen.get_workspaces())
        if len(workspaces) < 2:
            return
        last = workspaces[-1]
        if any(window.get_workspace() == last
               for window in screen.get_windows()):
            self.message.set_text("Move or close all windows on the last desktop first")
            return
        if screen.get_active_workspace() == last:
            workspaces[-2].activate(self.Gtk.get_current_event_time())
        screen.change_workspace_count(len(workspaces) - 1)
        self.GLib.timeout_add(350, self._verify_count, len(workspaces) - 1)

    def _verify_count(self, expected):
        self.refresh()
        screen = self._screen()
        if screen is not None and len(screen.get_workspaces()) != expected:
            self.message.set_text("XFCE did not confirm the desktop change")
        return False

    def close(self):
        if self.closed:
            return
        self.closed = True
        screen = self._screen()
        if screen is not None:
            for handler in self._screen_signals:
                screen.disconnect(handler)
        self._screen_signals = []
        self.window.destroy()
