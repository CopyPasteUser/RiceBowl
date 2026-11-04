"""ChromeOS notification center backed by Xfce's existing D-Bus log.

No competing freedesktop notification daemon, no local copy of the log, no
replayed notification actions, and no synchronous I/O on the GTK thread.
"""

from __future__ import annotations

from collections import OrderedDict
import logging
import shutil
import threading

from . import chrome_notification_backend as backend


class ChromeNotifications:
    def __init__(self, shell, Gtk, GLib, Gio, parent, *, is_current):
        self.shell, self.Gtk, self.GLib, self.Gio = shell, Gtk, GLib, Gio
        self.is_current = is_current
        self._generation = 0
        self._busy = False
        self._syncing = False
        self._has_items = False
        self._unread = False
        self._badge_busy = False
        self._refreshing = False
        self._refresh_queued = False
        self._pending_feedback = None
        self._dbus = None
        self._subscription = 0

        self.surface = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                                    "chrome-notifications")
        parent.pack_start(self.surface, True, True, 0)
        status_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        status_row.pack_start(shell._class(
            Gtk.Label(label="Do Not Disturb", xalign=0), "chrome-notifications-label"),
            True, True, 0)
        self.dnd = Gtk.Switch()
        self.dnd.set_sensitive(False)
        self.dnd.set_valign(Gtk.Align.CENTER)
        self.dnd.get_accessible().set_name("Do Not Disturb for XFCE notifications")
        self.dnd.connect("notify::active", self._dnd_changed)
        status_row.pack_end(self.dnd, False, False, 0)
        self.surface.pack_start(status_row, False, False, 0)
        self.status = shell._class(Gtk.Label(label="Open notifications to read Xfce history.",
                                              xalign=0), "chrome-notifications-status")
        self.status.set_line_wrap(True)
        self.surface.pack_start(self.status, False, False, 0)
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.mark_all = shell._class(Gtk.Button(label="Mark all read"),
                                      "chrome-notifications-action")
        self.mark_all.set_sensitive(False)
        self.mark_all.connect("clicked", lambda _button: self._write(backend.mark_read))
        toolbar.pack_start(self.mark_all, True, True, 0)
        self.clear = shell._class(Gtk.Button(label="Clear all"),
                                   "chrome-notifications-action")
        self.clear.set_sensitive(False)
        self.clear.connect("clicked", self._ask_clear)
        toolbar.pack_start(self.clear, True, True, 0)
        self.surface.pack_start(toolbar, False, False, 0)

        self.confirm = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8),
                                    "chrome-notifications-confirm")
        caution = Gtk.Label(label="Delete all Xfce notification history permanently?",
                            xalign=0)
        caution.set_line_wrap(True)
        self.confirm.pack_start(caution, False, False, 0)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cancel = shell._class(Gtk.Button(label="Cancel"), "chrome-notifications-action")
        cancel.connect("clicked", lambda _button: self.confirm.hide())
        proceed = shell._class(Gtk.Button(label="Delete history"),
                                "chrome-notifications-danger")
        proceed.connect("clicked", lambda _button: self._write(backend.clear_notifications))
        buttons.pack_start(cancel, True, True, 0)
        buttons.pack_start(proceed, True, True, 0)
        self.confirm.pack_start(buttons, False, False, 0)
        self.confirm.set_no_show_all(True)
        self.surface.pack_start(self.confirm, False, False, 0)

        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        # The detail page already owns a scroller. Nested GtkScrolledWindows
        # steal wheel events and make long histories impossible to reach.
        self.surface.pack_start(self.list_box, False, False, 0)
        native = shell._class(Gtk.Button(label="Xfce notification preferences  ›"),
                               "chrome-notifications-action")
        native.set_sensitive(shutil.which("xfce4-notifyd-config") is not None)
        native.set_tooltip_text("Open installed XFCE notification settings" if native.get_sensitive()
                                else "xfce4-notifyd-config is not installed")
        native.connect("clicked", lambda _button: shell._open_tool("xfce4-notifyd-config"))
        self.surface.pack_start(native, False, False, 0)
        self._add_text("Notifications will appear here if XFCE history is enabled.")
        self.GLib.idle_add(self._connect_signals)

    def _connect_signals(self):
        def ready(_source, result):
            try:
                self._dbus = self.Gio.bus_get_finish(result)
                self._subscription = self._dbus.signal_subscribe(
                    backend.BUS_NAME, backend.LOG_INTERFACE, None,
                    backend.OBJECT_PATH, None, self.Gio.DBusSignalFlags.NONE,
                    self._log_changed)
            except (self.GLib.Error, OSError) as exc:
                logging.getLogger(__name__).debug("XFCE notification signals unavailable: %s",
                                                  type(exc).__name__)
            self.refresh_badge()

        self.Gio.bus_get(self.Gio.BusType.SESSION, None, ready)
        self.GLib.timeout_add_seconds(45, self._poll_badge)
        return False

    def _poll_badge(self):
        self.refresh_badge()
        return True

    def _log_changed(self, *_args):
        self.refresh_badge()
        if self.is_current():
            self.refresh()

    def refresh_badge(self):
        if self._badge_busy:
            return
        self._badge_busy = True

        def worker():
            try:
                unread = backend.has_unread()
            except backend.NotificationUnavailable:
                unread = None

            def apply():
                self._badge_busy = False
                badge = getattr(self.shell, "chrome_notifications_badge", None)
                if badge is not None:
                    badge.set_text("●" if unread else "")
                button = getattr(self.shell, "chrome_notifications_button", None)
                if button is not None:
                    button.get_accessible().set_name(
                        "Open unread notifications" if unread else "Open notifications")
                return False

            self.GLib.idle_add(apply)

        threading.Thread(target=worker, daemon=True,
                         name="ricebowl-chrome-notification-count").start()

    def _add_text(self, message):
        label = self.shell._class(self.Gtk.Label(label=message, xalign=0),
                                  "chrome-notifications-empty")
        label.set_line_wrap(True)
        self.list_box.pack_start(label, False, False, 0)

    def _clear_cards(self):
        for child in tuple(self.list_box.get_children()):
            child.destroy()

    def discard(self):
        """Forget private notification content when the popup closes."""
        self._generation += 1
        self._busy = False
        self._unread = self._has_items = False
        self._clear_cards()
        self._add_text("Open notifications to read Xfce history.")
        self.confirm.hide()

    def on_open(self):
        self.confirm.hide()
        self.refresh()

    def refresh(self):
        if not self.is_current() or self._busy:
            return
        if self._refreshing:
            self._refresh_queued = True
            return
        self._refreshing = True
        self._generation += 1
        generation = self._generation
        self.status.set_text("Reading Xfce notifications…")
        self.mark_all.set_sensitive(False)
        self.clear.set_sensitive(False)
        self.dnd.set_sensitive(False)

        def worker():
            try:
                entries = backend.list_notifications()
                error = None
            except backend.NotificationUnavailable:
                entries, error = (), "Xfce notification history is not available."
            dnd = backend.read_dnd()

            def apply():
                self._refreshing = False
                if generation != self._generation or not self.is_current():
                    if self._refresh_queued and self.is_current() and not self._busy:
                        self._refresh_queued = False
                        self.refresh()
                    return False
                self._syncing = True
                try:
                    self.dnd.set_active(bool(dnd))
                finally:
                    self._syncing = False
                self.dnd.set_sensitive(dnd is not None and not self._busy)
                self._render(entries, error)
                if self._refresh_queued:
                    self._refresh_queued = False
                    self.refresh()
                return False

            self.GLib.idle_add(apply)

        threading.Thread(target=worker, daemon=True,
                         name="ricebowl-chrome-notification-read").start()

    def _render(self, entries, error):
        self._clear_cards()
        self._has_items = bool(entries)
        self._unread = any(not item.is_read for item in entries)
        self.mark_all.set_sensitive(self._unread and not self._busy)
        self.clear.set_sensitive(self._has_items and not self._busy)
        self.status.set_text(error or self._pending_feedback or
                             (f"{len(entries)} recent notifications" if entries else
                              "No logged notifications. Logging may be disabled."))
        self._pending_feedback = None
        if not entries:
            self._add_text("Turn on notification logging in Xfce preferences to retain past alerts.")
        grouped = OrderedDict()
        for item in entries:
            grouped.setdefault(item.application, []).append(item)
        for application, items in grouped.items():
            self.list_box.pack_start(self.shell._class(
                self.Gtk.Label(label=application, xalign=0),
                "chrome-notifications-group"), False, False, 0)
            for item in items:
                self._add_item(item)
        self.list_box.show_all()

    def _add_item(self, item):
        card = self.shell._class(self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL,
                                              spacing=5), "chrome-notifications-card")
        if not item.is_read:
            card.get_style_context().add_class("chrome-notifications-unread")
        header = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=8)
        header.pack_start(self.shell._icon(item.icon, self.Gtk.IconSize.MENU),
                          False, False, 0)
        title = self.shell._class(self.Gtk.Label(label=item.summary, xalign=0),
                                  "chrome-notifications-summary")
        title.set_line_wrap(True)
        header.pack_start(title, True, True, 0)
        header.pack_end(self.shell._class(
            self.Gtk.Label(label=item.timestamp), "chrome-notifications-time"),
            False, False, 0)
        card.pack_start(header, False, False, 0)
        if item.body:
            body = self.shell._class(self.Gtk.Label(label=item.body, xalign=0),
                                     "chrome-notifications-body")
            body.set_line_wrap(True)
            body.set_max_width_chars(48)
            card.pack_start(body, False, False, 0)
        actions = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=5)
        if not item.is_read:
            read = self.shell._class(self.Gtk.Button(label="Mark read"),
                                     "chrome-notifications-action")
            read.connect("clicked", lambda _button, entry_id=item.identifier:
                         self._write(lambda: backend.mark_read((entry_id,))))
            actions.pack_start(read, False, False, 0)
        dismiss = self.shell._class(self.Gtk.Button(label="Dismiss"),
                                    "chrome-notifications-action")
        dismiss.get_accessible().set_name("Dismiss notification: " + item.summary)
        dismiss.connect("clicked", lambda _button, entry_id=item.identifier:
                        self._write(lambda: backend.delete_notification(entry_id)))
        actions.pack_end(dismiss, False, False, 0)
        card.pack_start(actions, False, False, 0)
        self.list_box.pack_start(card, False, False, 0)

    def _ask_clear(self, *_args):
        self.confirm.show_all()

    def _dnd_changed(self, switch, _property):
        if not self._syncing:
            enabled = switch.get_active()
            self._write(lambda: backend.set_dnd(enabled))

    def _write(self, writer):
        if self._busy or not self.is_current():
            return
        self._busy = True
        self._generation += 1
        generation = self._generation
        self.mark_all.set_sensitive(False)
        self.clear.set_sensitive(False)
        self.dnd.set_sensitive(False)
        self.confirm.hide()
        self.status.set_text("Applying and verifying Xfce notification state…")

        def worker():
            error = None
            try:
                writer()
            except (backend.NotificationUnavailable, ValueError) as exc:
                error = str(exc)

            def apply():
                if generation != self._generation:
                    return False
                self._busy = False
                if error:
                    self._pending_feedback = error
                self.refresh()
                self.refresh_badge()
                return False

            self.GLib.idle_add(apply)

        threading.Thread(target=worker, daemon=True,
                         name="ricebowl-chrome-notification-write").start()
