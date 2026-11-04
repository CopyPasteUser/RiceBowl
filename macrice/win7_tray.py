"""Windows 7 Aero notification flyouts over verified shared Linux backends.

The controls intentionally reuse XP's asynchronous backend transactions, but
own their separate Windows 7 layout, title bar and taskbar anchoring style.
"""

from __future__ import annotations

from .luna_tray import LunaTray


class Win7Tray(LunaTray):
    """Windows 7 status flyouts; never expose an unverified hardware toggle."""

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
        return popup

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
