"""Small Win98-style notification-area panels for real Linux device state."""

from __future__ import annotations

import shutil


def build(shell, Gtk, Gdk):
    """Install separate transient mini-panels without a second tray host."""
    popups = {}

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
        win.add(root)
        win.connect("key-press-event", lambda _window, event:
                    _on_key(win, event, Gdk))
        win.connect("focus-out-event", lambda *_args: win.hide())
        popups[name] = win
        return root

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

    network = popup("network", "Network", 280)
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: checking…", xalign=0), "rice-control-detail")
    network.pack_start(shell.control_network_label, False, False, 0)
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

    def show(kind):
        if kind not in popups:
            return
        win = popups[kind]
        was_visible = win.get_visible()
        for other in popups.values():
            other.hide()
        if was_visible:
            return
        shell._hide_menu()
        shell._refresh_status_async()
        win.show_all()
        rect = shell._desktop_rect()
        width, height = win.get_size()
        button = shell._status_widgets.get(kind, (None,))[0]
        if button and button.get_window():
            origin = button.get_window().get_origin()
            x = origin[1] if len(origin) == 3 else origin[0]
        else:
            x = rect.x + rect.width - width - 12
        win.move(max(rect.x + 4, min(x, rect.x + rect.width - width - 4)),
                 max(rect.y + 4, rect.y + rect.height - 34 - height - 5))
        win.present()

    def close():
        for window in popups.values():
            window.destroy()

    shell.classic98_tray_show = show
    shell.classic98_tray_close = close


def _on_key(window, event, Gdk):
    if event.keyval == Gdk.KEY_Escape:
        window.hide()
        return True
    return False
