"""Windows 10 renderer adapter for the shared Riceware device/notification APIs.

Hardware and XFCE D-Bus I/O never run on GTK's main thread.  Only verified
readbacks change UI switches; notifications stay owned by xfce4-notifyd.
"""

from __future__ import annotations

import logging

from .riceware import pop, spice
from .riceware.worker import LatestRequestRunner

LOG = logging.getLogger(__name__)
TOGGLES = ("wifi", "bluetooth", "quiet")


def group_notifications(items):
    """Keep application groups in recency order without duplicating XFCE data."""
    groups = {}
    for item in items:
        groups.setdefault(item.application, []).append(item)
    return tuple((app, tuple(entries)) for app, entries in groups.items())


def switch_state(results):
    """Return (enabled, available) without guessing from failed probes."""
    wifi, bluetooth, quiet = results
    return {
        "wifi": (wifi.value if wifi.status == "ok" else None,
                 wifi.status == "ok" and type(wifi.value) is bool),
        "bluetooth": (bluetooth.value.powered if bluetooth.status == "ok" else None,
                      bluetooth.status == "ok" and
                      type(bluetooth.value.powered) is bool),
        "quiet": (quiet, type(quiet) is bool),
    }


class TenController:
    """A bounded, closeable Riceware adapter belonging to one Windows 10 shell."""

    def __init__(self, shell, Gtk, GLib, *, runner=None):
        self.shell = shell
        self.Gtk = Gtk
        self.runner = runner if runner is not None else LatestRequestRunner(GLib.idle_add)
        self.switches = {}
        self.history_box = None
        self.history_message = None
        self.mark_button = None
        self.clear_button = None
        self.confirmation = None
        self.feedback = None
        self.opened = False
        self.closed = False
        self.epoch = 0
        self._watch = None
        self._ids = ()
        self._states = {name: (None, False) for name in TOGGLES}
        self._writing = set()
        self._clearing_history = False

    def bind(self, *, switches, history_box, history_message, mark_button, feedback,
             clear_button=None, confirmation=None):
        self.switches = switches
        self.history_box = history_box
        self.history_message = history_message
        self.mark_button = mark_button
        self.clear_button = clear_button
        self.confirmation = confirmation
        self.feedback = feedback
        for name, button in switches.items():
            button.set_sensitive(False)
            button.connect("clicked", self._toggle_clicked, name)
        mark_button.connect("clicked", lambda _button: self.mark_read())

    def refresh_status(self, callback):
        def done(response):
            result = response.value
            callback(result.value if response.error is None and
                     result.status == "ok" else None)

        self.runner.submit("ten-desktop", lambda: spice.read("desktop_status"), done)

    def change_audio(self, action, value, callback):
        def done(response):
            result = response.value
            if response.error or result.status != "ok":
                callback(None, response.error or result.reason or "Device unavailable")
            else:
                callback(result.value, None)

        self.runner.submit(action, lambda: spice.change(action, value), done)

    def on_open(self):
        if self.closed:
            return
        self.opened = True
        self.epoch += 1
        if self._watch is None:
            try:
                self._watch = pop.watch(self.refresh_history)
            except (pop.NotificationUnavailable, RuntimeError, OSError) as exc:
                LOG.debug("Win10 native notification watch unavailable: %s", exc)
        self.refresh_switches()
        self.refresh_history()

    def discard(self):
        """Remove private notification text when the flyout is dismissed."""
        self.opened = False
        self.epoch += 1
        self._ids = ()
        if self.history_box is not None:
            for child in self.history_box.get_children():
                self.history_box.remove(child)
        if self.mark_button is not None:
            self.mark_button.set_sensitive(False)
        if self.clear_button is not None:
            self.clear_button.set_sensitive(False)
        if self.confirmation is not None:
            self.confirmation.hide()

    def _message(self, message):
        if self.feedback is not None and self.opened:
            self.feedback.set_text(message)

    def refresh_switches(self):
        if not self.opened or self.closed:
            return
        epoch = self.epoch

        def probe():
            return (spice.read("wifi"), spice.read("bluetooth"), pop.quiet_mode())

        def done(response):
            if epoch != self.epoch or not self.opened:
                return
            if response.error:
                self._message("Quick actions temporarily unavailable")
                return
            self._states = switch_state(response.value)
            for name, button in self.switches.items():
                enabled, available = self._states[name]
                button.set_sensitive(available and name not in self._writing)
                if available:
                    button.set_active(enabled)
                else:
                    button.set_active(False)
                button.set_tooltip_text(
                    "Toggle " + {"wifi": "Wi-Fi", "bluetooth": "Bluetooth",
                                  "quiet": "Focus assist (Do Not Disturb)"}[name]
                    if available else "System backend unavailable")

        self.runner.submit("ten-switches", probe, done)

    def _toggle_clicked(self, button, name):
        enabled, available = self._states[name]
        if not available or self.closed or name in self._writing:
            button.set_active(bool(enabled))
            return
        requested = not enabled
        self._writing.add(name)
        button.set_active(enabled)  # GTK toggles optimistically; await verification.
        button.set_sensitive(False)
        self._message("Applying " + name + "…")
        epoch = self.epoch

        def change():
            if name == "quiet":
                return pop.set_quiet_mode(requested)
            return spice.change("wifi" if name == "wifi" else "bluetooth_power",
                                requested)

        def done(response):
            self._writing.discard(name)
            if epoch != self.epoch or not self.opened:
                if self.opened:
                    self.refresh_switches()
                return
            result = response.value
            success = (response.error is None and
                       (result is requested if name == "quiet" else
                        result.status == "ok"))
            if success:
                self._message("Setting applied")
            else:
                self._message("Could not change " + name + ": " +
                              (response.error or (result.reason if name != "quiet" else
                                                  "Unverified state")))
            self.refresh_switches()
            self.shell._refresh_status_async()

        self.runner.submit("ten-toggle-" + name, change, done)

    def refresh_history(self):
        if not self.opened or self.closed or self.history_box is None or self._clearing_history:
            return
        epoch = self.epoch
        self.history_message.set_text("Loading notifications…")

        def done(response):
            if epoch != self.epoch or not self.opened:
                return
            if response.error:
                self.history_message.set_text("Notification history unavailable")
                self._message(response.error)
                self._ids = ()
                for child in self.history_box.get_children():
                    self.history_box.remove(child)
                self.mark_button.set_sensitive(False)
                if self.clear_button is not None:
                    self.clear_button.set_sensitive(False)
                return
            items = response.value[:20]
            self._ids = tuple(item.identifier for item in response.value if not item.is_read)
            for child in self.history_box.get_children():
                self.history_box.remove(child)
            self.mark_button.set_sensitive(bool(self._ids))
            if self.clear_button is not None:
                self.clear_button.set_sensitive(bool(response.value))
            self.history_message.set_text("" if items else "You're all caught up")
            for application, entries in group_notifications(items):
                self.history_box.pack_start(self.shell._class(
                    self.Gtk.Label(label=f"{application}  ·  {len(entries)}", xalign=0),
                    "ten-notification-group"), False, False, 0)
                for item in entries:
                    self._add_notification(item)
            self.history_box.show_all()

        self.runner.submit("ten-history", pop.history, done)

    def _add_notification(self, item):
        Gtk = self.Gtk
        card = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4),
                                 "ten-notification-card")
        if not item.is_read:
            card.get_style_context().add_class("ten-notification-unread")
        heading = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        heading.pack_start(self.shell._icon(item.icon, Gtk.IconSize.MENU), False, False, 0)
        title = self.shell._class(Gtk.Label(label=item.summary or item.application,
                                              xalign=0), "ten-notification-title")
        title.set_line_wrap(True)
        title.set_selectable(True)
        heading.pack_start(title, True, True, 0)
        heading.pack_end(self.shell._class(
            Gtk.Label(label=item.timestamp), "ten-notification-time"), False, False, 0)
        card.pack_start(heading, False, False, 0)
        if item.body:
            body = self.shell._class(Gtk.Label(label=item.body, xalign=0), "ten-muted")
            body.set_line_wrap(True)
            body.set_selectable(True)
            card.pack_start(body, False, False, 0)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        if not item.is_read:
            read = self.shell._class(Gtk.Button(label="Mark read"), "ten-notification-dismiss")
            read.connect("clicked", lambda _button, identifier=item.identifier:
                         self._history_change(lambda: pop.mark_read((identifier,))))
            controls.pack_start(read, False, False, 0)
        dismiss = self.shell._class(Gtk.Button(label="Dismiss"), "ten-notification-dismiss")
        dismiss.get_accessible().set_name("Dismiss notification from " + item.application)
        dismiss.connect("clicked", lambda _button, identifier=item.identifier:
                        self.dismiss(identifier))
        controls.pack_end(dismiss, False, False, 0)
        card.pack_start(controls, False, False, 0)
        self.history_box.pack_start(card, False, False, 0)

    def clear_history(self):
        """Clear only after the user confirms; XFCE remains the log owner."""
        if not self.opened or self.closed or self._clearing_history:
            return
        if self.confirmation is not None:
            self.confirmation.hide()
        self._clearing_history = True
        if self.clear_button is not None:
            self.clear_button.set_sensitive(False)
        self.mark_button.set_sensitive(False)
        self._message("Deleting XFCE notification history…")
        epoch = self.epoch

        def done(response):
            self._clearing_history = False
            if epoch != self.epoch or not self.opened:
                return
            self._message("Notification history cleared" if response.error is None else
                          "Could not clear notifications: " + response.error)
            self.refresh_history()

        self.runner.submit("ten-clear-history", pop.clear_history, done)

    def mark_read(self):
        if not self._ids or not self.opened:
            return
        ids = self._ids
        self.mark_button.set_sensitive(False)
        self._history_change(lambda: pop.mark_read(ids))

    def dismiss(self, identifier):
        if self.opened:
            self._history_change(lambda: pop.dismiss(identifier))

    def _history_change(self, operation):
        epoch = self.epoch

        def done(response):
            if epoch != self.epoch or not self.opened:
                return
            if response.error:
                self._message("Notification update failed: " + response.error)
            self.refresh_history()

        self.runner.submit("ten-notification-change", operation, done)

    def close(self):
        if self.closed:
            return
        self.discard()
        self.closed = True
        if self._watch is not None:
            self._watch.close()
            self._watch = None
        self.runner.close()
