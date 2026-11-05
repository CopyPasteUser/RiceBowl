"""Compact native Aqua device popovers anchored to the actual tray buttons.

No additional polling or daemon: an existing 20-second hardware monitor
refreshes the popover; its sound writes use the verified shared backend.
"""

from __future__ import annotations

import threading


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
        self._bluetooth_scan_event = None

    def show(self, kind: str):
        if kind not in ("network", "audio", "battery", "bluetooth"):
            return
        if hasattr(self.shell, "_aqua_notifications"):
            self.shell._aqua_notifications.popover.popdown()
        if hasattr(self.shell, "_aqua_drives"):
            self.shell._aqua_drives.popover.popdown()
        if hasattr(self.shell, "_aqua_calendar"):
            self.shell._aqua_calendar.popover.popdown()
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
        if kind == "bluetooth":
            event = getattr(self, "_bluetooth_scan_event", None)
            if event is not None:
                event.set()
                self._bluetooth_scan_event = None
        self._generations[kind] = self._generations.get(kind, 0) + 1
        self._busy.discard(kind)
        self._confirming.discard(kind)
        self._confirming.discard(kind + "-password")
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
            outputs = hw.read_sound_outputs()
            try:
                players = hw.read_media_players()
            except RuntimeError:
                players = None  # Audio controls remain usable if the session bus is down.
            return outputs, players
        return hw.read_power_profiles()

    def _refresh_details(self, kind, *, feedback=None):
        if kind in self._busy or kind not in self.popovers or not self.popovers[kind].get_visible():
            return
        self._busy.add(kind)
        self._confirming.discard(kind)
        self._confirming.discard(kind + "-password")
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

    def _change(self, kind, operation, *, feedback="Change applied and verified"):
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
                self._refresh_details(kind, feedback=feedback)

        self.controller.submit("aqua-write-" + kind, operation, complete)

    def _start_bluetooth_scan(self):
        """Use an existing worker for one cancellable, bounded BlueZ scan."""
        kind = "bluetooth"
        if (kind in self._busy or kind not in self.popovers
                or not self.popovers[kind].get_visible()):
            return
        event = threading.Event()
        self._bluetooth_scan_event = event
        self._busy.add(kind)
        self._generations[kind] = self._generations.get(kind, 0) + 1
        generation = self._generations[kind]
        self.details[kind].set_sensitive(False)
        self.detail_status[kind].set_text("Discovering nearby devices for up to 9 seconds… Close to cancel.")

        def complete(response):
            if self._bluetooth_scan_event is event:
                self._bluetooth_scan_event = None
            if (generation != self._generations.get(kind)
                    or kind not in self.popovers or not self.popovers[kind].get_visible()):
                return
            self._busy.discard(kind)
            if response.error:
                self.details[kind].set_sensitive(True)
                self.detail_status[kind].set_text("Discovery unavailable: " + response.error[:165])
                return
            self._render_details(kind, response.value)
            self.details[kind].set_sensitive(True)
            self.detail_status[kind].set_text("Discovery finished · only devices visible to BlueZ are shown")

        self.controller.submit("aqua-scan-bluetooth",
                               lambda: self.controller.hardware.scan_bluetooth_devices(
                                   duration=9, cancel=event), complete)

    def _row(self, parent, title, *, button=None, action=None,
             secondary_button=None, secondary_action=None):
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
        if secondary_button is not None:
            control = self.shell._class(Gtk.Button(label=secondary_button), "aqua-flyout-more")
            control.get_accessible().set_name(secondary_button + ": " + title)
            control.connect("clicked", lambda _button: secondary_action())
            row.pack_end(control, False, False, 0)
        parent.pack_start(row, False, False, 0)

    def _password_prompt(self, ssid):
        """One-shot WPA entry; never show, store or log the entered secret."""
        kind = "network"
        if kind in self._busy or kind not in self.popovers or not self.popovers[kind].get_visible():
            return
        if kind + "-password" in self._confirming:
            return
        self._confirming.add(kind + "-password")
        Gtk = self.Gtk
        box = self.details[kind]
        self._confirming.discard(kind)
        box.pack_start(Gtk.Label(label="Wi-Fi password for " + ssid[:32], xalign=0), False, False, 0)
        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_max_length(63)
        entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        entry.get_accessible().set_name("WPA password for " + ssid[:32])
        box.pack_start(entry, False, False, 0)

        def submit():
            secret = entry.get_text()
            entry.set_text("")
            # The verified Riceware facade passes secrets on nmcli stdin.
            self._change("network", lambda: self.controller.hardware.connect_wifi_secured(ssid, secret))

        entry.connect("activate", lambda _entry: submit())
        self._row(box, "Use password once", button="Connect", action=submit)
        self._row(box, "Return to networks", button="Cancel",
                  action=lambda: self._refresh_details("network"))
        box.show_all()
        entry.grab_focus()

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
                    security = network.security.upper()
                    password_supported = (not network.connected and "WPA" in security and
                                          not any(value in security for value in ("EAP", "802.1X", "ENTERPRISE")))
                    self._row(box, caption,
                              button="Disconnect" if network.connected else "Connect",
                              action=(lambda: self._change("network", hw.disconnect_wifi))
                              if network.connected else
                              (lambda ssid=network.ssid: self._change(
                                  "network", lambda: hw.connect_wifi(ssid))),
                              secondary_button="Password…" if password_supported else None,
                              secondary_action=(lambda ssid=network.ssid: self._password_prompt(ssid))
                              if password_supported else None)
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
            if state.powered is True:
                self._row(box, "Search for nearby devices · 9s", button="Scan…",
                          action=self._start_bluetooth_scan)
            if not state.devices:
                self._row(box, "No known Bluetooth devices · try Scan")
            # Keep active connections visible while giving newly found,
            # unpaired devices priority over old disconnected cache entries.
            ranked = sorted(state.devices, key=lambda item:
                            (0 if item.connected else 1 if not item.paired else 2,
                             item.name.casefold()))
            for device in ranked[:5]:
                caption = device.name[:42] + (" · Connected" if device.connected else "")
                if state.powered is True and device.paired:
                    self._row(box, caption,
                              button="Disconnect" if device.connected else "Connect",
                              action=lambda item=device: self._change(
                                  "bluetooth", lambda: hw.set_bluetooth_connection(
                                      item.address, not item.connected)))
                elif state.powered is True and not device.paired:
                    self._row(box, caption, button="Pair",
                              action=lambda item=device: self._change(
                                  "bluetooth", lambda: hw.pair_bluetooth_device(item.address)))
                else:
                    self._row(box, caption)
        elif kind == "audio":
            outputs, players = snapshot
            if not outputs:
                self._row(box, "No audio output devices reported")
            for output in outputs[:5]:
                self._row(box, output.label[:48] + (" · Active" if output.active else ""),
                          button=None if output.active else "Use",
                          action=(lambda name=output.name: self._change(
                              "audio", lambda: hw.set_sound_output(name))))
            self._row(box, "NOW PLAYING · MPRIS SESSION")
            if players is None:
                self._row(box, "Session media bus unavailable")
            elif not players:
                self._row(box, "No compatible player is currently running")
            for item in (players or ())[:2]:
                self._row(box, item.title[:42] +
                          (" · " + item.artist[:27] if item.artist else "") +
                          " · " + item.label)
                controls = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=6)
                for caption, command, enabled in (
                    ("◀ Previous", "Previous", item.can_previous),
                    ("Pause" if item.status == "Playing" else "Play",
                     "PlayPause", item.can_play_pause),
                    ("Next ▶", "Next", item.can_next),
                ):
                    button = self.shell._class(self.Gtk.Button(label=caption), "aqua-flyout-more")
                    button.set_sensitive(enabled)
                    button.get_accessible().set_name(caption + " · " + item.label)
                    button.connect("clicked", lambda _button, player=item.bus_name, cmd=command:
                                   self._change("audio", lambda: hw.media_action(player, cmd),
                                                feedback="Player command acknowledged; state refreshed"))
                    controls.pack_start(button, True, True, 0)
                box.pack_start(controls, False, False, 0)
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
