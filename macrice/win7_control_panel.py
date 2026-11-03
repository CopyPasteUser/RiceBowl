"""Windows 7-inspired Control Panel over installed Linux settings tools.

The historical category taxonomy is visual/navigation guidance; every leaf
launches a real installed XFCE/Linux program. No Windows APIs are emulated.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class Task:
    name: str
    commands: tuple[str, ...]


@dataclass(frozen=True)
class Category:
    name: str
    icon: str
    tasks: tuple[Task, ...]


CATEGORIES = (
    Category("System and Security", "ricehub-cp-system", (
        Task("System settings", ("xfce4-settings-manager",)),
        Task("Power options", ("xfce4-power-manager-settings",)),
        Task("Session and startup", ("xfce4-session-settings",)),
    )),
    Category("Network and Internet", "ricehub-cp-network", (
        Task("View network connections", ("nm-connection-editor",)),
        Task("Network settings", ("nm-connection-editor", "nm-applet")),
    )),
    Category("Hardware and Sound", "ricehub-cp-hardware", (
        Task("Sound", ("pavucontrol", "xfce4-mixer")),
        Task("Devices and printers", ("system-config-printer",)),
        Task("Display", ("xfce4-display-settings",)),
    )),
    Category("Programs", "ricehub-cp-programs", (
        Task("Browse installed applications", ("xfce4-appfinder",)),
        Task("Preferred applications", ("exo-preferred-applications",)),
    )),
    Category("User Accounts and Family Safety", "ricehub-cp-accounts", (
        Task("User accounts", ("users-admin", "mate-user-admin")),
        Task("Session and startup", ("xfce4-session-settings",)),
    )),
    Category("Appearance and Personalization", "ricehub-cp-appearance", (
        Task("Change the theme", ("xfce4-appearance-settings",)),
        Task("Desktop background", ("xfdesktop-settings",)),
        Task("Window borders", ("xfwm4-settings",)),
    )),
    Category("Clock, Language, and Region", "ricehub-cp-clock", (
        Task("Date and time", ("time-admin", "gnome-control-center")),
        Task("Keyboard and language", ("xfce4-keyboard-settings",)),
    )),
    Category("Ease of Access", "ricehub-cp-ease", (
        Task("Accessibility settings", ("xfce4-accessibility-settings",)),
        Task("Mouse and touchpad", ("xfce4-mouse-settings",)),
    )),
)


def installed_command(task: Task, which=shutil.which) -> str | None:
    """Resolve only executables from a fixed, maintained catalog."""
    return next((command for command in task.commands if which(command)), None)


def matching_categories(query: str) -> tuple[Category, ...]:
    needle = query.casefold().strip()
    return tuple(category for category in CATEGORIES if not needle or
                 needle in category.name.casefold() or
                 any(needle in task.name.casefold() for task in category.tasks))


def build(shell, Gtk, Gdk):
    """Build an actual navigable category window, not a quick-toggle popup."""
    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("Control Panel — RiceBowl Linux")
    window.set_icon_name("preferences-system")
    window.set_resizable(True)
    window.set_default_size(810, 565)
    window.set_skip_taskbar_hint(False)
    window.set_skip_pager_hint(False)

    def close_window(_window, _event):
        # The taskbar/keyboard shortcut owns this reusable application window.
        shell._hide_actions()
        return True

    window.connect("delete-event", close_window)

    root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                        "win7-cp-root")
    toolbar = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                           "win7-cp-toolbar")
    back = shell._class(Gtk.Button(), "win7-cp-back")
    back.add(shell._icon("go-previous", Gtk.IconSize.BUTTON))
    back.get_accessible().set_name("Back to Control Panel home")
    back.set_sensitive(False)
    toolbar.pack_start(back, False, False, 0)
    breadcrumb = shell._class(Gtk.Button(label="Control Panel"), "win7-cp-breadcrumb")
    breadcrumb.get_accessible().set_name("Return to Control Panel home")
    toolbar.pack_start(breadcrumb, True, True, 0)
    search = shell._class(Gtk.SearchEntry(), "win7-control-search")
    search.set_placeholder_text("Search Control Panel")
    search.get_accessible().set_name("Search Control Panel")
    search.set_size_request(215, -1)
    toolbar.pack_end(search, False, False, 0)
    root.pack_start(toolbar, False, False, 0)

    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_min_content_height(250)
    content = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14),
                           "win7-cp-content")
    heading = shell._class(Gtk.Label(label="Adjust your computer's settings", xalign=0),
                           "win7-cp-heading")
    content.pack_start(heading, False, False, 0)
    view_by = shell._class(Gtk.Label(label="View by: Category", xalign=1), "win7-cp-viewby")
    content.pack_start(view_by, False, False, 0)
    categories_grid = Gtk.Grid(column_spacing=22, row_spacing=18)
    categories_grid.set_column_homogeneous(True)
    content.pack_start(categories_grid, False, False, 2)
    empty = shell._class(Gtk.Label(label="No matching settings", xalign=0),
                         "win7-cp-empty")
    empty.set_no_show_all(True)
    content.pack_start(empty, False, False, 0)
    details = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11),
                           "win7-cp-details")
    details.set_no_show_all(True)
    content.pack_start(details, False, False, 0)
    scroll.add(content)
    root.pack_start(scroll, True, True, 0)

    def task_link(task):
        command = installed_command(task)
        button = shell._class(Gtk.Button(label=task.name), "win7-cp-link")
        button.set_halign(Gtk.Align.START)
        button.set_sensitive(command is not None)
        button.get_accessible().set_name("Open " + task.name)
        button.set_tooltip_text("Open " + task.name if command else
                                "Not installed: " + " / ".join(task.commands))
        if command:
            button.connect("clicked", lambda _button, selected=command: shell._open_tool(selected))
        return button

    category_rows = []

    def show_home(*_args):
        for widget in details.get_children():
            details.remove(widget)
        details.hide()
        empty.hide()
        categories_grid.show()
        view_by.show()
        back.set_sensitive(False)
        breadcrumb.set_label("Control Panel")
        heading.set_text("Adjust your computer's settings")
        scroll.get_vadjustment().set_value(0)

    def show_category(category):
        categories_grid.hide()
        view_by.hide()
        empty.hide()
        for widget in details.get_children():
            details.remove(widget)
        back.set_sensitive(True)
        breadcrumb.set_label("Control Panel  ›  " + category.name)
        heading.set_text(category.name)
        for task in category.tasks:
            details.pack_start(task_link(task), False, False, 0)
        details.show_all()
        scroll.get_vadjustment().set_value(0)

    for index, category in enumerate(CATEGORIES):
        row = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=11),
                           "win7-cp-category")
        image = shell._icon(category.icon, Gtk.IconSize.DIALOG)
        image.set_pixel_size(35)
        row.pack_start(image, False, False, 0)
        links = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title = shell._class(Gtk.Button(label=category.name), "win7-cp-category-title")
        title.set_halign(Gtk.Align.START)
        title.get_accessible().set_name("Show " + category.name + " settings")
        title.connect("clicked", lambda _button, chosen=category: show_category(chosen))
        links.pack_start(title, False, False, 0)
        for task in category.tasks[:2]:
            links.pack_start(task_link(task), False, False, 0)
        row.pack_start(links, True, True, 0)
        categories_grid.attach(row, index % 2, index // 2, 1, 1)
        category_rows.append((category, row))

    def on_search(entry):
        show_home()
        matching = matching_categories(entry.get_text())
        for category, row in category_rows:
            row.set_visible(category in matching)
        empty.set_visible(not matching)

    search.connect("search-changed", on_search)
    back.connect("clicked", show_home)
    breadcrumb.connect("clicked", show_home)

    # Native status controls stay available but live in a clearly identified
    # Linux hardware drawer; they are not fabricated Windows control items.
    expander = Gtk.Expander(label="Linux device status and volume")
    expander.get_style_context().add_class("win7-cp-status-expander")
    hardware = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6),
                            "win7-cp-hardware")
    shell.status_summary = shell._class(
        Gtk.Label(label="Reading hardware status…", xalign=0), "rice-status-summary")
    hardware.pack_start(shell.status_summary, False, False, 0)
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: reading…", xalign=0), "rice-control-detail")
    hardware.pack_start(shell.control_network_label, False, False, 0)
    shell.control_battery_label = shell._class(
        Gtk.Label(label="Battery: reading…", xalign=0), "rice-control-detail")
    hardware.pack_start(shell.control_battery_label, False, False, 0)
    shell.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
    shell.control_battery_level.set_value(0)
    shell.control_battery_level.set_no_show_all(True)
    hardware.pack_start(shell.control_battery_level, False, False, 0)
    shell.volume_status_label = shell._class(
        Gtk.Label(label="Volume: reading…", xalign=0), "rice-control-detail")
    hardware.pack_start(shell.volume_status_label, False, False, 0)
    shell.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    shell.volume_scale.set_draw_value(False)
    shell.volume_scale.set_sensitive(False)
    shell.volume_scale.get_accessible().set_name("System output volume")
    shell.volume_scale.connect("value-changed", shell._queue_volume_change)
    hardware.pack_start(shell.volume_scale, False, False, 0)
    shell.mute_button = Gtk.ToggleButton(label="Mute output")
    shell.mute_button.set_sensitive(False)
    shell.mute_button.get_accessible().set_name("Mute or unmute output")
    shell.mute_button.connect("clicked", shell._toggle_output_mute)
    hardware.pack_start(shell.mute_button, False, False, 0)
    expander.add(hardware)
    root.pack_end(expander, False, False, 0)

    window.add(root)
    def on_key_press(_widget, event):
        if event.keyval == Gdk.KEY_Left and event.state & Gdk.ModifierType.MOD1_MASK:
            show_home()  # Explorer-style Alt+Left navigation
            return True
        return shell._action_key(event)

    window.connect("key-press-event", on_key_press)
    shell.win7_panel_search = search
    shell.win7_panel_back = back
    shell.win7_panel_rows = category_rows
    shell.win7_panel_show_category = show_category
    shell.win7_panel_show_home = show_home
    show_home()
    return window
