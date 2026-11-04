"""Windows 98 SE all-icons Control Panel backed by real Linux utilities.

Only the Win98 rice imports this module. The native XFWM window can be moved,
resized, minimized and closed normally; no second settings daemon is required.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class Applet:
    name: str
    icon: str
    commands: tuple[str, ...]
    description: str


APPLETS: tuple[Applet, ...] = (
    Applet("Accessibility Options", "preferences-desktop-accessibility", ("xfce4-accessibility-settings",),
           "Adjust keyboard, pointer and accessibility options."),
    Applet("Add/Remove Programs", "system-software-install", ("mintinstall", "gnome-software", "synaptic"),
           "Open your installed software manager. Package removal is handled by Linux."),
    Applet("Date/Time", "preferences-system-time", ("time-admin", "gnome-control-center"),
           "Open your system's date and time settings."),
    Applet("Display", "video-display", ("xfdesktop-settings", "xfce4-display-settings"),
           "Background, appearance and display options."),
    Applet("Fonts", "preferences-desktop-font", ("xfce4-appearance-settings",),
           "Configure desktop fonts and rendering."),
    Applet("Internet Options", "applications-internet", ("exo-preferred-applications",),
           "Choose your preferred web browser and other default applications."),
    Applet("Keyboard", "input-keyboard", ("xfce4-keyboard-settings",),
           "Configure repeat speed, layouts and keyboard shortcuts."),
    Applet("Mouse", "input-mouse", ("xfce4-mouse-settings",),
           "Configure pointer, click and scrolling preferences."),
    Applet("Multimedia", "audio-card", ("pavucontrol", "xfce4-mixer"),
           "Manage the real audio devices and their output levels."),
    Applet("Network", "network-workgroup", ("nm-connection-editor",),
           "Manage actual NetworkManager connections."),
    Applet("Power Management", "battery", ("xfce4-power-manager-settings",),
           "Configure suspend, battery and display power behavior."),
    Applet("Printers", "printer", ("system-config-printer",),
           "Open printer queues and installed printer management."),
    Applet("Regional Settings", "preferences-desktop-locale", ("xfce4-settings-manager",),
           "Open Linux desktop preferences; regional support depends on your distribution."),
    Applet("Sounds", "audio-volume-high", ("pavucontrol", "xfce4-mixer"),
           "Adjust system output, input devices and volume."),
    Applet("System", "computer", (),
           "Read-only real Linux system, devices and performance information."),
    Applet("Taskbar & Start Menu", "preferences-desktop", (),
           "Configure RiceBowl Windows 98 Quick Launch and taskbar clock."),
)


def executable(applet: Applet, which=shutil.which) -> str | None:
    """Do not enable settings that have no installed executable."""
    return next((name for name in applet.commands if which(name)), None)


def visible_applets(query: str = "") -> tuple[Applet, ...]:
    needle = query.strip().casefold()
    return tuple(a for a in APPLETS if not needle or needle in a.name.casefold()
                 or needle in a.description.casefold())


def build(shell, Gtk, Gdk):
    """Construct a real, standalone GTK window with the classic icon view."""
    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("Control Panel")
    window.set_icon_name("preferences-system")
    window.set_default_size(690, 475)
    window.set_resizable(True)
    window.set_skip_taskbar_hint(False)
    window.set_skip_pager_hint(False)
    window.connect("delete-event", lambda *_args: (shell._hide_actions(), True)[1])

    root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                        "classic98-control")
    menu_bar = Gtk.MenuBar()
    file_menu = Gtk.Menu()
    file_item = Gtk.MenuItem(label="File")
    file_item.set_submenu(file_menu)
    close_item = Gtk.MenuItem(label="Close")
    close_item.connect("activate", lambda *_args: shell._hide_actions())
    file_menu.append(close_item)
    menu_bar.append(file_item)
    view_menu = Gtk.Menu()
    view_item = Gtk.MenuItem(label="View")
    view_item.set_submenu(view_menu)
    for title in ("Large Icons", "Small Icons"):
        item = Gtk.MenuItem(label=title)
        item.connect("activate", lambda _item, large=title == "Large Icons": set_icon_size(large))
        view_menu.append(item)
    menu_bar.append(view_item)
    root.pack_start(menu_bar, False, False, 0)

    address = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6),
                           "classic98-cp-address")
    address.pack_start(Gtk.Label(label="Address: ", xalign=0), False, False, 0)
    address.pack_start(Gtk.Label(label="Control Panel", xalign=0), True, True, 0)
    root.pack_start(address, False, False, 0)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    flow = Gtk.FlowBox()
    flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
    flow.set_activate_on_single_click(False)
    flow.set_min_children_per_line(3)
    flow.set_max_children_per_line(7)
    flow.set_row_spacing(10)
    flow.set_column_spacing(6)
    flow.set_margin_start(12)
    flow.set_margin_end(12)
    flow.set_margin_top(10)
    flow.set_margin_bottom(10)
    flow.set_halign(Gtk.Align.FILL)
    scroll.add(flow)
    root.pack_start(scroll, True, True, 0)

    status = shell._class(Gtk.Label(xalign=0), "classic98-cp-status")
    root.pack_end(status, False, False, 0)
    images = []
    available = 0
    for applet in APPLETS:
        command = executable(applet)
        native = applet.name in ("Taskbar & Start Menu", "System")
        if command or native:
            available += 1
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        image = shell._icon(applet.icon, Gtk.IconSize.DIALOG)
        images.append(image)
        content.pack_start(image, False, False, 0)
        label = Gtk.Label(label=applet.name)
        label.set_line_wrap(True)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_max_width_chars(19)
        content.pack_start(label, False, False, 0)
        child = shell._class(Gtk.FlowBoxChild(), "classic98-cp-item")
        child.add(content)
        child.set_tooltip_text(applet.description if command or native else
                               "Unavailable: " + " / ".join(applet.commands))
        child.get_accessible().set_name(applet.name)
        child.set_sensitive(command is not None or native)
        child._rice_command = command
        child._rice_applet = applet.name
        flow.add(child)

    def launch(_flow, child):
        if child._rice_applet == "Taskbar & Start Menu":
            shell.classic98_open_taskbar_properties()
        elif child._rice_applet == "System":
            from .classic98_system import show_system
            show_system(shell, Gtk)
        elif child._rice_command:
            shell._open_tool(child._rice_command)

    flow.connect("child-activated", launch)

    def set_icon_size(large):
        for image in images:
            # Gtk.Image handles icon-name and cached pixbuf artwork alike.
            image.set_pixel_size(32 if large else 16)
        flow.set_min_children_per_line(3 if large else 5)

    status.set_text(f"{len(APPLETS)} objects  ·  {available} available on this Linux system")
    window.add(root)
    window.connect("key-press-event", lambda _widget, event: shell._action_key(event))
    return window
