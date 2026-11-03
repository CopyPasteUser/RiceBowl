"""Windows XP-inspired category Control Panel with real XFCE actions.

The panel intentionally uses installed Linux utilities instead of pretending
that an unavailable Windows applet exists. No settings are changed on open.
"""

from __future__ import annotations

import shutil


LUNA_CATEGORIES = (
    ("Appearance and Themes", "preferences-desktop-theme",
     ("xfce4-appearance-settings",), "Colors, fonts and window appearance"),
    ("Network and Internet Connections", "network-workgroup",
     ("nm-connection-editor", "nm-applet"), "Configure network connections"),
    ("Add or Remove Programs", "system-software-install",
     ("mintinstall", "gnome-software", "synaptic"), "Install or remove applications"),
    ("Sounds, Speech, and Audio Devices", "audio-card",
     ("pavucontrol", "xfce4-mixer"), "Playback and input devices"),
    ("Performance and Maintenance", "utilities-system-monitor",
     ("xfce4-taskmanager", "gnome-system-monitor"), "Inspect running processes"),
    ("Printers and Other Hardware", "printer",
     ("system-config-printer",), "Set up printers"),
    ("User Accounts", "system-users",
     ("users-admin", "gnome-control-center"), "Manage local accounts"),
    ("Date, Time, Language, and Regional Options", "preferences-system-time",
     ("time-admin", "xfce4-settings-manager"), "Open regional and time settings"),
)


def available_program(candidates, which=shutil.which):
    """Select the first *available* real tool; never fake a working applet."""
    return next((command for command in candidates if which(command)), None)


