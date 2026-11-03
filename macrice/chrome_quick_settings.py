"""ChromeOS-like Quick Settings made of genuine Linux navigation and status.

The XFCE notification daemon continues to own external notifications. Network,
Bluetooth, brightness and other privileged controls are *not* represented by
fake on/off buttons. Every enabled action opens an installed XFCE utility.
"""

from __future__ import annotations

import shutil

from .chrome_shell import apply_rounded_window_shape


QUICK_ACTIONS = (
    ("Network", "network-wireless", "nm-connection-editor", "Connection settings"),
    ("Bluetooth", "bluetooth", "blueman-manager", "Bluetooth settings"),
    ("Display", "video-display", "xfce4-display-settings", "Display & brightness"),
    ("Notifications", "preferences-system-notifications",
     "xfce4-notifyd-config", "Notification preferences"),
    ("Power", "battery", "xfce4-power-manager-settings", "Power settings"),
    ("Keyboard", "input-keyboard", "xfce4-keyboard-settings", "Keyboard settings"),
)


def build(shell, Gtk, Gdk, GLib):
    from gi.repository import Pango
    actions = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    actions.set_title("RiceBowl ChromeOS Quick Settings")
    actions.set_decorated(False)
    actions.set_resizable(True)
    actions.set_skip_taskbar_hint(True)
    actions.set_skip_pager_hint(True)
    actions.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    actions.set_transient_for(shell.bar)
    actions.set_keep_above(True)
    actions.set_default_size(396, 608)

    root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12),
                        "chrome-quick-root")
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
    title = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    title.pack_start(shell._class(
        Gtk.Label(label="Quick Settings", xalign=0), "chrome-quick-title"),
        False, False, 0)
    shell.chrome_quick_clock = shell._class(
        Gtk.Label(label="", xalign=0), "chrome-quick-date")
    title.pack_start(shell.chrome_quick_clock, False, False, 0)
    header.pack_start(title, True, True, 0)
    for name, icon, command in (
        ("Settings", "preferences-system", "xfce4-settings-manager"),
        ("Sign out", "system-shutdown", "xfce4-session-logout"),
    ):
        button = shell._class(Gtk.Button(), "chrome-launcher-settings")
        button.set_image(shell._icon(icon, Gtk.IconSize.MENU))
        button.set_tooltip_text(
            "Open " + name if shutil.which(command) else command + " is not installed")
        button.get_accessible().set_name("Open " + name)
        button.set_sensitive(shutil.which(command) is not None)
        button.connect("clicked", lambda _button, cmd=command: shell._open_tool(cmd))
        header.pack_end(button, False, False, 0)
    root.pack_start(header, False, False, 0)

    section = shell._class(Gtk.Label(label="Connectivity & device", xalign=0),
                           "chrome-section-caption")
    root.pack_start(section, False, False, 0)
    grid = Gtk.Grid(row_spacing=7, column_spacing=7)
    grid.set_column_homogeneous(True)
    for index, (name, icon_name, command, explanation) in enumerate(QUICK_ACTIONS):
        button = shell._class(Gtk.Button(), "chrome-quick-button")
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        content.pack_start(shell._icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR),
                           False, False, 0)
        description = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        caption = shell._class(Gtk.Label(label=name, xalign=0),
                               "chrome-quick-action")
        description.pack_start(caption, False, False, 0)
        detail = shell._class(Gtk.Label(label=explanation, xalign=0),
                              "chrome-quick-detail")
        detail.set_ellipsize(Pango.EllipsizeMode.END)
        detail.set_max_width_chars(15)
        description.pack_start(detail, False, False, 0)
        content.pack_start(description, True, True, 0)
        # These launch real Linux settings; the chevron makes that different
        # from the actual on/off controls below, which verify their state.
        arrow = shell._class(Gtk.Label(label="›"), "chrome-quick-chevron")
        content.pack_end(arrow, False, False, 0)
        button.add(content)
        button.get_accessible().set_name("Open " + name + " settings")
        available = shutil.which(command) is not None
        button.set_sensitive(available)
        button.set_tooltip_text(
            explanation if available else command + " is not installed")
        button.connect("clicked", lambda _button, cmd=command: shell._open_tool(cmd))
        grid.attach(button, index % 2, index // 2, 1, 1)
        if name == "Network":
            shell.chrome_network_detail = detail
    root.pack_start(grid, False, False, 0)

    root.pack_start(shell._class(
        Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), "chrome-divider"),
        False, False, 0)
    root.pack_start(shell._class(
        Gtk.Label(label="Volume", xalign=0), "chrome-section-caption"),
        False, False, 0)
    audio = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                         "chrome-surface")
    shell.volume_status_label = shell._class(
        Gtk.Label(label="Reading audio output…", xalign=0), "chrome-status-line")
    audio.pack_start(shell.volume_status_label, False, False, 0)
    volume = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    volume.pack_start(shell._icon("audio-volume-high", Gtk.IconSize.MENU),
                      False, False, 0)
    shell.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    shell.volume_scale.set_draw_value(False)
    shell.volume_scale.set_sensitive(False)
    shell.volume_scale.set_hexpand(True)
    shell.volume_scale.set_tooltip_text("Change and verify real system output volume")
    shell.volume_scale.get_accessible().set_name("System output volume")
    shell.volume_scale.connect("value-changed", shell._queue_volume_change)
    volume.pack_start(shell.volume_scale, True, True, 0)
    audio.pack_start(volume, False, False, 0)
    shell.mute_button = shell._class(Gtk.ToggleButton(label="Mute output"),
                                    "chrome-quick-mute")
    shell.mute_button.set_sensitive(False)
    shell.mute_button.get_accessible().set_name("Mute or unmute system output")
    shell.mute_button.connect("clicked", shell._toggle_output_mute)
    audio.pack_start(shell.mute_button, False, False, 0)
    root.pack_start(audio, False, False, 0)

    hardware = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5),
                            "chrome-surface")
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: reading…", xalign=0), "chrome-status-line")
    shell.control_battery_label = shell._class(
        Gtk.Label(label="Battery: reading…", xalign=0), "chrome-status-line")
    shell.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
    shell.control_battery_level.set_no_show_all(True)
    hardware.pack_start(shell.control_network_label, False, False, 0)
    hardware.pack_start(shell.control_battery_label, False, False, 0)
    hardware.pack_start(shell.control_battery_level, False, False, 0)
    root.pack_start(hardware, False, False, 0)
    # The real network/battery/sound states already appear directly above;
    # avoid a duplicated footer that gets clipped on 1024x768 laptops.
    # A plain GtkBox is windowless; it inherits the exact X11 shape of the
    # top-level popup. An extra ScrolledWindow creates its own Gdk child window
    # whose rectangular backing can leak outside the rounded top-level mask.
    # The content is intentionally bounded to fit the 608px popup on 768px
    # desktops, with no redundant status footer.
    actions.add(root)

    def shape_later(*_args):
        GLib.idle_add(apply_rounded_window_shape, actions, 26)
        return False
    actions.connect("configure-event", shape_later)
    actions.connect("map-event", shape_later)
    actions.connect("focus-out-event",
                    lambda *_args: shell._schedule_popup_hide("control"))
    actions.connect("key-press-event",
                    lambda _widget, event: shell._action_key(event))
    return actions
