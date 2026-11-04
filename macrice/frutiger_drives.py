"""Native Aqua mounted-volume flyout backed by Gio's event-driven VolumeMonitor.

Only mounted, user-visible locations appear. Unmount is explicit, asynchronous
and never uses privileged shell commands or forced ejection.
"""

from __future__ import annotations

from urllib.parse import unquote, urlsplit


_SYSTEM_MOUNT_ROOTS = ("/", "/boot", "/proc", "/sys", "/dev", "/run", "/var", "/usr", "/etc", "/tmp", "/home")


def _system_mount(uri):
    parts = urlsplit(uri)
    if parts.scheme != "file":
        return False
    path = unquote(parts.path).rstrip("/") or "/"
    return path in _SYSTEM_MOUNT_ROOTS or path.startswith(("/boot/", "/proc/", "/sys/", "/dev/"))


def visible_mounts(mounts):
    """Filter system roots/shadow mounts without probing filesystem contents."""
    rows = []
    for mount in mounts:
        try:
            if mount.is_shadowed():
                continue
            uri = mount.get_default_location().get_uri()
            if not isinstance(uri, str) or _system_mount(uri):
                continue
            rows.append((str(mount.get_name())[:70], uri, mount))
        except Exception:
            # Gio mounts can disappear while VolumeMonitor is enumerating.
            continue
    return sorted(rows, key=lambda row: row[0].casefold())[:8]


class AquaDrives:
    def __init__(self, shell, Gtk, Gio):
        self.shell, self.Gtk, self.Gio = shell, Gtk, Gio
        self.monitor = Gio.VolumeMonitor.get()
        self.handlers = []
        self.pending = False
        self._closed = False
        self.popover = Gtk.Popover.new(shell.aqua_drives_button)
        self.popover.set_position(Gtk.PositionType.TOP)
        self.popover.set_modal(True)
        self.popover.get_style_context().add_class("aqua-flyout")
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.get_style_context().add_class("aqua-flyout-root")
        root.pack_start(Gtk.Label(label="Connected locations", xalign=0), False, False, 0)
        self.status = Gtk.Label(label="", xalign=0)
        self.status.set_line_wrap(True)
        self.status.get_style_context().add_class("aqua-flyout-status")
        root.pack_start(self.status, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(272)
        scroll.set_propagate_natural_height(True)
        self.rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll.add(self.rows)
        root.pack_start(scroll, True, True, 0)
        refresh = Gtk.Button(label="↻  Refresh mounted locations")
        refresh.get_style_context().add_class("aqua-flyout-more")
        refresh.connect("clicked", lambda _button: self.refresh())
        root.pack_start(refresh, False, False, 0)
        self.popover.add(root)
        self.popover.connect("closed", lambda *_args: self._on_closed())

    def _clear(self):
        for child in tuple(self.rows.get_children()):
            child.destroy()

    def _on_closed(self):
        for handler in self.handlers:
            try:
                self.monitor.disconnect(handler)
            except (RuntimeError, TypeError):
                pass  # Shutdown can race a Gio monitor losing its connection.
        self.handlers.clear()
        self._clear()  # Discard private mount names and reference objects.

    def close(self):
        self._closed = True
        self._on_closed()
        self.popover.destroy()

    def show(self):
        if self._closed:
            return
        if hasattr(self.shell, "_aqua_notifications"):
            self.shell._aqua_notifications.popover.popdown()
        if hasattr(self.shell, "_aqua_calendar"):
            self.shell._aqua_calendar.popover.popdown()
        if hasattr(self.shell, "_aqua_flyouts"):
            for other in self.shell._aqua_flyouts.popovers.values():
                other.popdown()
        if not self.handlers:
            for signal in ("mount-added", "mount-removed", "mount-changed"):
                self.handlers.append(self.monitor.connect(signal, lambda *_args: self.refresh()))
        self.refresh()
        self.popover.show_all()
        self.popover.popup()

    def refresh(self):
        if self._closed:
            return
        self._clear()
        try:
            mounts = visible_mounts(self.monitor.get_mounts())
        except (OSError, RuntimeError):
            mounts = []
            self.status.set_text("Could not read connected locations")
        else:
            self.status.set_text("Open files before unmounting a drive" if mounts else
                                 "No mounted removable or network locations")
        for title, uri, mount in mounts:
            row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=6)
            caption = self.Gtk.Label(label=title, xalign=0)
            caption.set_line_wrap(True)
            caption.set_max_width_chars(20)
            row.pack_start(caption, True, True, 0)
            open_button = self.Gtk.Button(label="Open")
            open_button.get_style_context().add_class("aqua-flyout-more")
            open_button.get_accessible().set_name("Open location " + title)
            open_button.connect("clicked", lambda _button, destination=uri:
                                self.shell._open_uri(destination))
            row.pack_end(open_button, False, False, 0)
            try:
                can_unmount = mount.can_unmount()
            except Exception:
                can_unmount = False  # A mounted volume can vanish during redraw.
            if can_unmount:
                unmount = self.Gtk.Button(label="Unmount…")
                unmount.get_style_context().add_class("aqua-flyout-more")
                unmount.get_accessible().set_name("Unmount " + title)
                unmount.set_sensitive(not self.pending)
                unmount.connect("clicked", lambda _button, item=mount, label=title:
                                self._confirm_unmount(item, label))
                row.pack_end(unmount, False, False, 0)
            self.rows.pack_start(row, False, False, 0)
        self.rows.show_all()

    def _confirm_unmount(self, mount, title):
        if self._closed or self.pending:
            return
        try:
            if not mount.can_unmount():
                self.status.set_text("This location cannot be unmounted")
                return
        except Exception:
            self.status.set_text("The location is no longer available")
            return
        dialog = self.Gtk.MessageDialog(
            transient_for=self.shell.bar, modal=True,
            message_type=self.Gtk.MessageType.QUESTION,
            buttons=self.Gtk.ButtonsType.NONE,
            text="Unmount " + title[:70] + "?")
        dialog.format_secondary_text(
            "Close any open files first. Unmounting a busy drive may fail; no forced eject is used.")
        dialog.add_button("Keep mounted", self.Gtk.ResponseType.CANCEL)
        dialog.add_button("Unmount", self.Gtk.ResponseType.OK)
        approved = dialog.run() == self.Gtk.ResponseType.OK
        dialog.destroy()
        if not approved:
            return
        self.pending = True
        self.status.set_text("Requesting safe unmount…")

        def finished(item, response):
            try:
                if not item.unmount_with_operation_finish(response):
                    raise RuntimeError("Unmount was not confirmed by the system")
            except Exception as exc:
                feedback = "Unmount failed: " + str(exc)[:150]
            else:
                feedback = "Unmount complete"
            finally:
                self.pending = False
                if not self._closed and self.popover.get_visible():
                    self.refresh()
                    self.status.set_text(feedback)

        try:
            operation = self.Gtk.MountOperation.new(self.shell.bar)
            mount.unmount_with_operation(self.Gio.MountUnmountFlags.NONE, operation,
                                        None, finished)
        except Exception:
            self.pending = False
            self.status.set_text("Unmount unavailable; use the file manager's eject control")
