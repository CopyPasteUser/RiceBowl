"""ChromeOS-inspired Quick Settings with genuine Linux navigation and status.

The XFCE notification daemon continues to own external notifications. Network,
Bluetooth, brightness and other privileged controls are *not* represented by
fake on/off buttons. Every tile navigates to an actual settings detail page.
"""

from __future__ import annotations

from datetime import date
import shutil

from .chrome_shell import apply_rounded_window_shape
from .chrome_settings import ACTIONS, available_tool, status_text
from .frutiger_native_controls import NativeAquaControls


QUICK_ACTIONS = (
    ("Network", "network-wireless", "Connections", "Connections & VPN"),
    ("Bluetooth", "bluetooth", "Bluetooth devices", "Nearby devices"),
    ("Display", "video-display", "Displays", "Displays & scaling"),
    ("Notifications", "preferences-system-notifications", "Notifications", "Notification preferences"),
    ("Power", "battery", "Power", "Battery & sleep"),
    ("Keyboard", "input-keyboard", "Keyboard", "Keyboard & shortcuts"),
)


def calendar_today(today: date | None = None) -> tuple[int, int, int]:
    """GTK Calendar uses zero-based months; the local system date is authoritative."""
    value = today or date.today()
    return value.year, value.month - 1, value.day


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
    back = shell._class(Gtk.Button(label="‹"), "chrome-quick-back")
    back.set_tooltip_text("Back to Quick Settings")
    back.get_accessible().set_name("Back to Quick Settings")
    back.set_no_show_all(True)
    header.pack_start(back, False, False, 0)
    title = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    heading = shell._class(Gtk.Label(label="Quick Settings", xalign=0),
                           "chrome-quick-title")
    title.pack_start(heading, False, False, 0)
    shell.chrome_quick_clock = shell._class(
        Gtk.Label(label="", xalign=0), "chrome-quick-date")
    date_button = shell._class(Gtk.Button(), "chrome-quick-clock-button")
    date_button.add(shell.chrome_quick_clock)
    date_button.set_tooltip_text("Open the local calendar")
    date_button.get_accessible().set_name("Open the local calendar")
    date_button.connect("clicked", lambda _button: show_page("Calendar"))
    title.pack_start(date_button, False, False, 0)
    header.pack_start(title, True, True, 0)
    for name, icon, command in (
        ("Settings", "preferences-system", None),
        ("Sign out", "system-shutdown", "xfce4-session-logout"),
    ):
        button = shell._class(Gtk.Button(), "chrome-launcher-settings")
        button.set_image(shell._icon(icon, Gtk.IconSize.MENU))
        button.set_tooltip_text(
            "Open " + name if command is None or shutil.which(command) else
            command + " is not installed")
        button.get_accessible().set_name("Open " + name)
        button.set_sensitive(command is None or shutil.which(command) is not None)
        button.connect("clicked", lambda _button, cmd=command:
                       shell._open_chrome_settings() if cmd is None else shell._open_tool(cmd))
        header.pack_end(button, False, False, 0)
    root.pack_start(header, False, False, 0)
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.NONE)
    overview = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

    section = shell._class(Gtk.Label(label="Connectivity & device", xalign=0),
                           "chrome-section-caption")
    overview.pack_start(section, False, False, 0)
    grid = Gtk.Grid(row_spacing=7, column_spacing=7)
    grid.set_column_homogeneous(True)
    for index, (name, icon_name, action_name, explanation) in enumerate(QUICK_ACTIONS):
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
        # Every chevron navigates to a detail page, not a fake state toggle.
        arrow = shell._class(Gtk.Label(label="›"), "chrome-quick-chevron")
        content.pack_end(arrow, False, False, 0)
        button.add(content)
        button.get_accessible().set_name("Open " + name + " settings")
        button.set_tooltip_text("Show " + name + " details")
        button.connect("clicked", lambda _button, page=name: show_page(page))
        grid.attach(button, index % 2, index // 2, 1, 1)
        if name == "Network":
            shell.chrome_network_detail = detail
    overview.pack_start(grid, False, False, 0)

    overview.pack_start(shell._class(
        Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), "chrome-divider"),
        False, False, 0)
    overview.pack_start(shell._class(
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
    overview.pack_start(audio, False, False, 0)

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
    overview.pack_start(hardware, False, False, 0)
    stack.add_named(overview, "overview")

    shell.chrome_quick_status_labels = []
    native_panels = {}
    for name, _icon_name, action_name, explanation in QUICK_ACTIONS:
        action = next(item for item in ACTIONS if item.name == action_name)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.pack_start(shell._class(Gtk.Label(label=explanation, xalign=0),
                                     "chrome-section-caption"), False, False, 0)
        status = shell._class(Gtk.Label(xalign=0), "chrome-quick-page-status")
        status.set_line_wrap(True)
        status.set_text(status_text(action, shell._last_status) if action.status else
                        "Uses installed Linux system settings")
        page.pack_start(status, False, False, 0)
        if action.status:
            shell.chrome_quick_status_labels.append((action, status))
        description = shell._class(Gtk.Label(label=action.description, xalign=0),
                                   "chrome-quick-page-description")
        description.set_line_wrap(True)
        page.pack_start(description, False, False, 0)
        native_panels[name] = []
        controls = {"Network": ("wifi",), "Bluetooth": ("bluetooth",),
                    "Display": ("display",), "Power": ("battery", "power")}
        for kind in controls.get(name, ()):
            panel = NativeAquaControls(
                shell, Gtk, GLib, page,
                is_current=lambda page_name=name:
                    actions.get_visible() and stack.get_visible_child_name() == page_name,
                style_prefix="chrome")
            getattr(panel, kind)()
            native_panels[name].append(panel)
        open_settings = shell._class(Gtk.Button(label="View in Settings  ›"),
                                     "chrome-quick-page-action")
        open_settings.get_accessible().set_name("Open " + name + " in Settings")
        open_settings.connect("clicked", lambda _button, item=action:
                              shell._open_chrome_settings(action=item))
        page.pack_start(open_settings, False, False, 0)
        native = shell._class(Gtk.Button(label="Open Linux configuration utility"),
                              "chrome-quick-page-action")
        tool = available_tool(action)
        native.set_sensitive(tool is not None)
        native.set_tooltip_text("Installed system configuration" if tool else
                                "Requires " + " or ".join(action.tools))
        if tool is not None:
            native.connect("clicked", lambda _button, cmd=tool: shell._open_tool(cmd))
        page.pack_start(native, False, False, 0)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(page)
        stack.add_named(scroller, name)

    calendar_page = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12),
                                 "chrome-quick-calendar-page")
    calendar_page.pack_start(shell._class(
        Gtk.Label(label="Local calendar", xalign=0), "chrome-section-caption"),
        False, False, 0)
    calendar = shell._class(Gtk.Calendar(), "chrome-quick-calendar")
    calendar.get_accessible().set_name("Local monthly calendar")
    calendar_page.pack_start(calendar, False, False, 0)
    calendar_note = shell._class(
        Gtk.Label(label="This shows your local dates. Online events are not connected.",
                  xalign=0), "chrome-quick-page-description")
    calendar_note.set_line_wrap(True)
    calendar_page.pack_start(calendar_note, False, False, 0)

    def reset_calendar():
        year, month, day = calendar_today()
        calendar.select_month(month, year)
        calendar.select_day(day)

    today_button = shell._class(Gtk.Button(label="Today"), "chrome-quick-page-action")
    today_button.get_accessible().set_name("Return calendar to today")
    today_button.connect("clicked", lambda _button: reset_calendar())
    calendar_page.pack_start(today_button, False, False, 0)
    stack.add_named(calendar_page, "Calendar")
    native_panels["Calendar"] = []
    shell.chrome_quick_calendar = calendar

    def show_home():
        heading.set_text("Quick Settings")
        stack.set_visible_child_name("overview")
        back.hide()

    def show_page(name):
        heading.set_text(name)
        stack.set_visible_child_name(name)
        back.show()
        if name == "Calendar":
            reset_calendar()
        for panel in native_panels[name]:
            panel.refresh()

    back.connect("clicked", lambda *_: show_home())
    shell.chrome_quick_show_home = show_home
    shell.chrome_quick_show_page = show_page
    shell.chrome_quick_stack = stack
    root.pack_start(stack, True, True, 0)
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
