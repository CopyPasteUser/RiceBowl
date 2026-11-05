"""Small Win98-style notification-area panels for real Linux device state."""

from __future__ import annotations

import shutil

from .aero_layout import anchored_popup_x
from .riceware import spice


MAX_NETWORKS = 12
MAX_DEVICES = 10


def network_caption(network):
    security = "Secured" if network.security and network.security != "--" else "Open"
    return f"{network.signal}% · {security}" + (" · Connected" if network.connected else "")


def build(shell, Gtk, Gdk):
    """Install separate transient mini-panels without a second tray host."""
    from gi.repository import GLib, Pango

    popups = {}
    epochs = {}
    pending = set()
    centered_popups = set()
    notices = {"network": "", "bluetooth": "", "brightness": ""}
    brightness_source = 0
    brightness_programmatic = False

    def label(text, *, wrapping=False):
        widget = Gtk.Label(label=text, xalign=0)
        widget.set_line_wrap(wrapping)
        return widget

    def action(text, callback):
        button = shell._class(Gtk.Button(label=text), "classic98-tray-action")
        button.get_accessible().set_name(text)
        caption = button.get_child()
        if isinstance(caption, Gtk.Label):
            caption.set_ellipsize(Pango.EllipsizeMode.END)
            caption.set_max_width_chars(28)
        button.connect("clicked", lambda _button: callback())
        return button

    def clear(box):
        for child in box.get_children():
            box.remove(child)

    def submit(kind, key, operation, callback, *, on_stale=None):
        generation = epochs[kind]

        def delivered(result):
            if generation != epochs[kind] or not popups[kind].get_visible():
                if on_stale:
                    on_stale()
                return
            callback(result)

        shell.classic98_controller.submit(kind + "-" + key, operation, delivered)

    def popup(name, title, width=275):
        win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        win.set_title(title)
        win.set_decorated(False)
        win.set_resizable(False)
        win.set_skip_taskbar_hint(True)
        win.set_skip_pager_hint(True)
        win.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        win.set_transient_for(shell.bar)
        win.set_keep_above(True)
        win.set_default_size(width, -1)
        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7),
                            "classic98-tray-popup")
        heading = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6),
                                "classic98-tray-title")
        heading.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
        close = Gtk.Button(label="×")
        close.get_accessible().set_name("Close " + title)
        close.connect("clicked", lambda _widget: win.hide())
        heading.pack_end(close, False, False, 0)
        root.pack_start(heading, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        scroll.set_max_content_height(max(200, min(475, shell._desktop_rect().height - 85)))
        scroll.add(root)
        win.add(scroll)
        win.connect("key-press-event", lambda _window, event:
                    _on_key(win, event, Gdk))
        win.connect("focus-out-event", lambda *_args: win.hide())
        win.connect("size-allocate", lambda _win, _allocation, kind=name:
                    GLib.idle_add(place, kind))
        epochs[name] = 0
        win.connect("hide", lambda _win, kind=name: on_hide(kind))
        popups[name] = win
        return root

    def on_hide(kind):
        nonlocal brightness_source
        epochs[kind] += 1
        if kind == "network":
            clear(network_list)
            network_feedback.set_text("")
        elif kind == "bluetooth":
            clear(bluetooth_list)
            bluetooth_feedback.set_text("")
        elif kind == "audio":
            clear(audio_outputs)
        elif kind == "battery" and brightness_source:
            GLib.source_remove(brightness_source)
            brightness_source = 0

    audio = popup("audio", "Volume Control", 255)
    shell.volume_status_label = shell._class(
        Gtk.Label(label="Reading system volume…", xalign=0), "rice-control-detail")
    audio.pack_start(shell.volume_status_label, False, False, 0)
    shell.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    shell.volume_scale.set_draw_value(False)
    shell.volume_scale.set_sensitive(False)
    shell.volume_scale.get_accessible().set_name("System output volume")
    shell.volume_scale.connect("value-changed", shell._queue_volume_change)
    audio.pack_start(shell.volume_scale, False, False, 0)
    shell.mute_button = shell._class(Gtk.ToggleButton(label="Mute"), "rice-mute")
    shell.mute_button.set_sensitive(False)
    shell.mute_button.get_accessible().set_name("Mute or unmute output")
    shell.mute_button.connect("clicked", shell._toggle_output_mute)
    audio.pack_start(shell.mute_button, False, False, 0)
    more_audio = Gtk.Button(label="Audio Properties…")
    more_audio.set_sensitive(bool(shutil.which("pavucontrol")))
    more_audio.connect("clicked", lambda _widget: shell._open_tool("pavucontrol"))
    audio.pack_start(more_audio, False, False, 0)
    audio.pack_start(label("Output device"), False, False, 0)
    audio_outputs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    audio.pack_start(audio_outputs, False, False, 0)

    network = popup("network", "Network", 280)
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: checking…", xalign=0), "rice-control-detail")
    network.pack_start(shell.control_network_label, False, False, 0)
    network_feedback = label("", wrapping=True)
    network.pack_start(network_feedback, False, False, 0)
    wifi_toggle = action("Checking Wi-Fi…", lambda: change_wifi())
    wifi_toggle.set_sensitive(False)
    network.pack_start(wifi_toggle, False, False, 0)
    wifi_disconnect = action("Disconnect Wi-Fi", lambda: change_network("wifi_disconnect"))
    wifi_disconnect.set_sensitive(False)
    network.pack_start(wifi_disconnect, False, False, 0)
    network.pack_start(label("Available wireless networks"), False, False, 0)
    network_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    network.pack_start(network_list, False, False, 0)
    network.pack_start(action("Refresh", lambda: refresh_network(rescan=True)), False, False, 0)
    connections = Gtk.Button(label="Network Connections…")
    connections.set_sensitive(bool(shutil.which("nm-connection-editor")))
    connections.connect("clicked", lambda _widget: shell._open_tool("nm-connection-editor"))
    network.pack_start(connections, False, False, 0)

    battery = popup("battery", "Power Meter", 255)
    shell.control_battery_label = shell._class(
        Gtk.Label(label="Battery: checking…", xalign=0), "rice-control-detail")
    battery.pack_start(shell.control_battery_label, False, False, 0)
    shell.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
    shell.control_battery_level.set_value(0)
    shell.control_battery_level.set_no_show_all(True)
    battery.pack_start(shell.control_battery_level, False, False, 0)
    battery.pack_start(label("Screen brightness"), False, False, 0)
    brightness_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 100, 5)
    brightness_scale.set_sensitive(False)
    brightness_scale.set_draw_value(True)
    brightness_scale.get_accessible().set_name("Screen brightness")
    battery.pack_start(brightness_scale, False, False, 0)
    brightness_feedback = label("Checking screen brightness…", wrapping=True)
    battery.pack_start(brightness_feedback, False, False, 0)
    battery.pack_start(label("Power scheme"), False, False, 0)
    profile_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    battery.pack_start(profile_box, False, False, 0)
    power = Gtk.Button(label="Power Management…")
    power.set_sensitive(bool(shutil.which("xfce4-power-manager-settings")))
    power.connect("clicked", lambda _widget: shell._open_tool("xfce4-power-manager-settings"))
    battery.pack_start(power, False, False, 0)

    calendar = popup("clock", "Date and Time", 265)
    calendar.pack_start(Gtk.Calendar(), False, False, 0)
    date = Gtk.Button(label="Date & Time Settings…")
    command = next((cmd for cmd in ("time-admin", "gnome-control-center")
                    if shutil.which(cmd)), None)
    date.set_sensitive(command is not None)
    if command:
        date.connect("clicked", lambda _widget: shell._open_tool(command))
    calendar.pack_start(date, False, False, 0)

    bluetooth = popup("bluetooth", "Bluetooth", 280)
    bluetooth_feedback = label("Checking Bluetooth adapter…", wrapping=True)
    bluetooth.pack_start(bluetooth_feedback, False, False, 0)
    bluetooth_toggle = action("Bluetooth unavailable", lambda: change_bluetooth())
    bluetooth_toggle.set_sensitive(False)
    bluetooth.pack_start(bluetooth_toggle, False, False, 0)
    bluetooth.pack_start(label("Known devices"), False, False, 0)
    bluetooth_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    bluetooth.pack_start(bluetooth_list, False, False, 0)
    bluetooth.pack_start(action("Refresh devices", lambda: refresh_bluetooth()),
                         False, False, 0)
    manager = Gtk.Button(label="Bluetooth devices…")
    manager.set_sensitive(shutil.which("blueman-manager") is not None)
    manager.connect("clicked", lambda _button: shell._open_tool("blueman-manager"))
    bluetooth.pack_start(manager, False, False, 0)

    def render_message(box, message):
        clear(box)
        box.pack_start(label(message, wrapping=True), False, False, 0)
        box.show_all()

    def refresh_outputs():
        render_message(audio_outputs, "Checking output devices…")

        def ready(result):
            if result.status != "ok":
                render_message(audio_outputs, result.reason or "No selectable sound outputs")
                return
            clear(audio_outputs)
            for output in result.value[:8]:
                button = action(("✓ " if output.active else "○ ") + output.label,
                                lambda name=output.name: change_output(name))
                button.set_sensitive(not output.active and "audio-write" not in pending)
                button.set_tooltip_text(output.name)
                audio_outputs.pack_start(button, False, False, 0)
            audio_outputs.show_all()

        submit("audio", "outputs", lambda: spice.read("audio_outputs"), ready)

    def change_output(name):
        if "audio-write" in pending:
            return
        pending.add("audio-write")
        shell.volume_status_label.set_text("Switching sound output…")

        def finished(result):
            pending.discard("audio-write")
            if result.status != "ok":
                shell.volume_status_label.set_text("Output change failed: " +
                                                   (result.reason or "Not verified"))
            else:
                shell._refresh_status_async()
            refresh_outputs()

        submit("audio", "output-write", lambda: spice.change("audio_output", name),
               finished, on_stale=lambda: pending.discard("audio-write"))

    def refresh_network(*, rescan=False):
        if "network-write" in pending:
            return
        network_feedback.set_text("Looking for Wi-Fi networks…")
        wifi_toggle.set_sensitive(False)
        wifi_disconnect.set_sensitive(False)
        render_message(network_list, "Scanning…" if rescan else "Reading networks…")

        def ready(result):
            if not isinstance(result, tuple):
                network_feedback.set_text(result.reason or "NetworkManager unavailable")
                wifi_toggle.set_label("Wi-Fi unavailable")
                render_message(network_list, "No network backend available")
                return
            radio, scan = result
            available = radio.status == "ok" and type(radio.value) is bool
            enabled = radio.value if available else None
            wifi_toggle.set_sensitive(available)
            wifi_toggle.set_label("Turn Wi-Fi off" if enabled else
                                  "Turn Wi-Fi on" if enabled is False else "Wi-Fi unavailable")
            networks = scan.value if scan.status == "ok" and enabled else ()
            wifi_disconnect.set_sensitive(bool(networks) and any(n.connected for n in networks))
            network_feedback.set_text(notices["network"] or (
                radio.reason or "NetworkManager unavailable" if not available else
                scan.reason or "Unable to scan Wi-Fi" if scan.status != "ok" and enabled else
                "Wi-Fi is off" if not enabled else "Connected networks are marked ✓"))
            clear(network_list)
            for network in networks[:MAX_NETWORKS]:
                button = action(("✓ " if network.connected else "○ ") + network.ssid,
                                lambda ssid=network.ssid: change_network("wifi_connect", ssid))
                button.set_sensitive(not network.connected)
                button.set_tooltip_text(network_caption(network))
                button.get_accessible().set_name(
                    ("Connected to " if network.connected else "Connect to ") + network.ssid)
                network_list.pack_start(button, False, False, 0)
            if not networks:
                network_list.pack_start(label("No networks available" if enabled else
                                              "Enable Wi-Fi to list networks"), False, False, 0)
            network_list.show_all()

        submit("network", "scan", lambda: (spice.read("wifi"),
               spice.scan_wifi(rescan=rescan)), ready)

    def change_wifi():
        if "network-write" in pending:
            return
        # Probe again in the worker. Another desktop app may have changed Wi-Fi.
        def toggle():
            state = spice.read("wifi")
            return spice.change("wifi", not state.value) if state.status == "ok" else state

        change_network("wifi", operation=toggle)

    def change_network(action_name, ssid=None, *, operation=None):
        if "network-write" in pending:
            return
        pending.add("network-write")
        notices["network"] = ""
        wifi_toggle.set_sensitive(False)
        wifi_disconnect.set_sensitive(False)
        network_feedback.set_text("Applying network change…")

        def complete(result):
            pending.discard("network-write")
            if result.status != "ok":
                notices["network"] = ((result.reason or "Change not verified") +
                                      ". Use Network Connections for credentials.")
            else:
                network_feedback.set_text("Network change verified")
            refresh_network()
            shell._refresh_status_async()

        def stale():
            pending.discard("network-write")
            if popups["network"].get_visible():
                refresh_network()

        submit("network", "write", operation or
               (lambda: spice.change(action_name, ssid)), complete, on_stale=stale)

    def refresh_bluetooth():
        if "bluetooth-write" in pending:
            return
        bluetooth_toggle.set_sensitive(False)
        bluetooth_feedback.set_text("Reading Bluetooth devices…")

        def ready(result):
            clear(bluetooth_list)
            state = result.value if result.status == "ok" else None
            powered = state.powered if state else None
            bluetooth_toggle.set_sensitive(type(powered) is bool)
            bluetooth_toggle.set_label("Turn Bluetooth off" if powered else
                                       "Turn Bluetooth on" if powered is False else
                                       "Bluetooth unavailable")
            bluetooth_feedback.set_text(notices["bluetooth"] or (
                "Adapter on" if powered else "Adapter off" if powered is False else
                result.reason or "No Bluetooth backend"))
            for device in (state.devices if state else ())[:MAX_DEVICES]:
                title = ("✓ " if device.connected else "○ ") + device.name
                button = action(title, lambda item=device:
                                change_bluetooth_device(item.address, item.connected))
                button.set_sensitive(bool(powered) and device.paired)
                button.set_tooltip_text(device.address if device.paired else
                                        "Pair this device using Bluetooth settings first")
                bluetooth_list.pack_start(button, False, False, 0)
            if not bluetooth_list.get_children():
                bluetooth_list.pack_start(label("No paired devices"), False, False, 0)
            bluetooth_list.show_all()

        submit("bluetooth", "read", lambda: spice.read("bluetooth"), ready)

    def change_bluetooth():
        if "bluetooth-write" in pending:
            return
        def toggle():
            state = spice.read("bluetooth")
            return spice.change("bluetooth_power", not state.value.powered) if (
                state.status == "ok" and type(state.value.powered) is bool) else state
        write_bluetooth(toggle)

    def change_bluetooth_device(address, connected):
        write_bluetooth(lambda: spice.change(
            "bluetooth_disconnect" if connected else "bluetooth_connect", address))

    def write_bluetooth(operation):
        if "bluetooth-write" in pending:
            return
        pending.add("bluetooth-write")
        notices["bluetooth"] = ""
        bluetooth_toggle.set_sensitive(False)
        bluetooth_feedback.set_text("Applying Bluetooth change…")

        def done(result):
            pending.discard("bluetooth-write")
            if result.status != "ok":
                notices["bluetooth"] = result.reason or "Bluetooth change not verified"
            refresh_bluetooth()

        def stale():
            pending.discard("bluetooth-write")
            if popups["bluetooth"].get_visible():
                refresh_bluetooth()

        submit("bluetooth", "write", operation, done, on_stale=stale)

    def refresh_power():
        def brightness_ready(result):
            nonlocal brightness_programmatic
            value = result.value if result.status == "ok" else None
            valid = type(value) is int
            brightness_scale.set_sensitive(valid and "brightness-write" not in pending)
            brightness_feedback.set_text(notices["brightness"] or (
                "Brightness available" if valid else
                result.reason or "Brightness unavailable"))
            if valid and "brightness-write" not in pending:
                brightness_programmatic = True
                try:
                    brightness_scale.set_value(value)
                finally:
                    brightness_programmatic = False

        def profiles_ready(result):
            clear(profile_box)
            current, options = result.value if result.status == "ok" else (None, ())
            for name in options[:3]:
                button = action(("✓ " if name == current else "○ ") + name,
                                lambda selection=name: change_profile(selection))
                button.set_sensitive(name != current and "profile-write" not in pending)
                profile_box.pack_start(button, False, False, 0)
            if not options:
                profile_box.pack_start(label(result.reason or "No power profile backend"),
                                       False, False, 0)
            profile_box.show_all()

        submit("battery", "brightness", lambda: spice.read("brightness"), brightness_ready)
        submit("battery", "profiles", lambda: spice.read("power_profiles"), profiles_ready)

    def queue_brightness(_slider):
        nonlocal brightness_source
        if brightness_programmatic or "brightness-write" in pending:
            return
        if brightness_source:
            GLib.source_remove(brightness_source)
        brightness_source = GLib.timeout_add(280, write_brightness)

    def write_brightness():
        nonlocal brightness_source
        brightness_source = 0
        if "brightness-write" in pending or not popups["battery"].get_visible():
            return False
        pending.add("brightness-write")
        notices["brightness"] = ""
        brightness_scale.set_sensitive(False)
        value = int(round(brightness_scale.get_value()))

        def done(result):
            pending.discard("brightness-write")
            if result.status != "ok":
                notices["brightness"] = result.reason or "Brightness change not verified"
            refresh_power()

        submit("battery", "brightness-write", lambda: spice.change("brightness", value),
               done, on_stale=lambda: pending.discard("brightness-write"))
        return False

    def change_profile(name):
        if "profile-write" in pending:
            return
        pending.add("profile-write")
        render_message(profile_box, "Switching power scheme…")

        def done(result):
            pending.discard("profile-write")
            if result.status != "ok":
                render_message(profile_box, result.reason or "Power change not verified")
                profile_box.pack_start(action("Retry", lambda: refresh_power()),
                                       False, False, 0)
                profile_box.show_all()
            else:
                refresh_power()

        submit("battery", "profile-write", lambda: spice.change("power_profile", name),
               done, on_stale=lambda: pending.discard("profile-write"))

    brightness_scale.connect("value-changed", queue_brightness)

    def place(kind):
        win = popups[kind]
        if not win.get_visible():
            return False
        rect = shell._desktop_rect()
        width, height = win.get_size()
        if kind in centered_popups:
            x = rect.x + (rect.width - width) // 2
            y = rect.y + (rect.height - height - 34) // 2
        else:
            anchor = (shell.classic98_clock_button if kind == "clock" else
                      getattr(shell, "classic98_bluetooth_button", None) if kind == "bluetooth" else
                      shell._status_widgets.get(kind, (None,))[0])
            offset = (anchor.translate_coordinates(shell.bar, 0, 0)
                      if anchor is not None and shell.bar.get_window() else None)
            # Gtk.Button is usually a NO_WINDOW widget: anchor.get_window()
            # belongs to the whole taskbar and its origin is at the far left.
            button_x = (shell.bar.get_window().get_root_origin()[0] + offset[0]
                        if offset is not None else rect.x + rect.width - 16)
            button_width = anchor.get_allocated_width() if offset is not None else 24
            x = anchored_popup_x(rect.x, rect.width, button_x, button_width, width)
            y = rect.y + rect.height - 34 - height - 5
        x = max(rect.x + 4, min(x, rect.x + rect.width - width - 4))
        y = max(rect.y + 4, y)
        if win.get_window() and win.get_window().get_root_origin() != (x, y):
            win.move(x, y)
        return False

    def show(kind, *, centered=False):
        if kind not in popups:
            return
        win = popups[kind]
        was_visible = win.get_visible()
        for other in popups.values():
            other.hide()
        if was_visible:
            return
        shell._hide_menu()
        if getattr(shell, "actions", None) is not None and shell.actions.get_visible():
            shell._hide_actions()
        shell._refresh_status_async()
        centered_popups.discard(kind)
        if centered:
            centered_popups.add(kind)
        win.show_all()
        place(kind)
        win.present()
        GLib.idle_add(place, kind)
        if kind == "network":
            refresh_network()
        elif kind == "bluetooth":
            refresh_bluetooth()
        elif kind == "battery":
            refresh_power()
        elif kind == "audio":
            refresh_outputs()

    def close():
        nonlocal brightness_source
        if brightness_source:
            GLib.source_remove(brightness_source)
            brightness_source = 0
        for window in popups.values():
            window.destroy()

    def hide_all():
        for window in popups.values():
            window.hide()

    shell.classic98_tray_show = show
    shell.classic98_tray_hide = hide_all
    shell.classic98_tray_close = close
    shell.classic98_tray_popups = popups


def _on_key(window, event, Gdk):
    if event.keyval == Gdk.KEY_Escape:
        window.hide()
        return True
    return False
