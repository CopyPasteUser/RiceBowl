"""Windows 7 Aero notification flyouts over verified shared Linux backends.

The controls intentionally reuse XP's asynchronous backend transactions, but
own their separate Windows 7 layout, title bar and taskbar anchoring style.
"""

from __future__ import annotations

from .luna_tray import LunaTray
from .riceware import pop


def recent_alerts(items, limit=6):
    """Show only recent, already-sanitized native history; never replay actions."""
    return tuple(items)[:limit]


class Win7Tray(LunaTray):
    """Windows 7 status flyouts; never expose an unverified hardware toggle."""

    def __init__(self, shell, Gtk, GLib):
        super().__init__(shell, Gtk, GLib)
        self._alerts_busy = False
        self._alerts_writing = False
        self._alerts_watch = None
        self._alerts_button = None
        self._alerts_error = None

    def close(self):
        if self._alerts_watch is not None:
            self._alerts_watch.close()
            self._alerts_watch = None
        super().close()

    def _alerts_changed(self):
        self.refresh_alert_indicator()
        if self.popovers.get("alerts") is not None and self.popovers["alerts"].get_visible():
            self.refresh_alerts()

    def refresh_alert_indicator(self):
        if self._alerts_button is None:
            return
        self._requests.submit("alerts-indicator", pop.status, self._indicator_ready)

    def _indicator_ready(self, reply):
        if self._alerts_button is None:
            return
        state = None if reply.error else reply.value
        self._alerts_button.set_tooltip_text(
            "Action Center · Unread notifications" if state and state.unread else
            "Action Center · Quiet mode enabled" if state and state.quiet else
            "Action Center · XFCE history unavailable" if not state or not state.history_available else
            "Action Center · No unread notifications")
        context = self._alerts_button.get_style_context()
        if state and state.unread:
            context.add_class("win7-alert-unread")
        else:
            context.remove_class("win7-alert-unread")

    def _alerts(self, body):
        Gtk = self.Gtk
        self._heading(body, "Action Center", "dialog-information")
        self.alerts_status = self._label("Open to check notification history")
        body.pack_start(self.alerts_status, False, False, 0)
        self.alerts_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.pack_start(self.alerts_list, False, False, 0)
        self.alerts_mark = self.shell._class(Gtk.Button(label="Mark all as read"),
                                             "win7-tray-link")
        self.alerts_mark.set_sensitive(False)
        self.alerts_mark.connect("clicked", lambda _button: self._mark_alerts())
        body.pack_start(self.alerts_mark, False, False, 0)
        body.pack_start(self._button("Notification settings…", ("xfce4-notifyd-config",)),
                        False, False, 0)

    def _clear_alert_items(self):
        for widget in tuple(self.alerts_list.get_children()):
            widget.destroy()

    def refresh_alerts(self):
        if self._alerts_busy or self._alerts_writing:
            return
        self._alerts_busy = True
        self.alerts_mark.set_sensitive(False)
        self.alerts_status.set_text("Reading XFCE notification history…")
        self._requests.submit("alerts-history", pop.history, self._alerts_ready)

    def _alerts_ready(self, reply):
        self._alerts_busy = False
        if not self.popovers["alerts"].get_visible():
            return
        self._clear_alert_items()
        if reply.error:
            self.alerts_status.set_text("Notification history unavailable: " + reply.error)
            self.alerts_list.show_all()
            return
        entries = reply.value
        self.alerts_mark.set_sensitive(any(not entry.is_read for entry in entries))
        self.alerts_status.set_text(self._alerts_error or (
            f"{len(entries)} logged notifications" if entries else
            "No notifications in XFCE history. Logging may be disabled."))
        self._alerts_error = None
        for entry in recent_alerts(entries):
            item = self.shell._class(
                self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=2),
                "win7-alert-item")
            if not entry.is_read:
                item.get_style_context().add_class("win7-alert-item-unread")
            item.pack_start(self._label(entry.application + " · " + entry.timestamp),
                            False, False, 0)
            item.pack_start(self._label(entry.summary, "win7-alert-summary"),
                            False, False, 0)
            if entry.body:
                item.pack_start(self._label(entry.body), False, False, 0)
            self.alerts_list.pack_start(item, False, False, 0)
        if len(entries) > 6:
            self.alerts_list.pack_start(self._label("Showing the 6 most recent alerts"),
                                        False, False, 0)
        self.alerts_list.show_all()

    def _mark_alerts(self):
        if self._alerts_writing or self._alerts_busy:
            return
        self._alerts_writing = True
        self.alerts_mark.set_sensitive(False)
        self.alerts_status.set_text("Marking notifications as read…")
        self._requests.submit("alerts-write", pop.mark_read, self._marked_alerts)

    def _marked_alerts(self, reply):
        self._alerts_writing = False
        self._alerts_error = "Could not mark notifications: " + reply.error if reply.error else None
        self.refresh_alert_indicator()
        if self.popovers["alerts"].get_visible():
            self.refresh_alerts()

    def announce(self, message):
        """Own-device balloons respect native quiet mode without blocking GTK."""
        def finished(reply):
            if reply.error is None and reply.value is False and self.shell.luna_balloon:
                self.shell.luna_balloon.show(message)

        self._requests.submit("alert-quiet", pop.quiet_mode, finished)

    def install(self, name, anchor):
        popup = super().install(name, anchor)
        popup.set_title("Windows 7 " + name.title())
        popup.get_style_context().add_class("win7-tray-popup")
        scroll = popup.get_child()
        scroll.get_style_context().add_class("win7-tray-scroll")
        body = scroll.get_child()
        if isinstance(body, self.Gtk.Viewport):
            body = body.get_child()
        body.get_style_context().add_class("win7-tray-body")
        if name == "alerts":
            self._alerts_button = anchor
            self._alerts(body)
            popup.connect("hide", lambda _popup: self._clear_alert_items())
            try:
                self._alerts_watch = pop.watch(self._alerts_changed)
            except pop.NotificationUnavailable:
                pass
            self.refresh_alert_indicator()
        return popup

    def toggle(self, name):
        super().toggle(name)
        if name == "alerts" and self.popovers[name].get_visible():
            self.refresh_alerts()

    def _label(self, value, kind="win7-tray-caption"):
        label = super()._label(value, kind)
        label.get_style_context().add_class("win7-tray-caption")
        return label

    def _button(self, label, command, *, css="win7-tray-link"):
        button = super()._button(label, command, css=css)
        button.get_style_context().add_class("win7-tray-link")
        return button

    def _heading(self, body, name, icon):
        Gtk = self.Gtk
        # The original Windows 7 flyouts have a small translucent blue title
        # strip above a light device/content area, unlike XP's ivory heading.
        header = self.shell._class(
            Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8),
            "win7-tray-heading")
        name_icon = {
            "Volume": "audio-volume-high",
            "Network connections": "network-wireless",
            "Power": "battery",
            "Bluetooth devices": "bluetooth-active",
            "Date and time": "x-office-calendar",
        }.get(name, icon)
        header.pack_start(self.shell._icon(name_icon, Gtk.IconSize.LARGE_TOOLBAR),
                          False, False, 0)
        header.pack_start(self._label(name, "win7-tray-title"), True, True, 0)
        body.pack_start(header, False, False, 0)

    def _audio(self, body):
        """Period-style upright volume control with a compact output drawer."""
        Gtk = self.Gtk
        self._heading(body, "Volume", "audio-volume-high")
        self.audio_label = self._label("Checking sound output…")
        body.pack_start(self.audio_label, False, False, 0)
        volume_row = self.shell._class(
            Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12),
            "win7-tray-volume-row")
        self.audio_scale = Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 5)
        self.audio_scale.set_draw_value(False)
        self.audio_scale.set_size_request(46, 134)
        self.audio_scale.set_sensitive(False)
        self.audio_scale.get_accessible().set_name("System output volume")
        self.audio_scale.connect("value-changed", self.shell._queue_volume_change)
        volume_row.pack_start(self.audio_scale, False, False, 8)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right.pack_start(self._label("Speakers", "win7-tray-section"), False, False, 4)
        self.audio_mute = self.shell._class(Gtk.ToggleButton(label="Mute"),
                                            "win7-tray-toggle")
        self.audio_mute.set_sensitive(False)
        self.audio_mute.get_accessible().set_name("Mute system output")
        self.audio_mute.connect("clicked", self.shell._toggle_output_mute)
        right.pack_start(self.audio_mute, False, False, 0)
        right.pack_start(self._button("Sound settings…", ("pavucontrol", "xfce4-mixer")),
                         False, False, 0)
        volume_row.pack_start(right, True, True, 0)
        body.pack_start(volume_row, False, False, 0)

        devices = self.shell._class(Gtk.Expander(label="Playback devices"),
                                    "win7-tray-devices")
        self.output_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        devices.add(self.output_list)
        body.pack_start(devices, False, False, 0)
