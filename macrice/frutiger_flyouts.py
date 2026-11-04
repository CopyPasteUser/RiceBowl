"""Compact native Aqua device popovers anchored to the actual tray buttons.

No additional polling or daemon: an existing 20-second hardware monitor
refreshes the popover; its sound writes use the verified shared backend.
"""

from __future__ import annotations


class AquaFlyouts:
    def __init__(self, shell, Gtk):
        self.shell, self.Gtk = shell, Gtk
        self.controller = shell.frutiger_controller
        self.popovers = {}
        self.labels = {}
        self.details = {}
        self.detail_status = {}
        self._generations = {}
        self._busy = set()
        self._confirming = set()
        self.audio_scale = None
        self.audio_mute = None

    def show(self, kind: str):
        if kind not in ("network", "audio", "battery", "bluetooth"):
            return
        if hasattr(self.shell, "_aqua_notifications"):
            self.shell._aqua_notifications.popover.popdown()
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
        self._refresh_details(kind)

    def close(self):
        for kind, popover in tuple(self.popovers.items()):
            self._discard(kind)
            popover.destroy()
        self.popovers.clear()

    def _discard(self, kind):
        self._generations[kind] = self._generations.get(kind, 0) + 1
        self._busy.discard(kind)
        self._confirming.discard(kind)
        if kind in self.details:
            self._clear(self.details[kind])

    @staticmethod
    def _clear(box):
        for child in tuple(box.get_children()):
            child.destroy()

    def _build(self, kind):
        Gtk = self.Gtk
        shell = self.shell
        button = (shell.aqua_bluetooth_button if kind == "bluetooth"
                  else shell._status_widgets[kind][0])
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
            "bluetooth": ("Bluetooth devices", "bluetooth-active"),
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

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.details[kind] = details
        root.pack_start(details, False, False, 0)
        detail_status = shell._class(Gtk.Label(label="", xalign=0), "aqua-flyout-status")
        detail_status.set_line_wrap(True)
        self.detail_status[kind] = detail_status
        root.pack_start(detail_status, False, False, 0)
        refresh = shell._class(Gtk.Button(label="↻  Refresh devices"), "aqua-flyout-more")
        refresh.get_accessible().set_name("Refresh actual " + title.lower() + " devices")
        refresh.connect("clicked", lambda _button: self._refresh_details(kind))
        root.pack_start(refresh, False, False, 0)

        open_button = shell._class(Gtk.Button(label="More " + title.lower() + " settings  ›"),
                                   "aqua-flyout-more")
        open_button.get_accessible().set_name("Open Aqua Control Center " + title)

        def open_detail(_button):
            popover.popdown()
            shell._show_aqua_control({"network": "connections", "audio": "sound",
                                      "battery": "power", "bluetooth": "connections"}[kind],
                                     "Bluetooth devices" if kind == "bluetooth" else None)

        open_button.connect("clicked", open_detail)
        root.pack_start(open_button, False, False, 0)
        popover.add(root)
        popover.connect("closed", lambda *_args: self._discard(kind))
        return popover

    def _read_details(self, kind):
        hw = self.controller.hardware
        if kind == "network":
            return hw.read_wifi_radio(), hw.read_wifi_networks()
        if kind == "bluetooth":
            return hw.read_bluetooth()
        if kind == "audio":
            return hw.read_sound_outputs()
        return hw.read_power_profiles()

    def _refresh_details(self, kind, *, feedback=None):
        if kind in self._busy or kind not in self.popovers or not self.popovers[kind].get_visible():
            return
        self._busy.add(kind)
        self._confirming.discard(kind)
        self._generations[kind] = self._generations.get(kind, 0) + 1
        generation = self._generations[kind]
        self.detail_status[kind].set_text("Reading actual Linux devices…")
        self.details[kind].set_sensitive(False)

        def complete(response):
            if (generation != self._generations.get(kind)
                    or not self.popovers[kind].get_visible()):
                return
            self._busy.discard(kind)
            if response.error:
                self._clear(self.details[kind])
                self.detail_status[kind].set_text("Device unavailable: " + response.error[:165])
                return
            self._render_details(kind, response.value)
            self.details[kind].set_sensitive(True)
            self.detail_status[kind].set_text(feedback or "")

        self.controller.submit("aqua-read-" + kind,
                               lambda: self._read_details(kind), complete)

    def _change(self, kind, operation):
        if (kind in self._busy or kind not in self.popovers
                or not self.popovers[kind].get_visible()):
            return
        self._busy.add(kind)
        self._generations[kind] = self._generations.get(kind, 0) + 1
        generation = self._generations[kind]
        self.details[kind].set_sensitive(False)
        self.detail_status[kind].set_text("Applying and verifying…")

        def complete(response):
            if (generation != self._generations.get(kind)
                    or not self.popovers[kind].get_visible()):
                return
            self._busy.discard(kind)
            if response.error:
                self.details[kind].set_sensitive(True)
                self.detail_status[kind].set_text("Change failed: " + response.error[:165])
            else:
                self._refresh_details(kind, feedback="Change applied and verified")

        self.controller.submit("aqua-write-" + kind, operation, complete)

    def _row(self, parent, title, *, button=None, action=None):
        Gtk = self.Gtk
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label(label=title, xalign=0)
        label.set_line_wrap(True)
        label.set_max_width_chars(27)
        row.pack_start(label, True, True, 0)
        if button is not None:
            control = self.shell._class(Gtk.Button(label=button), "aqua-flyout-more")
            control.get_accessible().set_name(button + ": " + title)
            control.connect("clicked", lambda _button: action())
            row.pack_end(control, False, False, 0)
        parent.pack_start(row, False, False, 0)

    def _confirm_radio_off(self, kind, action):
        """Explicit second click: disabling a radio can drop remote sessions."""
        if kind in self._confirming:
            return
        self._confirming.add(kind)
        box = self.details[kind]
        warning = self.Gtk.Label(label="This may disconnect your wireless devices.", xalign=0)
        warning.set_line_wrap(True)
        box.pack_start(warning, False, False, 0)
        self._row(box, "Confirm radio shutdown", button="Turn off",
                  action=lambda: self._change(kind, action))
        self._row(box, "Keep radio enabled", button="Cancel",
                  action=lambda: self._refresh_details(kind))
        box.show_all()

    def _render_details(self, kind, snapshot):
        box = self.details[kind]
        self._clear(box)
        hw = self.controller.hardware
        if kind == "network":
            enabled, networks = snapshot
            if enabled is None:
                self._row(box, "Wi-Fi radio unavailable (NetworkManager not detected)")
            else:
                self._row(box, "Wi-Fi radio: " + ("On" if enabled else "Off"),
                          button="Turn off" if enabled else "Turn on",
                          action=(lambda: self._confirm_radio_off("network", lambda:
                                      hw.set_wifi_radio(False))) if enabled else
                                  lambda: self._change("network", lambda: hw.set_wifi_radio(True)))
            if not networks:
                self._row(box, "No Wi-Fi networks reported")
            for network in networks[:5]:
                caption = ("● " if network.connected else "") + (
                    f"{network.ssid[:36]} · {network.signal}%")
                if enabled is True:
                    self._row(box, caption,
                              button="Disconnect" if network.connected else "Connect",
                              action=(lambda: self._change("network", hw.disconnect_wifi))
                              if network.connected else
                              (lambda ssid=network.ssid: self._change(
                                  "network", lambda: hw.connect_wifi(ssid))))
                else:
                    self._row(box, caption)
        elif kind == "bluetooth":
            state = snapshot
            if state.powered is None:
                self._row(box, "Bluetooth adapter unavailable or blocked")
            else:
                self._row(box, "Bluetooth: " + ("On" if state.powered else "Off") +
                          (" · " + state.backend if state.backend else ""),
                          button="Turn off" if state.powered else "Turn on",
                          action=(lambda: self._confirm_radio_off("bluetooth", lambda:
                                      hw.set_bluetooth_power(False))) if state.powered else
                                  lambda: self._change("bluetooth", lambda: hw.set_bluetooth_power(True)))
            if not state.devices:
                self._row(box, "No paired Bluetooth devices reported")
            for device in state.devices[:5]:
                caption = device.name[:42] + (" · Connected" if device.connected else "")
                if state.powered is True and device.paired:
                    self._row(box, caption,
                              button="Disconnect" if device.connected else "Connect",
                              action=lambda item=device: self._change(
                                  "bluetooth", lambda: hw.set_bluetooth_connection(
                                      item.address, not item.connected)))
                else:
                    self._row(box, caption)
        elif kind == "audio":
            outputs = snapshot
            if not outputs:
                self._row(box, "No audio output devices reported")
            for output in outputs[:5]:
                self._row(box, output.label[:48] + (" · Active" if output.active else ""),
                          button=None if output.active else "Use",
                          action=(lambda name=output.name: self._change(
                              "audio", lambda: hw.set_sound_output(name))))
        else:
            current, available = snapshot
            if not current or not available:
                self._row(box, "Power profiles unavailable on this device")
            else:
                for profile in available[:3]:
                    self._row(box, profile.replace("-", " ").title() +
                              (" · Active" if profile == current else ""),
                              button=None if profile == current else "Use",
                              action=lambda selected=profile: self._change(
                                  "battery", lambda: hw.set_power_profile(selected)))
        box.show_all()

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
            elif kind == "bluetooth":
                label.set_text("Adapter and paired-device status from Linux")
            elif kind == "audio":
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
