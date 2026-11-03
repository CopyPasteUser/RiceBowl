"""Windows 10 notification flyout built from real XFCE actions and Linux status."""

from __future__ import annotations

import shutil


QUICK_ACTIONS = (
    ("Network", "network-wireless", "nm-connection-editor"),
    ("Bluetooth", "bluetooth", "blueman-manager"),
    ("Display", "video-display", "xfce4-display-settings"),
    ("All settings", "preferences-system", "xfce4-settings-manager"),
    ("Sound", "audio-volume-high", "pavucontrol"),
    ("Power", "battery", "xfce4-power-manager-settings"),
    ("Appearance", "preferences-desktop-theme", "xfce4-appearance-settings"),
    ("Keyboard", "input-keyboard", "xfce4-keyboard-settings"),
)


def build(shell, Gtk, Gdk):
    """Use the shared shell's status/volume callbacks; no pretend toggles.

    Notifications remain the job of xfce4-notifyd until RiceBowl has its own
    notification backend. This flyout explicitly reports that boundary.
    """
    actions = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    actions.set_title("RiceBowl Windows 10 Action Center")
    actions.set_decorated(False)
    actions.set_resizable(True)
    actions.set_skip_taskbar_hint(True)
    actions.set_skip_pager_hint(True)
    actions.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    actions.set_transient_for(shell.bar)
    actions.set_keep_above(True)
    actions.set_default_size(362, 680)
    root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                        "ten-action-root")

    header = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8),
                          "ten-action-header")
    header.pack_start(shell._class(Gtk.Label(label="Action center", xalign=0),
                                   "ten-action-title"), True, True, 0)
    close = shell._class(Gtk.Button(label="×"), "ten-rail-button")
    close.get_accessible().set_name("Close Action Center")
    close.connect("clicked", lambda _button: shell._hide_actions())
    header.pack_end(close, False, False, 0)
    root.pack_start(header, False, False, 0)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    notifications = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11),
                                  "ten-action-notifications")
    notifications.pack_start(shell._class(
        Gtk.Label(label="Notifications", xalign=0), "ten-section-heading"),
        False, False, 0)
    notifications.pack_start(shell._class(
        Gtk.Label(label="No RiceBowl notifications", xalign=0),
        "ten-notification-empty"), False, False, 0)
    note = shell._class(Gtk.Label(
        label="Other desktop notifications appear through the XFCE "
              "notification service.", xalign=0), "ten-muted")
    note.set_line_wrap(True)
    notifications.pack_start(note, False, False, 0)
    notify_command = ("xfce4-notifyd-config"
                      if shutil.which("xfce4-notifyd-config") else None)
    notification_settings = shell._class(
        Gtk.Button(label="Notification settings"), "aero-menu-app")
    notification_settings.set_halign(Gtk.Align.START)
    notification_settings.set_sensitive(notify_command is not None)
    notification_settings.get_accessible().set_name("Open notification settings")
    notification_settings.set_tooltip_text(
        "Open XFCE notification preferences" if notify_command else
        "XFCE notification preferences are not installed")
    if notify_command:
        notification_settings.connect(
            "clicked", lambda _button, cmd=notify_command: shell._open_tool(cmd))
    notifications.pack_start(notification_settings, False, False, 0)
    notifications.pack_start(Gtk.Box(), True, True, 0)
    scroll.add(notifications)
    root.pack_start(scroll, True, True, 0)

    bottom = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                          "ten-action-bottom")
    bottom.pack_start(shell._class(
        Gtk.Label(label="Quick actions", xalign=0), "ten-section-heading"),
        False, False, 0)
    grid = Gtk.Grid(row_spacing=5, column_spacing=5)
    grid.set_column_homogeneous(True)
    for index, (name, icon_name, command) in enumerate(QUICK_ACTIONS):
        button = shell._class(Gtk.Button(), "ten-quick")
        tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        icon = shell._icon(icon_name, Gtk.IconSize.LARGE_TOOLBAR)
        icon.set_halign(Gtk.Align.CENTER)
        tile.pack_start(icon, False, False, 0)
        caption = shell._class(Gtk.Label(label=name), "ten-quick-label")
        caption.set_justify(Gtk.Justification.CENTER)
        caption.set_line_wrap(True)
        tile.pack_start(caption, False, False, 0)
        button.add(tile)
        button.get_accessible().set_name("Open " + name)
        available = shutil.which(command) is not None
        button.set_tooltip_text("Open " + name if available else
                                command + " is not installed")
        button.set_sensitive(available)
        button.connect("clicked", lambda _button, cmd=command: shell._open_tool(cmd))
        grid.attach(button, index % 4, index // 4, 1, 1)
        if name == "Network":
            shell.ten_network_action = button
    bottom.pack_start(grid, False, False, 0)

    hardware = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: reading…", xalign=0), "ten-action-detail")
    shell.control_battery_label = shell._class(
        Gtk.Label(label="Battery: reading…", xalign=0), "ten-action-detail")
    shell.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
    shell.control_battery_level.set_no_show_all(True)
    hardware.pack_start(shell.control_network_label, False, False, 0)
    hardware.pack_start(shell.control_battery_label, False, False, 0)
    hardware.pack_start(shell.control_battery_level, False, False, 0)
    shell.volume_status_label = shell._class(
        Gtk.Label(label="Volume: reading…", xalign=0), "ten-action-detail")
    hardware.pack_start(shell.volume_status_label, False, False, 4)
    volume_row = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                              "ten-volume")
    volume_row.pack_start(shell._icon("audio-volume-high", Gtk.IconSize.MENU),
                          False, False, 0)
    shell.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    shell.volume_scale.set_draw_value(False)
    shell.volume_scale.set_hexpand(True)
    shell.volume_scale.set_sensitive(False)
    shell.volume_scale.get_accessible().set_name("System output volume")
    shell.volume_scale.set_tooltip_text("Set and verify the actual output volume")
    shell.volume_scale.connect("value-changed", shell._queue_volume_change)
    volume_row.pack_start(shell.volume_scale, True, True, 0)
    hardware.pack_start(volume_row, False, False, 0)
    shell.mute_button = shell._class(Gtk.ToggleButton(label="Mute output"), "ten-mute")
    shell.mute_button.set_sensitive(False)
    shell.mute_button.get_accessible().set_name("Mute or unmute system output")
    shell.mute_button.connect("clicked", shell._toggle_output_mute)
    hardware.pack_start(shell.mute_button, False, False, 0)
    bottom.pack_start(hardware, False, False, 1)
    shell.status_summary = shell._class(
        Gtk.Label(label="Reading hardware status…", xalign=0), "ten-muted")
    shell.status_summary.set_line_wrap(True)
    bottom.pack_start(shell.status_summary, False, False, 0)
    root.pack_start(bottom, False, False, 0)
    actions.add(root)
    actions.connect("focus-out-event",
                    lambda *_args: shell._schedule_popup_hide("control"))
    actions.connect("key-press-event",
                    lambda _widget, event: shell._action_key(event))
    return actions
