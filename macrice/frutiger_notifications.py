"""Small Aqua-style view of XFCE's real ricePop notification history.

XFCE remains the only notification daemon. No third-party action replay, new
history database or continuous polling is introduced by this popover.
"""

from __future__ import annotations

from .riceware import pop


def notification_preview(entries, *, limit=6):
    """Keep the popover bounded even if the host has a long notification log."""
    return tuple((entry.application[:45], entry.summary[:120], entry.is_read)
                 for entry in entries[:limit])


class AquaNotifications:
    def __init__(self, shell, Gtk):
        self.shell, self.Gtk = shell, Gtk
        self.controller = shell.frutiger_controller
        self._serial = 0
        self._busy = False
        self._syncing = False
        self._quiet = None
        self._history_available = False
        self.popover = Gtk.Popover.new(shell.aqua_notifications_button)
        self.popover.set_position(Gtk.PositionType.TOP)
        self.popover.set_modal(True)
        self.popover.get_style_context().add_class("aqua-flyout")

        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                            "aqua-flyout-root")
        root.set_size_request(294, -1)
        root.pack_start(shell._class(Gtk.Label(label="Your World · Notifications", xalign=0),
                                     "aqua-flyout-title"), False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        row.pack_start(Gtk.Label(label="Do Not Disturb", xalign=0), True, True, 0)
        self.dnd = Gtk.Switch()
        self.dnd.set_sensitive(False)
        self.dnd.get_accessible().set_name("XFCE Do Not Disturb")
        self.dnd.connect("notify::active", self._change_quiet)
        row.pack_end(self.dnd, False, False, 0)
        root.pack_start(row, False, False, 0)
        self.status = shell._class(Gtk.Label(label="Reading native notifications…", xalign=0),
                                   "aqua-flyout-status")
        self.status.set_line_wrap(True)
        root.pack_start(self.status, False, False, 0)
        self.entries = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        root.pack_start(self.entries, False, False, 0)
        self.mark_read = shell._class(Gtk.Button(label="Mark all read"), "aqua-flyout-more")
        self.mark_read.set_sensitive(False)
        self.mark_read.connect("clicked", lambda _button: self._action(pop.mark_read))
        root.pack_start(self.mark_read, False, False, 0)
        self.popover.add(root)
        self.popover.connect("closed", self._closed)

    def show(self):
        self.popover.show_all()
        self.popover.popup()
        self.refresh()

    def _forget(self):
        for child in tuple(self.entries.get_children()):
            child.destroy()

    def _closed(self, *_args):
        self._serial += 1
        self._busy = False
        self._quiet = None
        self._history_available = False
        self.dnd.set_sensitive(False)
        self.mark_read.set_sensitive(False)
        self._forget()  # Notification bodies must not persist in hidden GTK widgets.

    def close(self):
        self._closed()
        self.popover.destroy()

    def refresh(self, *, feedback=None):
        self._serial += 1
        serial = self._serial
        self._busy = True
        self.dnd.set_sensitive(False)
        self.mark_read.set_sensitive(False)
        self.status.set_text("Reading native notifications…")

        def read():
            state = pop.status()
            try:
                entries = pop.history() if state.history_available else ()
            except pop.NotificationUnavailable as exc:
                state = pop.NotificationStatus(False, None, state.quiet, str(exc))
                entries = ()
            return state, notification_preview(entries)

        def completed(response):
            if serial != self._serial or not self.popover.get_visible():
                return
            self._busy = False
            if response.error:
                self.status.set_text("Notifications unavailable: " + response.error[:160])
                self._forget()
                return
            state, entries = response.value
            self._quiet = state.quiet
            self._history_available = state.history_available
            self._syncing = True
            try:
                if state.quiet is not None:
                    self.dnd.set_active(state.quiet)
            finally:
                self._syncing = False
            self.dnd.set_sensitive(state.quiet is not None)
            self.mark_read.set_sensitive(bool(state.unread) and state.history_available)
            self.status.set_text(feedback or (state.reason if not state.history_available else
                                  "Notifications from your XFCE desktop"))
            self._forget()
            if not entries:
                label = self.Gtk.Label(label="No recent notifications" if state.history_available
                                       else "XFCE notification history is unavailable", xalign=0)
                label.set_line_wrap(True)
                self.entries.pack_start(label, False, False, 0)
            for application, summary, is_read in entries:
                caption = f"{application or 'Application'} · {summary or 'Notification'}"
                label = self.Gtk.Label(label=("• " if not is_read else "") + caption,
                                       xalign=0)
                label.set_line_wrap(True)
                label.set_max_width_chars(37)
                self.entries.pack_start(label, False, False, 0)
            self.entries.show_all()

        self.controller.submit("notification-view", read, completed)

    def _action(self, operation):
        if self._busy or not self._history_available:
            return
        serial = self._serial
        self._busy = True
        self.mark_read.set_sensitive(False)

        def completed(response):
            if serial != self._serial or not self.popover.get_visible():
                return
            self._busy = False
            self.refresh(feedback="Notification history updated" if not response.error else
                         "Update failed: " + response.error[:160])

        self.controller.submit("notification-action", operation, completed)

    def _change_quiet(self, switch, _property):
        if self._syncing or self._busy or self._quiet is None:
            return
        requested = bool(switch.get_active())
        if requested == self._quiet:
            return
        serial = self._serial
        self._busy = True
        self.dnd.set_sensitive(False)

        def completed(response):
            if serial != self._serial or not self.popover.get_visible():
                return
            self._busy = False
            self.refresh(feedback="Do Not Disturb updated" if not response.error else
                         "Do Not Disturb failed: " + response.error[:160])

        self.controller.submit("notification-quiet", lambda: pop.set_quiet_mode(requested),
                               completed)