def build(shell, Gtk, Gdk):
    """Create a lightweight 2001-style category view; return its GTK window."""
    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("Control Panel")
    window.set_decorated(False)
    window.set_resizable(True)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    window.set_transient_for(shell.bar)
    window.set_keep_above(True)
    window.set_default_size(746, 536)

    frame = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                         "luna-control-window")
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.add(frame)
    window.add(scroll)

    caption = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8),
                           "luna-control-caption")
    caption.pack_start(shell._icon("preferences-system", Gtk.IconSize.MENU),
                       False, False, 3)
    caption.pack_start(Gtk.Label(label="Control Panel", xalign=0), True, True, 0)
    close = shell._class(Gtk.Button(label="×"), "luna-control-close")
    close.get_accessible().set_name("Close Control Panel")
    close.connect("clicked", lambda _button: shell._hide_actions())
    caption.pack_end(close, False, False, 0)

    def move_window(_widget, event):
        if event.button != 1:
            return False
        window.begin_move_drag(1, int(event.x_root), int(event.y_root), event.time)
        return True

    caption.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    caption.connect("button-press-event", move_window)
    frame.pack_start(caption, False, False, 0)

    body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    frame.pack_start(body, True, True, 0)
    sidebar = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8),
                           "luna-control-sidebar")
    sidebar.set_size_request(232, -1)
    body.pack_start(sidebar, False, False, 0)
    main = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10),
                        "luna-control-main")
    body.pack_start(main, True, True, 0)

    heading = shell._class(Gtk.Label(label="Pick a category", xalign=0),
                           "luna-control-heading")
    main.pack_start(heading, False, False, 0)
    main.pack_start(Gtk.Label(label="Choose a task to configure your computer", xalign=0),
                    False, False, 0)

    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.NONE)
    category_grid = Gtk.Grid(row_spacing=10, column_spacing=10)
    classic_grid = Gtk.Grid(row_spacing=8, column_spacing=8)
    stack.add_named(category_grid, "categories")
    stack.add_named(classic_grid, "classic")
    main.pack_start(stack, True, True, 2)

    def category_button(name, icon, commands, explanation, *, compact=False):
        program = available_program(commands)
        button = shell._class(Gtk.Button(),
                              "luna-control-applet" if compact else "luna-control-category")
        button.set_relief(Gtk.ReliefStyle.NONE)
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        line.pack_start(shell._icon(icon, Gtk.IconSize.LARGE_TOOLBAR if compact else
                                    Gtk.IconSize.DIALOG), False, False, 0)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = shell._class(Gtk.Label(label=name, xalign=0), "luna-control-link")
        title.set_line_wrap(True)
        title.set_max_width_chars(23 if not compact else 19)
        labels.pack_start(title, False, False, 0)
        if not compact:
            subtitle = shell._class(Gtk.Label(label=explanation, xalign=0),
                                    "luna-control-explanation")
            subtitle.set_line_wrap(True)
            subtitle.set_max_width_chars(24)
            labels.pack_start(subtitle, False, False, 0)
        line.pack_start(labels, True, True, 0)
        button.add(line)
        button.set_sensitive(program is not None)
        button.set_tooltip_text("Open " + name if program else
                                "Not installed: " + " or ".join(commands))
        button.get_accessible().set_name("Open " + name)
        if program:
            button.connect("clicked", lambda _button, executable=program:
                           shell._open_tool(executable))
        return button

    for index, (name, icon, commands, explanation) in enumerate(LUNA_CATEGORIES):
        category_grid.attach(category_button(name, icon, commands, explanation),
                             index % 2, index // 2, 1, 1)
        classic_grid.attach(category_button(name, icon, commands, explanation, compact=True),
                            index % 2, index // 2, 1, 1)

    nav_group = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4),
                             "luna-control-side-group")
    sidebar.pack_start(nav_group, False, False, 0)
    nav_group.pack_start(shell._class(Gtk.Label(label="Control Panel", xalign=0),
                                       "luna-control-side-heading"), False, False, 0)
    toggle = shell._class(Gtk.Button(label="Switch to Classic View"), "luna-control-nav")
    toggle.get_accessible().set_name("Switch Control Panel view")

    def switch_view(_button):
        classic = stack.get_visible_child_name() != "classic"
        stack.set_visible_child_name("classic" if classic else "categories")
        toggle.set_label("Switch to Category View" if classic else "Switch to Classic View")
        heading.set_text("Classic View" if classic else "Pick a category")

    toggle.connect("clicked", switch_view)
    nav_group.pack_start(toggle, False, False, 0)
    shell.luna_control_stack = stack
    shell.luna_control_switch = toggle

    hardware = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5),
                            "luna-control-side-group")
    sidebar.pack_start(hardware, False, False, 0)
    hardware.pack_start(shell._class(Gtk.Label(label="System status", xalign=0),
                                     "luna-control-side-heading"), False, False, 0)
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: reading…", xalign=0), "rice-control-detail")
    shell.control_network_label.set_line_wrap(True)
    hardware.pack_start(shell.control_network_label, False, False, 0)
    shell.control_battery_label = shell._class(
        Gtk.Label(label="Battery: reading…", xalign=0), "rice-control-detail")
    shell.control_battery_label.set_line_wrap(True)
    hardware.pack_start(shell.control_battery_label, False, False, 0)
    shell.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
    shell.control_battery_level.set_no_show_all(True)
    hardware.pack_start(shell.control_battery_level, False, False, 0)
    shell.volume_status_label = shell._class(
        Gtk.Label(label="Volume: reading…", xalign=0), "rice-control-detail")
    shell.volume_status_label.set_line_wrap(True)
    hardware.pack_start(shell.volume_status_label, False, False, 0)
    shell.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    shell.volume_scale.set_draw_value(False)
    shell.volume_scale.set_sensitive(False)
    shell.volume_scale.get_accessible().set_name("System output volume")
    shell.volume_scale.connect("value-changed", shell._queue_volume_change)
    hardware.pack_start(shell.volume_scale, False, False, 0)
    shell.mute_button = shell._class(Gtk.ToggleButton(label="Mute output"), "rice-mute")
    shell.mute_button.set_sensitive(False)
    shell.mute_button.get_accessible().set_name("Mute or unmute output")
    shell.mute_button.connect("clicked", shell._toggle_output_mute)
    hardware.pack_start(shell.mute_button, False, False, 0)
    shell.status_summary = shell._class(
        Gtk.Label(label="Reading hardware status…", xalign=0), "luna-control-summary")
    shell.status_summary.set_line_wrap(True)
    sidebar.pack_end(shell.status_summary, False, False, 0)

    window.connect("focus-out-event", lambda *_args: shell._schedule_popup_hide("control"))
    window.connect("key-press-event", lambda _widget, event: shell._action_key(event))
    return window
