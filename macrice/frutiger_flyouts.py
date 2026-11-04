"""Compact native Aqua device popovers anchored to the actual tray buttons.

No additional polling or daemon: an existing 20-second hardware monitor
refreshes the popover; its sound writes use the verified shared backend.
"""

from __future__ import annotations


class AquaFlyouts:
    def __init__(self, shell, Gtk):
        self.shell, self.Gtk = shell, Gtk
        self.popovers = {}
        self.labels = {}
        self.audio_scale = None
        self.audio_mute = None

    def show(self, kind: str):
        if kind not in ("network", "audio", "battery"):
            return
        popover = self.popovers.get(kind)
        if popover is None:
            popover = self._build(kind)
            self.popovers[kind] = popover
        for other_kind, other in self.popovers.items():
            if other_kind != kind:
                other.popdown()
        self.sync(getattr(self.shell, "_last_status", None))
        popover.show_all()
        popover.popup()
        self.shell._refresh_status_async()

    def _build(self, kind):
        Gtk = self.Gtk
        shell = self.shell
        button = shell._status_widgets[kind][0]
        popover = Gtk.Popover.new(button)
        popover.set_position(Gtk.PositionType.TOP)
        popover.set_modal(True)
        popover.get_style_context().add_class("aqua-flyout")

        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                            "aqua-flyout-root")
        root.set_size_request(272, -1)
        hero = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                            "aqua-flyout-heading")
        title, icon = {
            "network": ("Connections", "network-wireless"),
            "audio": ("Sound & media", "audio-volume-high"),
            "battery": ("Power & battery", "battery"),
        }[kind]
        hero.pack_start(shell._icon(icon, Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
        hero.pack_start(shell._class(Gtk.Label(label=title, xalign=0),
                                     "aqua-flyout-title"), True, True, 0)
        root.pack_start(hero, False, False, 0)

        label = shell._class(Gtk.Label(label="Checking actual device status…", xalign=0),
                             "aqua-flyout-status")
        label.set_line_wrap(True)
        root.pack_start(label, False, False, 0)
        self.labels[kind] = label

        if kind == "audio":
            scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
            scale.set_draw_value(False)
            scale.set_sensitive(False)
            scale.get_accessible().set_name("Change system output volume")
            scale.connect("value-changed", shell._queue_volume_change)
            root.pack_start(scale, False, False, 0)
            self.audio_scale = scale
            mute = shell._class(Gtk.ToggleButton(label="Mute output"), "aqua-flyout-mute")
            mute.get_accessible().set_name("Mute or unmute actual audio output")
            mute.set_sensitive(False)
            mute.connect("clicked", shell._toggle_output_mute)
            root.pack_start(mute, False, False, 0)
            self.audio_mute = mute

        open_button = shell._class(Gtk.Button(label="More " + title.lower() + " settings  ›"),
                                   "aqua-flyout-more")
        open_button.get_accessible().set_name("Open Aqua Control Center " + title)

        def open_detail(_button):
            popover.popdown()
            shell._show_aqua_control({"network": "connections", "audio": "sound",
                                      "battery": "power"}[kind])

        open_button.connect("clicked", open_detail)
        root.pack_start(open_button, False, False, 0)
        popover.add(root)
        return popover

    def sync(self, status):
        for kind, label in self.labels.items():
            if status is None:
                label.set_text("Device information unavailable — checking again")
            elif kind == "network":
                label.set_text({"wifi": "Wi-Fi connection active",
                                "ethernet": "Wired connection active",
                                "offline": "No active network route"}.get(
                                    status.network, "Network status unavailable"))
            elif kind == "battery":
                battery = status.battery
                label.set_text(f"{battery.percent}% · {battery.label}" if battery else
                               "No battery reported by Linux")
            else:
                sound = status.sound
                label.set_text("Audio backend unavailable" if sound.percent is None else
                               f"Output {sound.percent}%" + (" · Muted" if sound.muted else ""))

        if self.audio_scale is None:
            return
        sound = status.sound if status else None
        percent = sound.percent if sound else None
        muted = sound.muted if sound else None
        self.audio_scale.set_sensitive(percent is not None)
        self.audio_mute.set_sensitive(muted is not None and not self.shell._mute_writing)
        if percent is not None and not self.shell._volume_writing and self.shell._volume_queued is None:
            self.shell._volume_programmatic = True
            try:
                self.audio_scale.set_value(min(100, percent))
            finally:
                self.shell._volume_programmatic = False
        if muted is not None and not self.shell._mute_writing:
            self.audio_mute.set_active(muted)
