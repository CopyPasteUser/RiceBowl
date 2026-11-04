"""Verified, native Aqua World controls for real Linux devices.

No privileged shell commands or optimistic setting indicators. Read/write work
is kept off GTK's main loop; every successful write is followed by a read-back.
The surrounding Control Center still offers Linux configuration utilities for
the settings a lightweight desktop shell cannot safely own.
"""

from __future__ import annotations

import logging
import shutil
import threading

from . import hardware_status as hw


NATIVE_TASKS = frozenset({
    ("connections", "Network connections"),
    ("connections", "Bluetooth devices"),
    ("sound", "Output volume & mute"),
    ("sound", "Input & output devices"),
    ("display", "Display configuration"),
    ("power", "Battery status"),
    ("power", "Power management"),
})


class NativeAquaControls:
    def __init__(self, shell, Gtk, GLib, parent, *, is_current, style_prefix="aqua",
                 backend=None, runner=None):
        self.shell, self.Gtk, self.GLib = shell, Gtk, GLib
        self.parent, self.is_current = parent, is_current
        self.style_prefix = style_prefix
        self.backend = backend if backend is not None else hw
        self.runner = runner
        self._disposed = False
        self._generation = 0
        self._syncing = False
        self._busy = False
        self._interactive = []
        self._reader = None
        self._renderer = None
        self._debounce = 0

        self.surface = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                                    self._style("panel"))
        self.title = shell._class(Gtk.Label(label="LIVE CONTROLS", xalign=0),
                                  self._style("title"))
        self.surface.pack_start(self.title, False, False, 0)
        self.status = shell._class(Gtk.Label(label="Reading your Linux devices…", xalign=0),
                                   self._style("status"))
        self.status.set_line_wrap(True)
        self.surface.pack_start(self.status, False, False, 0)
        parent.pack_start(self.surface, False, False, 6)

    def _style(self, name):
        return f"{self.style_prefix}-native-{name}"

    def _add(self, widget, *, interactive=False):
        self.surface.pack_start(widget, False, False, 0)
        if interactive:
            widget.set_sensitive(False)
            self._interactive.append(widget)
        return widget

    def _label(self, text, style=None):
        label = self.shell._class(self.Gtk.Label(label=text, xalign=0),
                                  style or self._style("label"))
        label.set_line_wrap(True)
        return self._add(label)

    def _switch(self, caption, callback):
        row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=12)
        title = self.shell._class(self.Gtk.Label(label=caption, xalign=0),
                                  self._style("label"))
        row.pack_start(title, True, True, 0)
        toggle = self.Gtk.Switch()
        toggle.set_valign(self.Gtk.Align.CENTER)
        toggle.get_accessible().set_name(caption)
        toggle.set_sensitive(False)
        self._interactive.append(toggle)
        toggle.connect("notify::active", lambda widget, _prop: None if self._syncing
                       else callback(widget.get_active()))
        row.pack_end(toggle, False, False, 0)
        self._add(row)
        return toggle

    def _scale(self, caption, callback, *, minimum=0, maximum=100):
        self._label(caption)
        scale = self.Gtk.Scale.new_with_range(self.Gtk.Orientation.HORIZONTAL,
                                               minimum, maximum, 1)
        scale.set_draw_value(True)
        scale.set_digits(0)
        scale.set_value_pos(self.Gtk.PositionType.RIGHT)
        scale.get_accessible().set_name(caption)
        self._add(scale, interactive=True)

        def changed(widget):
            if self._syncing or self._busy:
                return
            if self._debounce:
                self.GLib.source_remove(self._debounce)
            value = round(widget.get_value())

            def commit():
                self._debounce = 0
                if self.is_current():
                    callback(value)
                return False

            self._debounce = self.GLib.timeout_add(310, commit)

        scale.connect("value-changed", changed)
        return scale

    def _button(self, caption, callback):
        button = self.shell._class(self.Gtk.Button(label=caption), self._style("action"))
        button.connect("clicked", lambda _button: callback())
        self._add(button, interactive=True)
        return button

    def _combo(self, caption, callback):
        self._label(caption)
        combo = self.Gtk.ComboBoxText()
        combo.get_accessible().set_name(caption)
        self._add(combo, interactive=True)
        combo.connect("changed", lambda widget: None if self._syncing or
                      not widget.get_active_id() else callback(widget.get_active_id()))
        return combo

    def _set_values(self, changes):
        self._syncing = True
        try:
            changes()
        finally:
            self._syncing = False

    def _status(self, message, *, error=False):
        self.status.set_text(message)
        css = self.status.get_style_context()
        if error:
            css.add_class(self._style("error"))
        else:
            css.remove_class(self._style("error"))

    def _set_sensitive(self, available):
        for widget in self._interactive:
            widget.set_sensitive(bool(available) and not self._busy)

    def _submit(self, writer=None, *, completion=None):
        """Serialize GTK actions and discard results from a left-behind page."""
        if getattr(self, "_disposed", False) or self._busy or not self.is_current() or self._reader is None:
            return
        self._generation += 1
        generation = self._generation
        self._busy = True
        self._set_sensitive(False)
        self._status("Applying and verifying…" if writer else "Reading device state…")

        def probe():
            failure = None
            try:
                if writer:
                    writer()
            except (OSError, ValueError, RuntimeError) as exc:
                failure = str(exc)[:220]
                logging.getLogger(__name__).warning("Aqua device action: %s", type(exc).__name__)
            try:
                snapshot = self._reader()
                read_ok = True
            except (OSError, ValueError, RuntimeError) as exc:
                snapshot = None
                read_ok = False
                failure = failure or str(exc)[:220]
                logging.getLogger(__name__).warning("Aqua device read-back: %s", type(exc).__name__)
            return snapshot, read_ok, failure

        def apply(response):
            if generation != self._generation:
                return False  # A newer request owns the busy state.
            if getattr(self, "_disposed", False) or not self.is_current():
                self._busy = False
                return False
            self._busy = False
            snapshot, read_ok, failure = response
            self._set_sensitive(read_ok)
            summary = [None]
            if read_ok:
                try:
                    self._set_values(lambda: summary.__setitem__(0, self._renderer(snapshot)))
                except (AttributeError, TypeError, ValueError) as exc:
                    logging.getLogger(__name__).warning("Aqua device render: %s", type(exc).__name__)
                    self._status("Unable to display the device state", error=True)
                    self._set_sensitive(False)
                    self.refresh_button.set_sensitive(True)
                    return False
            if failure:
                self._status(failure, error=True)
                if not read_ok:
                    self._set_sensitive(False)
                    self.refresh_button.set_sensitive(True)
            else:
                self._status(completion or ("Applied and verified" if writer else
                                summary[0] or "Live device state"))
            return False

        if getattr(self, "runner", None) is not None:
            def completed(response):
                if response.error:
                    apply((None, False, response.error))
                else:
                    apply(response.value)

            self.runner.submit(f"native-{id(self)}", probe, completed)
        else:
            def worker():
                result = probe()
                self.GLib.idle_add(lambda: apply(result))

            threading.Thread(target=worker, daemon=True, name="ricebowl-aqua-control").start()

    def suspend(self):
        """Invalidate hidden-page responses and pending debounced writes."""
        self._generation += 1
        self._busy = False
        if self._debounce:
            self.GLib.source_remove(self._debounce)
            self._debounce = 0

    def dispose(self):
        self._disposed = True
        self.suspend()

    def bind(self, reader, renderer):
        self._reader, self._renderer = reader, renderer
        self.refresh_button = self._button("↻  Refresh device state", self.refresh)
        self.refresh_button.set_sensitive(True)
        self.refresh()

    def refresh(self):
        self._submit()

    def change(self, writer):
        self._submit(writer)

    def wifi(self):
        def wifi_radio_change(enabled):
            if not enabled:
                # Turning off Wi-Fi can terminate SSH/Tailscale and other
                # connections. An inline second action avoids stealing focus
                # from the parent Control Center's auto-hide window.
                self._set_values(lambda: toggle.set_active(True))
                confirmation.set_visible(True)
                return
            confirmation.set_visible(False)
            self.change(lambda: self.backend.set_wifi_radio(enabled))

        toggle = self._switch("Wi-Fi radio", wifi_radio_change)
        confirmation = self.shell._class(
            self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=5),
            self._style("confirm"))
        caution = self.Gtk.Label(
            label="Turning Wi-Fi off may interrupt remote connections. Continue?", xalign=0)
        caution.set_line_wrap(True)
        confirmation.pack_start(caution, False, False, 0)
        buttons = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=7)
        cancel = self.shell._class(self.Gtk.Button(label="Keep Wi-Fi on"), self._style("mini"))
        confirm = self.shell._class(self.Gtk.Button(label="Turn Wi-Fi off"), self._style("mini"))
        cancel.connect("clicked", lambda _button: confirmation.set_visible(False))

        def confirm_off(_button):
            confirmation.set_visible(False)
            self.change(lambda: self.backend.set_wifi_radio(False))

        confirm.connect("clicked", confirm_off)
        buttons.pack_start(cancel, True, True, 0)
        buttons.pack_start(confirm, True, True, 0)
        confirmation.pack_start(buttons, False, False, 0)
        confirmation.show_all()
        confirmation.set_no_show_all(True)
        confirmation.hide()
        self._add(confirmation)
        self._label("The radio switch changes real NetworkManager state. Turning it off can disconnect this computer.",
                    self._style("hint"))
        self._label("Nearby networks", self._style("section"))
        networks_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=5)
        self._add(networks_box)

        def read():
            return self.backend.read_wifi_radio(), self.backend.read_wifi_networks()

        def render(snapshot):
            enabled, networks = snapshot
            toggle.set_active(bool(enabled))
            toggle.set_sensitive(enabled is not None)
            for child in tuple(networks_box.get_children()):
                networks_box.remove(child)
            for network in networks[:8]:
                line = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=8)
                line.pack_start(self.Gtk.Label(label=f"{network.ssid[:35]} · {network.signal}%" +
                                                     ("  ✓" if network.connected else ""), xalign=0),
                                True, True, 0)
                action = self.shell._class(self.Gtk.Button(
                    label="Disconnect" if network.connected else "Connect"),
                    self._style("mini"))
                if network.connected:
                    action.connect("clicked", lambda _button:
                                   self.change(self.backend.disconnect_wifi))
                else:
                    action.connect("clicked", lambda _button, ssid=network.ssid:
                                   self.change(lambda: self.backend.connect_wifi(ssid)))
                action.set_sensitive(enabled is True)
                line.pack_end(action, False, False, 0)
                networks_box.pack_start(line, False, False, 0)
            if not networks:
                networks_box.pack_start(self.Gtk.Label(label="No visible Wi-Fi networks reported", xalign=0),
                                        False, False, 0)
            networks_box.show_all()
            toggle.set_sensitive(enabled is not None)
            if enabled is None:
                return "NetworkManager Wi-Fi state unavailable; native radio control disabled"
            return "Wi-Fi on" if enabled else "Wi-Fi off"

        self.bind(read, render)

    def bluetooth(self):
        toggle = self._switch("Bluetooth adapter", lambda state:
                              self.change(lambda: self.backend.set_bluetooth_power(state)))
        devices = self._label("Connected devices: checking…", self._style("hint"))
        device_rows = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=5)
        if self.runner is not None:
            self._add(device_rows)

        def render(state):
            toggle.set_active(bool(state.powered))
            toggle.set_sensitive(state.powered is not None)
            devices.set_text("Connected devices: " +
                             (", ".join(state.connected) if state.connected else "none reported"))
            for child in tuple(device_rows.get_children()):
                child.destroy()
            if self.runner is not None:
                for device in state.devices[:8]:
                    row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=6)
                    row.pack_start(self.Gtk.Label(label=device.name[:45], xalign=0),
                                   True, True, 0)
                    button = self.shell._class(
                        self.Gtk.Button(label="Disconnect" if device.connected else "Connect"),
                        self._style("mini"))
                    button.set_sensitive(state.powered is True and
                                         (device.paired or device.connected) and not self._busy)
                    button.get_accessible().set_name(
                        ("Disconnect " if device.connected else "Connect ") + device.name)
                    button.connect("clicked", lambda _button, item=device:
                                   self.change(lambda: self.backend.set_bluetooth_connection(
                                       item.address, not item.connected)))
                    row.pack_end(button, False, False, 0)
                    device_rows.pack_start(row, False, False, 0)
                if not state.devices:
                    device_rows.pack_start(self.Gtk.Label(label="No paired devices reported", xalign=0),
                                           False, False, 0)
                device_rows.show_all()
            if state.powered is None:
                return "BlueZ controller unavailable; adapter control disabled"
            return "Bluetooth on" if state.powered else "Bluetooth off"

        self.bind(self.backend.read_bluetooth, render)

    def output_sound(self):
        slider = self._scale("Output volume", lambda value:
                              self.change(lambda: self.backend.set_sound_volume(value)))
        mute = self._switch("Mute output", lambda state:
                             self.change(lambda: self.backend.set_sound_mute(state)))

        def render(state):
            slider.set_value(min(100, state.percent or 0))
            slider.set_sensitive(state.percent is not None)
            mute.set_active(bool(state.muted))
            mute.set_sensitive(state.muted is not None)
            if state.percent is None:
                return "Audio backend unavailable; install WirePlumber or PulseAudio tools"
            return f"Output {state.percent}%" + (" · Muted" if state.muted else "")

        self.bind(self.backend.read_sound, render)

    def audio_devices(self):
        combo = self._combo("Default output device", lambda name:
                            self.change(lambda: self.backend.set_sound_output(name)))
        microphone = self._scale("Microphone input volume", lambda value:
                                 self.change(lambda: self.backend.set_microphone_volume(value)))
        mute = self._switch("Mute microphone", lambda state:
                             self.change(lambda: self.backend.set_microphone_mute(state)))

        def read():
            return self.backend.read_sound_outputs(), self.backend.read_microphone()

        def render(snapshot):
            outputs, state = snapshot
            combo.remove_all()
            for output in outputs:
                combo.append(output.name, output.label[:65])
                if output.active:
                    combo.set_active_id(output.name)
            combo.set_sensitive(bool(outputs))
            microphone.set_value(min(100, state.percent or 0))
            microphone.set_sensitive(state.percent is not None)
            mute.set_active(bool(state.muted))
            mute.set_sensitive(state.muted is not None)
            if not outputs and state.percent is None:
                return "No audio outputs or microphone backend reported"
            return "Audio devices detected; controls reflect actual device state"

        self.bind(read, render)

    def display(self):
        slider = self._scale("Laptop screen brightness", lambda value:
                              self.change(lambda: self.backend.set_brightness(value)), minimum=1)
        self._label("Backlight access requires a supported device and permission to use brightnessctl.",
                    self._style("hint"))

        def render(value):
            slider.set_value(value or 1)
            slider.set_sensitive(value is not None and bool(shutil.which("brightnessctl")))
            if value is None:
                return "No writable laptop backlight reported"
            if not shutil.which("brightnessctl"):
                return f"Brightness {value}% · install brightnessctl to change it"
            return f"Brightness {value}%"

        self.bind(self.backend.read_brightness, render)

    def battery(self):
        summary = self._label("Battery: checking…", self._style("section"))
        bar = self.Gtk.LevelBar.new_for_interval(0, 100)
        self._add(bar)

        def render(state):
            summary.set_text(f"{state.percent}% · {state.label}" if state else
                             "No battery reported by Linux (desktop/AC-only device)")
            bar.set_value(state.percent if state else 0)
            bar.set_visible(state is not None)
            return f"Battery {state.percent}%" if state else "No laptop battery detected"

        self.bind(self.backend.read_battery, render)

    def power(self):
        combo = self._combo("Performance / power profile", lambda name:
                            self.change(lambda: self.backend.set_power_profile(name)))
        self._label("Profiles are offered only when power-profiles-daemon supports them.",
                    self._style("hint"))

        def render(snapshot):
            current, supported = snapshot
            combo.remove_all()
            for option in supported:
                combo.append(option, option.replace("-", " ").title())
            if current:
                combo.set_active_id(current)
            combo.set_sensitive(bool(current and supported))
            return ("Power profile: " + current.replace("-", " ") if current else
                    "No supported power-profiles-daemon profile available")

        self.bind(self.backend.read_power_profiles, render)


def build_native_controls(shell, Gtk, GLib, parent, category, title, *, is_current,
                          backend=None, runner=None):
    """Attach a device-specific Linux control surface when one is supported."""
    key = (category, title)
    if key not in NATIVE_TASKS:
        return None
    panel = NativeAquaControls(shell, Gtk, GLib, parent, is_current=is_current,
                               backend=backend, runner=runner)
    handler = {
        ("connections", "Network connections"): panel.wifi,
        ("connections", "Bluetooth devices"): panel.bluetooth,
        ("sound", "Output volume & mute"): panel.output_sound,
        ("sound", "Input & output devices"): panel.audio_devices,
        ("display", "Display configuration"): panel.display,
        ("power", "Battery status"): panel.battery,
        ("power", "Power management"): panel.power,
    }[key]
    handler()
    return panel
