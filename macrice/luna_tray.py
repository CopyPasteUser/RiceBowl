"""Small authentic-XP-inspired notification-area popovers.

Uses the shell's verified audio transactions and optional native Linux device
backends. Never invents hardware state or installs a background daemon.
"""

from __future__ import annotations

import logging
import shutil
import threading

from .hardware_status import (
    connect_wifi, disconnect_wifi, read_bluetooth, read_brightness,
    read_power_profiles, read_sound_outputs, read_wifi_networks, read_wifi_radio,
    set_bluetooth_power, set_brightness, set_power_profile, set_sound_output,
    set_wifi_radio,
)

LOG = logging.getLogger(__name__)


class LunaTray:
    def __init__(self, shell, Gtk, GLib):
        self.shell, self.Gtk, self.GLib = shell, Gtk, GLib
        self.popovers = {}
        self._network_request = 0
        self._network_busy = False
        self._network_error = None
        self._brightness_writing = False
        self._brightness_queued = None
        self._brightness_source = 0
        self._brightness_programmatic = False
        self._audio_output_busy = False
        self._power_profile_busy = False
        self._bluetooth_busy = False
        self._profile_error = None
        self._bluetooth_error = None

    def _label(self, value, kind="luna-tray-caption"):
        label = self.shell._class(self.Gtk.Label(label=value, xalign=0), kind)
        label.set_line_wrap(True)
        return label

    def _button(self, label, command, *, css="luna-tray-link"):
        button = self.shell._class(self.Gtk.Button(label=label), css)
        button.get_accessible().set_name(label)
        available = next((item for item in command if shutil.which(item)), None)
        button.set_sensitive(available is not None)
        button.set_tooltip_text("Open " + label if available else
                                "Install " + " or ".join(command) + " to use this action")
        if available:
            button.connect("clicked", lambda _btn, cmd=available: self.shell._open_tool(cmd))
        return button

    def install(self, name, anchor):
        Gtk = self.Gtk
        popup = self.shell._class(Gtk.Popover.new(anchor), "luna-tray-popup")
        popup.set_position(Gtk.PositionType.TOP)
        # The anchor lives inside a DOCK toplevel only panel_height tall.
        # GTK3 defaults to PopoverConstraint.WINDOW, which clips/repositions
        # the flyout into that thin taskbar instead of above it.
        popup.set_constrain_to(Gtk.PopoverConstraint.NONE)
        popup.set_modal(True)
        body = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8),
                                  "luna-tray-card")
        popup.add(body)
        self.popovers[name] = popup
        if name == "audio":
            self._audio(body)
        elif name == "network":
            self._network(body)
        elif name == "battery":
            self._power(body)
        elif name == "clock":
            self._clock(body)
        elif name == "bluetooth":
            self._bluetooth(body)
        anchor.connect("clicked", lambda _button, kind=name: self.toggle(kind))
        return popup

    def _heading(self, body, name, icon):
        row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=8)
        row.pack_start(self.shell._icon(icon, self.Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
        row.pack_start(self._label(name, "luna-tray-title"), True, True, 0)
        body.pack_start(row, False, False, 0)

    def _audio(self, body):
        Gtk = self.Gtk
        self._heading(body, "Volume", "ricehub-luna-cp-audio")
        self.audio_label = self._label("Checking sound output…")
        body.pack_start(self.audio_label, False, False, 0)
        self.audio_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 2)
        self.audio_scale.set_draw_value(False)
        self.audio_scale.set_sensitive(False)
        self.audio_scale.get_accessible().set_name("System output volume")
        self.audio_scale.connect("value-changed", self.shell._queue_volume_change)
        body.pack_start(self.audio_scale, False, False, 0)
        self.audio_mute = self.shell._class(Gtk.ToggleButton(label="Mute"), "luna-tray-mute")
        self.audio_mute.set_sensitive(False)
        self.audio_mute.get_accessible().set_name("Mute system output")
        self.audio_mute.connect("clicked", self.shell._toggle_output_mute)
        body.pack_start(self.audio_mute, False, False, 0)
        body.pack_start(self._label("Output device", "luna-tray-section"),
                        False, False, 0)
        self.output_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        body.pack_start(self.output_list, False, False, 0)
        body.pack_start(self._button("Sound settings…", ("pavucontrol", "xfce4-mixer")),
                        False, False, 0)

    def _network(self, body):
        Gtk = self.Gtk
        self._heading(body, "Network connections", "ricehub-luna-cp-network")
        self.network_label = self._label("Checking NetworkManager…")
        body.pack_start(self.network_label, False, False, 0)
        self.wifi_toggle = self.shell._class(Gtk.Button(label="Wi-Fi status unknown"),
                                             "luna-tray-switch")
        self.wifi_toggle.set_sensitive(False)
        self.wifi_toggle.get_accessible().set_name("Toggle Wi-Fi radio")
        self.wifi_toggle.connect("clicked", self._toggle_wifi)
        body.pack_start(self.wifi_toggle, False, False, 0)
        self.wifi_disconnect = self.shell._class(Gtk.Button(label="Disconnect from Wi-Fi"),
                                                 "luna-tray-link")
        self.wifi_disconnect.set_sensitive(False)
        self.wifi_disconnect.connect("clicked", self._disconnect_wifi)
        body.pack_start(self.wifi_disconnect, False, False, 0)
        body.pack_start(self._label("Nearby networks", "luna-tray-section"),
                        False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(292, 142)
        self.network_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroll.add(self.network_list)
        body.pack_start(scroll, False, False, 0)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        refresh = self.shell._class(Gtk.Button(label="Refresh"), "luna-tray-link")
        refresh.connect("clicked", lambda _btn: self.refresh_network(rescan=True))
        actions.pack_start(refresh, True, True, 0)
        actions.pack_start(self._button("Connections…", ("nm-connection-editor",)),
                           True, True, 0)
        body.pack_start(actions, False, False, 0)

    def _power(self, body):
        Gtk = self.Gtk
        self._heading(body, "Power", "ricehub-luna-cp-performance")
        self.power_label = self._label("Checking battery…")
        body.pack_start(self.power_label, False, False, 0)
        self.power_level = Gtk.LevelBar.new_for_interval(0, 100)
        self.power_level.set_no_show_all(True)
        body.pack_start(self.power_level, False, False, 0)
        body.pack_start(self._label("Screen brightness", "luna-tray-section"),
                        False, False, 0)
        self.brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 2)
        self.brightness_scale.set_draw_value(False)
        self.brightness_scale.set_sensitive(False)
        self.brightness_scale.get_accessible().set_name("Screen brightness")
        self.brightness_scale.connect("value-changed", self._queue_brightness)
        body.pack_start(self.brightness_scale, False, False, 0)
        self.brightness_label = self._label("Brightness not detected")
        body.pack_start(self.brightness_label, False, False, 0)
        body.pack_start(self._label("Power profile", "luna-tray-section"),
                        False, False, 0)
        self.profile_label = self._label("Checking supported profiles…")
        body.pack_start(self.profile_label, False, False, 0)
        self.profile_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        body.pack_start(self.profile_buttons, False, False, 0)
        body.pack_start(self._button("Power options…", ("xfce4-power-manager-settings",)),
                        False, False, 0)

    def _bluetooth(self, body):
        Gtk = self.Gtk
        self._heading(body, "Bluetooth devices", "ricehub-luna-task-bluetooth")
        self.bluetooth_label = self._label("Checking Bluetooth adapter…")
        body.pack_start(self.bluetooth_label, False, False, 0)
        self.bluetooth_switch = self.shell._class(Gtk.Button(label="Bluetooth unavailable"),
                                                  "luna-tray-switch")
        self.bluetooth_switch.set_sensitive(False)
        self.bluetooth_switch.connect("clicked", self._toggle_bluetooth)
        body.pack_start(self.bluetooth_switch, False, False, 0)
        body.pack_start(self._label("Connected devices", "luna-tray-section"),
                        False, False, 0)
        self.bluetooth_devices = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.pack_start(self.bluetooth_devices, False, False, 0)
        body.pack_start(self._button("Bluetooth settings…", ("blueman-manager",)),
                        False, False, 0)

    def _clock(self, body):
        Gtk = self.Gtk
        self._heading(body, "Date and time", "ricehub-luna-cp-regional")
        self.date_label = self._label("", "luna-tray-caption")
        body.pack_start(self.date_label, False, False, 0)
        calendar = self.shell._class(Gtk.Calendar(), "luna-tray-calendar")
        calendar.set_display_options(Gtk.CalendarDisplayOptions.SHOW_HEADING |
                                     Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES)
        body.pack_start(calendar, False, False, 0)
        self.calendar = calendar
        body.pack_start(self._button("Date and time settings…",
                                      ("time-admin", "xfce4-settings-manager")),
                        False, False, 0)

    def toggle(self, name):
        pop = self.popovers[name]
        if pop.get_visible():
            # GtkPopover.popdown() leaves the widget visible during its exit
            # transition. XP menus dismiss immediately and must be closed
            # before another tray/menu surface can claim focus.
            pop.hide()
            return
        for other in self.popovers.values():
            if other.get_visible():
                other.hide()
        self.shell._hide_menu()
        self.shell._hide_actions()
        self.shell._refresh_status_async()
        pop.show_all()
        pop.popup()
        if name == "network":
            self.refresh_network()
        elif name == "battery":
            self.refresh_brightness()
            self.refresh_profiles()
        elif name == "audio":
            self.refresh_outputs()
        elif name == "bluetooth":
            self.refresh_bluetooth()
        elif name == "clock":
            now = self.GLib.DateTime.new_now_local()
            self.date_label.set_text(now.format("%A, %d %B %Y"))
            self.calendar.select_month(now.get_month() - 1, now.get_year())
            self.calendar.select_day(now.get_day_of_month())

    def on_status(self, status):
        if status is None:
            self.audio_label.set_text("Audio backend unavailable")
            self.audio_scale.set_sensitive(False)
            self.audio_mute.set_sensitive(False)
            self.power_label.set_text("Battery status unavailable")
            self.power_level.hide()
            return
        sound, battery = status.sound, status.battery
        if not self.shell._volume_writing and self.shell._volume_queued is None:
            self.shell._volume_programmatic = True
            try:
                if sound.percent is not None:
                    self.audio_scale.set_value(min(100, sound.percent))
            finally:
                self.shell._volume_programmatic = False
        self.audio_scale.set_sensitive(sound.percent is not None)
        self.audio_mute.set_sensitive(sound.muted is not None and not self.shell._mute_writing)
        if sound.muted is not None and not self.shell._mute_writing:
            self.audio_mute.set_active(sound.muted)
        self.audio_label.set_text("Output unavailable" if sound.percent is None else
                                  f"Output: {sound.percent}%" +
                                  (" · muted" if sound.muted else ""))
        self.power_label.set_text("No laptop battery detected" if battery is None else
                                  f"Battery: {battery.percent}% · {battery.label}")
        if battery is None:
            self.power_level.hide()
        else:
            self.power_level.set_value(battery.percent)
            self.power_level.show()

    def volume_pending(self, target):
        self.audio_label.set_text(f"Adjusting to {target}%…")

    def volume_done(self, state, error):
        if error:
            self.audio_label.set_text("Could not change volume: " + error)
        elif state is not None:
            self.audio_label.set_text(f"Output: {state.percent}%")

    def mute_done(self, state, error):
        if error:
            self.audio_label.set_text("Could not change mute: " + error)
        elif state is not None:
            self.audio_mute.set_active(bool(state.muted))
            self.audio_label.set_text("Muted" if state.muted else "Unmuted")

    def refresh_outputs(self):
        if self._audio_output_busy:
            return
        self._audio_output_busy = True
        self._set_list_message(self.output_list, "Checking outputs…")

        def worker():
            try:
                outputs = read_sound_outputs()
            except (OSError, RuntimeError, ValueError):
                outputs = ()
            self.GLib.idle_add(self._outputs_ready, outputs)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-audio-outputs").start()

    def _set_list_message(self, box, message):
        for child in box.get_children():
            box.remove(child)
        box.pack_start(self._label(message), False, False, 0)
        box.show_all()

    def _outputs_ready(self, outputs):
        self._audio_output_busy = False
        if not outputs:
            self._set_list_message(self.output_list, "No selectable outputs (pactl unavailable)")
            return False
        for child in self.output_list.get_children():
            self.output_list.remove(child)
        for output in outputs[:5]:
            button = self.shell._class(self.Gtk.Button(
                label=("✓  " if output.active else "○  ") + output.label),
                "luna-tray-device")
            button.set_sensitive(not output.active)
            if output.active:
                button.get_style_context().add_class("luna-tray-current")
            button.set_tooltip_text(output.name)
            button.get_accessible().set_name(("Current output: " if output.active else
                                               "Select output: ") + output.label)
            button.connect("clicked", lambda _button, name=output.name: self._switch_output(name))
            self.output_list.pack_start(button, False, False, 0)
        self.output_list.show_all()
        return False

    def _switch_output(self, name):
        if self._audio_output_busy:
            return
        self._audio_output_busy = True
        self.audio_label.set_text("Switching audio output…")

        def worker():
            try:
                selected, error = set_sound_output(name), None
            except (OSError, RuntimeError, ValueError) as exc:
                selected, error = None, str(exc)
            self.GLib.idle_add(self._output_changed, selected, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-select-output").start()

    def _output_changed(self, selected, error):
        self._audio_output_busy = False
        self.audio_label.set_text("Output change failed: " + error if error else
                                  "Using " + selected.label)
        self.refresh_outputs()
        self.shell._refresh_status_async()
        return False

    def refresh_network(self, *, rescan=False):
        if self._network_busy:
            return
        self._network_busy = True
        self._network_request += 1
        request = self._network_request
        self.network_label.set_text("Looking for Wi-Fi connections…")

        def worker():
            try:
                state, networks = read_wifi_radio(), read_wifi_networks(rescan=rescan)
            except (OSError, RuntimeError, ValueError) as exc:
                LOG.warning("Wi-Fi status unavailable: %s", exc)
                state, networks = None, ()
            self.GLib.idle_add(self._network_ready, request, state, networks)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-wifi").start()

    def _network_ready(self, request, radio, networks):
        if request != self._network_request:
            return False
        self._network_busy = False
        if radio is None:
            self.network_label.set_text("NetworkManager is unavailable")
            self.wifi_toggle.set_sensitive(False)
            self.wifi_toggle.set_label("Wi-Fi unavailable")
        else:
            self.network_label.set_text(self._network_error or
                                        ("Wi-Fi is on" if radio else "Wi-Fi is off"))
            self.wifi_toggle.set_sensitive(True)
            self.wifi_toggle.set_label("Turn Wi-Fi off" if radio else "Turn Wi-Fi on")
        self.wifi_disconnect.set_sensitive(bool(radio) and any(n.connected for n in networks))
        for child in self.network_list.get_children():
            self.network_list.remove(child)
        if radio and networks:
            for network in networks:
                row = self.shell._class(self.Gtk.Button(), "luna-tray-network-row")
                contents = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=8)
                contents.pack_start(self._label("●" if network.connected else "○",
                                           "luna-tray-network-mark"), False, False, 0)
                caption = self._label(network.ssid, "luna-tray-network-name")
                from gi.repository import Pango

                caption.set_ellipsize(Pango.EllipsizeMode.END)
                caption.set_tooltip_text(network.ssid)
                contents.pack_start(caption, True, True, 0)
                contents.pack_end(self._label(str(network.signal) + "%", "luna-tray-caption"),
                             False, False, 0)
                row.add(contents)
                row.set_sensitive(not network.connected)
                row.get_accessible().set_name("Connect to " + network.ssid if not network.connected
                                               else "Connected to " + network.ssid)
                row.set_tooltip_text(("Connected" if network.connected else "Connect")
                                     + " · " + (network.security or "Open network"))
                if not network.connected:
                    row.connect("clicked", lambda _btn, ssid=network.ssid: self._join_wifi(ssid))
                self.network_list.pack_start(row, False, False, 0)
        else:
            self.network_list.pack_start(self._label(
                "No nearby networks found" if radio else
                "Enable Wi-Fi to view available networks"), False, False, 5)
        self.network_list.show_all()
        return False

    def _toggle_wifi(self, _button):
        if self._network_busy:
            return
        # Read real state for each action; the label can be stale after an XFCE toggle.
        self._network_busy = True
        self._network_error = None
        self.wifi_toggle.set_sensitive(False)
        self.network_label.set_text("Applying Wi-Fi change…")

        def worker():
            try:
                current = read_wifi_radio()
                if current is None:
                    raise RuntimeError("NetworkManager is unavailable")
                set_wifi_radio(not current)
                error = None
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
            self.GLib.idle_add(self._wifi_changed, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-wifi-switch").start()

    def _wifi_changed(self, error):
        self._network_busy = False
        self._network_error = "Wi-Fi change failed: " + error if error else None
        self.refresh_network()
        return False

    def _join_wifi(self, ssid):
        if self._network_busy:
            return
        self._network_busy = True
        self._network_error = None
        self.wifi_toggle.set_sensitive(False)
        self.network_label.set_text("Connecting to " + ssid + "…")

        def worker():
            try:
                if not connect_wifi(ssid):
                    raise RuntimeError("Connected network could not be verified")
                error = None
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
            self.GLib.idle_add(self._wifi_joined, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-wifi-connect").start()

    def _wifi_joined(self, error):
        self._network_busy = False
        self._network_error = ("Unable to connect: " + error +
                               ". Use Connections… to enter credentials." if error else None)
        self.refresh_network()
        return False

    def _disconnect_wifi(self, _button):
        if self._network_busy:
            return
        self._network_busy = True
        self.wifi_disconnect.set_sensitive(False)
        self.network_label.set_text("Disconnecting Wi-Fi…")

        def worker():
            try:
                if not disconnect_wifi():
                    raise RuntimeError("Wi-Fi disconnection was not verified")
                error = None
            except (OSError, RuntimeError, ValueError) as exc:
                error = str(exc)
            self.GLib.idle_add(self._wifi_joined, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-wifi-disconnect").start()

    def refresh_profiles(self):
        if self._power_profile_busy:
            return
        self._power_profile_busy = True

        def worker():
            try:
                state = read_power_profiles()
            except (OSError, RuntimeError, ValueError):
                state = None, ()
            self.GLib.idle_add(self._profiles_ready, *state)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-power-profiles").start()

    def _profiles_ready(self, current, supported):
        self._power_profile_busy = False
        for child in self.profile_buttons.get_children():
            self.profile_buttons.remove(child)
        if not supported:
            self.profile_label.set_text(self._profile_error or "Power profiles not supported")
            return False
        self.profile_label.set_text(self._profile_error or
                                    ("Active: " + (current or "Unknown")))
        for name in supported:
            title = {"power-saver": "Saver", "balanced": "Balanced",
                     "performance": "Performance"}[name]
            button = self.shell._class(self.Gtk.Button(label=title),
                                        "luna-tray-device")
            button.set_sensitive(current != name)
            if current == name:
                button.get_style_context().add_class("luna-tray-current")
            button.get_accessible().set_name("Select " + name + " power profile")
            button.connect("clicked", lambda _button, profile=name: self._switch_profile(profile))
            self.profile_buttons.pack_start(button, True, True, 0)
        self.profile_buttons.show_all()
        return False

    def _switch_profile(self, profile):
        if self._power_profile_busy:
            return
        self._power_profile_busy = True
        self._profile_error = None
        self.profile_label.set_text("Selecting " + profile + "…")

        def worker():
            try:
                state, error = set_power_profile(profile), None
            except (OSError, ValueError, RuntimeError) as exc:
                state, error = None, str(exc)
            self.GLib.idle_add(self._profile_changed, state, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-set-power-profile").start()

    def _profile_changed(self, state, error):
        self._power_profile_busy = False
        self._profile_error = "Power profile change failed: " + error if error else None
        self.refresh_profiles()
        return False

    def refresh_bluetooth(self):
        if self._bluetooth_busy:
            return
        self._bluetooth_busy = True

        def worker():
            try:
                state = read_bluetooth()
            except (OSError, ValueError, RuntimeError):
                state = None
            self.GLib.idle_add(self._bluetooth_ready, state)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-bluetooth").start()

    def _bluetooth_ready(self, state):
        self._bluetooth_busy = False
        if state is None or state.powered is None:
            self.bluetooth_label.set_text(self._bluetooth_error or
                                          "Bluetooth adapter not available")
            self.bluetooth_switch.set_label("Bluetooth unavailable")
            self.bluetooth_switch.set_sensitive(False)
            self._set_list_message(self.bluetooth_devices, "No adapter or BlueZ service")
            return False
        self.bluetooth_label.set_text(self._bluetooth_error or
                                      ("Bluetooth is on" if state.powered else "Bluetooth is off"))
        self.bluetooth_switch.set_label("Turn Bluetooth off" if state.powered else
                                        "Turn Bluetooth on")
        self.bluetooth_switch.set_sensitive(True)
        if not state.connected:
            self._set_list_message(self.bluetooth_devices, "No connected devices")
        else:
            self._set_list_message(self.bluetooth_devices, "\n".join(state.connected))
        return False

    def _toggle_bluetooth(self, _button):
        if self._bluetooth_busy:
            return
        self._bluetooth_busy = True
        self._bluetooth_error = None
        self.bluetooth_switch.set_sensitive(False)
        self.bluetooth_label.set_text("Applying Bluetooth change…")

        def worker():
            try:
                current = read_bluetooth().powered
                if current is None:
                    raise RuntimeError("Bluetooth adapter not found")
                set_bluetooth_power(not current)
                error = None
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
            self.GLib.idle_add(self._bluetooth_changed, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-bluetooth-switch").start()

    def _bluetooth_changed(self, error):
        self._bluetooth_busy = False
        self._bluetooth_error = "Bluetooth change failed: " + error if error else None
        self.refresh_bluetooth()
        return False

    def refresh_brightness(self):
        def worker():
            try:
                value = read_brightness()
                writable = shutil.which("brightnessctl") is not None
            except (OSError, ValueError):
                value, writable = None, False
            self.GLib.idle_add(self._brightness_ready, value, writable)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-backlight").start()

    def _brightness_ready(self, value, writable):
        if self._brightness_writing or self._brightness_queued is not None:
            return False
        self._brightness_programmatic = True
        try:
            if value is not None:
                self.brightness_scale.set_value(max(1, value))
        finally:
            self._brightness_programmatic = False
        self.brightness_scale.set_sensitive(value is not None and writable)
        self.brightness_label.set_text(
            "Brightness not detected" if value is None else
            "Brightness: " + str(value) + "%" if writable else
            "Brightness: " + str(value) + "% · install brightnessctl")
        return False

    def _queue_brightness(self, slider):
        if self._brightness_programmatic:
            return
        self._brightness_queued = int(round(slider.get_value()))
        self.brightness_label.set_text(f"Brightness: {self._brightness_queued}%")
        if self._brightness_source:
            self.GLib.source_remove(self._brightness_source)
        self._brightness_source = self.GLib.timeout_add(340, self._commit_brightness)

    def _commit_brightness(self):
        self._brightness_source = 0
        if self._brightness_writing or self._brightness_queued is None:
            return False
        target = self._brightness_queued
        self._brightness_queued = None
        self._brightness_writing = True
        self.brightness_label.set_text(f"Setting brightness to {target}%…")

        def worker():
            try:
                actual, error = set_brightness(target), None
            except (OSError, ValueError, RuntimeError) as exc:
                actual, error = None, str(exc)
            self.GLib.idle_add(self._brightness_done, actual, error)

        threading.Thread(target=worker, daemon=True, name="ricebowl-xp-set-backlight").start()
        return False

    def _brightness_done(self, actual, error):
        self._brightness_writing = False
        self.brightness_label.set_text("Brightness adjustment failed: " + error if error else
                                       f"Brightness: {actual}%")
        if self._brightness_queued is not None:
            self._brightness_source = self.GLib.timeout_add(180, self._commit_brightness)
        else:
            self.refresh_brightness()
        return False
