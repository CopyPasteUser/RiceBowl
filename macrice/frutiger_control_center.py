"""Aqua World's settings hierarchy, native Linux controls and external tools."""

from __future__ import annotations

import shutil
import threading
import logging

from .frutiger_device_details import ProbeResult, probe
from .frutiger_native_controls import NATIVE_TASKS, build_native_controls


# id, label, icon, short explanation, (label, icon, utility candidates, purpose)
AQUA_CATEGORIES = (
    ("connections", "Connections", "network-wireless", "Wi-Fi, Ethernet and nearby devices", (
        ("Network connections", "network-wireless", ("nm-connection-editor",),
         "Manage real wired, wireless and VPN connections"),
        ("Bluetooth devices", "bluetooth", ("blueman-manager",),
         "Pair, connect and remove nearby devices"),
    )),
    ("sound", "Sound & media", "audio-volume-high", "Playback volume and devices", (
        ("Output volume & mute", "audio-volume-high", (),
         "Change the default sound output with verified Linux read-back"),
        ("Input & output devices", "audio-card", ("pavucontrol", "xfce4-mixer"),
         "Select an audio output and adjust microphone input with native controls"),
        ("Notification sounds", "preferences-desktop-notification", ("xfce4-notifyd-config",),
         "Configure the installed desktop notification service"),
    )),
    ("display", "Display & windows", "video-display", "Screens, wallpaper and window frames", (
        ("Display configuration", "video-display", ("xfce4-display-settings",),
         "Resolution, monitor arrangement and refresh rate"),
        ("Desktop & wallpaper", "preferences-desktop-wallpaper", ("xfdesktop-settings",),
         "Set background and desktop icon appearance"),
        ("Window decoration", "preferences-system-windows", ("xfwm4-settings",),
         "Adjust the real window-manager decorations"),
    )),
    ("personalize", "Personalize", "preferences-desktop-theme", "Make the desktop yours", (
        ("Themes & fonts", "preferences-desktop-theme", ("xfce4-appearance-settings",),
         "Choose native desktop theme, icons and fonts"),
        ("Desktop background", "preferences-desktop-wallpaper", ("xfdesktop-settings",),
         "Select a background supported by your desktop"),
        ("Session & startup", "preferences-system-session", ("xfce4-session-settings",),
         "Manage autostart and session settings"),
    )),
    ("power", "Power & battery", "battery", "Charging and power preferences", (
        ("Battery status", "battery", (),
         "Read current battery and AC state when available"),
        ("Power management", "preferences-system-power", ("xfce4-power-manager-settings",),
         "Set sleep, lid and battery behavior"),
        ("Log out or shut down", "system-shutdown", ("xfce4-session-logout",),
         "Open XFCE's confirmation dialog; never power off immediately"),
    )),
    ("devices", "Devices & input", "input-keyboard", "Mouse, keyboard and printers", (
        ("Mouse & touchpad", "input-mouse", ("xfce4-mouse-settings",),
         "Configure pointer and touchpad input"),
        ("Keyboard & shortcuts", "input-keyboard", ("xfce4-keyboard-settings",),
         "Configure keyboard layout and shortcuts"),
        ("Printers", "printer", ("system-config-printer",),
         "Manage printers if a printer manager is installed"),
    )),
    ("applications", "Applications", "system-software-install", "Installed apps and defaults", (
        ("Find applications", "system-search", ("xfce4-appfinder",),
         "Search and launch installed desktop applications"),
        ("Install & update software", "system-software-install", ("mintinstall", "gnome-software", "synaptic"),
         "Open an installed software manager"),
        ("Default applications", "preferences-desktop-default-applications", ("exo-preferred-applications",),
         "Select the default browser, mail and utilities"),
    )),
    ("system", "System & recovery", "computer", "System information and safety", (
        ("System information", "computer", ("xfce4-about",),
         "Read real operating-system and desktop details"),
        ("Task manager", "utilities-system-monitor", ("xfce4-taskmanager", "gnome-system-monitor"),
         "Inspect applications, CPU and memory"),
        ("Desktop settings", "preferences-system", ("xfce4-settings-manager",),
         "Access additional installed settings"),
    )),
    ("accessibility", "Accessibility", "preferences-desktop-accessibility", "Keyboard and reading comfort", (
        ("Accessibility settings", "preferences-desktop-accessibility", ("xfce4-accessibility-settings",),
         "Configure assistive keyboard and input settings"),
        ("Text & contrast", "preferences-desktop-theme", ("xfce4-appearance-settings",),
         "Adjust readable font size and native contrast"),
    )),
)

# These live read-only summaries supplement native verified controls.
DETAIL_PROBES = {
    ("connections", "Network connections"): "wifi",
    ("connections", "Bluetooth devices"): "bluetooth",
    ("sound", "Input & output devices"): "audio",
    ("display", "Display configuration"): "display",
    ("system", "System information"): "system",
}


def available_tool(candidates, which=shutil.which):
    """Return an installed allowlisted utility, or None for a read-only leaf."""
    from .aero_shell import LAUNCHABLE_TOOLS

    return next((candidate for candidate in candidates
                 if candidate in LAUNCHABLE_TOOLS and which(candidate)), None)


def search_aqua(query):
    """Search categories *and* leaf tasks without traversing the filesystem."""
    needle = query.casefold().strip()
    if not needle:
        return ()
    return tuple((category, task) for category in AQUA_CATEGORIES
                 for task in category[4]
                 if any(needle in value.casefold() for value in
                        (category[1], category[3], task[0], task[3])))


def build(shell, Gtk, Gdk):
    """Create the independently styled Aqua dashboard/category/task hierarchy."""
    from gi.repository import GLib

    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("Aqua World · Control Center")
    window.set_decorated(False)
    window.set_resizable(True)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
    window.set_transient_for(shell.bar)
    window.set_keep_above(True)
    window.set_default_size(492, 620)

    root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                        "aqua-control-root")
    root.get_style_context().add_class("aero-control-root")
    window.add(root)

    header = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9),
                          "aqua-control-hero")
    header.pack_start(shell._icon("preferences-system", Gtk.IconSize.LARGE_TOOLBAR),
                      False, False, 0)
    heading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
    heading_box.pack_start(shell._class(Gtk.Label(label="Aqua Control Center", xalign=0),
                                        "aero-menu-heading"), False, False, 0)
    heading_box.pack_start(shell._class(Gtk.Label(label="Your connected desktop", xalign=0),
                                        "aero-menu-sub"), False, False, 0)
    header.pack_start(heading_box, True, True, 0)
    close = shell._class(Gtk.Button(label="×"), "aqua-control-close")
    close.get_accessible().set_name("Close Aqua Control Center")
    close.connect("clicked", lambda _button: shell._hide_actions())
    header.pack_end(close, False, False, 0)
    root.pack_start(header, False, False, 0)

    nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    back = shell._class(Gtk.Button(label="‹ Back"), "aqua-control-back")
    nav.pack_start(back, False, False, 0)
    breadcrumb = shell._class(Gtk.Label(label="All settings", xalign=0),
                              "aqua-control-breadcrumb")
    from gi.repository import Pango

    breadcrumb.set_ellipsize(Pango.EllipsizeMode.END)
    nav.pack_start(breadcrumb, True, True, 0)
    root.pack_start(nav, False, False, 0)

    search = shell._class(Gtk.SearchEntry(), "aqua-control-search")
    search.set_placeholder_text("Find a setting or device")
    search.get_accessible().set_name("Search Aqua Control Center")
    root.pack_start(search, False, False, 0)

    scroller = Gtk.ScrolledWindow()
    scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroller.set_hexpand(True)
    scroller.set_vexpand(True)
    stack = Gtk.Stack()
    stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
    stack.set_transition_duration(130)
    stack.set_homogeneous(False)
    scroller.add(stack)
    root.pack_start(scroller, True, True, 0)

    home = shell._class(Gtk.Grid(row_spacing=8, column_spacing=8), "aqua-control-grid")
    home.set_column_homogeneous(True)
    category_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
    details = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                           "aqua-control-details")
    matches = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    for name, child in (("home", home), ("category", category_page),
                        ("detail", details), ("search", matches)):
        stack.add_named(child, name)

    current = ["home", None, None]
    request_serial = [0]

    def clear_box(box):
        for child in tuple(box.get_children()):
            box.remove(child)

    def navigate(page, category=None, task=None):
        request_serial[0] += 1
        current[:] = [page, category, task]
        stack.set_visible_child_name(page)
        back.set_sensitive(page != "home")
        label = "All settings"
        if category:
            label += "  ›  " + category[1]
        if task:
            label += "  ›  " + task[0]
        breadcrumb.set_text(label)
        scroller.get_vadjustment().set_value(0)

    def task_button(category, task):
        tool = available_tool(task[2])
        button = shell._class(Gtk.Button(), "aqua-control-task")
        line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        line.pack_start(shell._icon(task[1], Gtk.IconSize.LARGE_TOOLBAR),
                        False, False, 0)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        title = shell._class(Gtk.Label(label=task[0], xalign=0), "aqua-control-task-title")
        title.set_line_wrap(True)
        labels.pack_start(title, False, False, 0)
        note = shell._class(Gtk.Label(label=task[3], xalign=0), "aqua-control-task-note")
        note.set_line_wrap(True)
        labels.pack_start(note, False, False, 0)
        line.pack_start(labels, True, True, 0)
        line.pack_end(shell._class(Gtk.Label(label="›"), "aqua-control-chevron"),
                      False, False, 0)
        button.add(line)
        button.get_accessible().set_name("Show " + task[0] + " details")
        button.connect("clicked", lambda _button: show_detail(category, task))
        if (category[0], task[0]) in NATIVE_TASKS:
            button.set_tooltip_text("Open interactive Aqua controls for this device")
        else:
            button.set_tooltip_text("Review options" if tool or not task[2]
                                    else "Read more; this Linux utility is unavailable")
        return button

    for index, category in enumerate(AQUA_CATEGORIES):
        button = shell._class(Gtk.Button(), "aqua-control-category")
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        body.pack_start(shell._icon(category[2], Gtk.IconSize.DIALOG), False, False, 0)
        body.pack_start(shell._class(Gtk.Label(label=category[1]),
                                     "aqua-control-category-name"), False, False, 0)
        subtitle = shell._class(Gtk.Label(label=category[3]), "aqua-control-task-note")
        subtitle.set_line_wrap(True)
        subtitle.set_justify(Gtk.Justification.CENTER)
        body.pack_start(subtitle, False, False, 0)
        button.add(body)
        button.get_accessible().set_name("Open " + category[1])
        button.connect("clicked", lambda _button, selected=category: show_category(selected))
        home.attach(button, index % 2, index // 2, 1, 1)

    def show_category(category):
        if search.get_text():
            search.set_text("")
        clear_box(category_page)
        category_page.pack_start(shell._class(Gtk.Label(label=category[3], xalign=0),
                                               "aqua-control-intro"), False, False, 3)
        for task in category[4]:
            category_page.pack_start(task_button(category, task), False, False, 0)
        category_page.show_all()
        navigate("category", category)

    def show_detail(category, task):
        clear_box(details)
        shell.aqua_control_detail_status = None
        details.pack_start(shell._class(Gtk.Label(label=task[0], xalign=0),
                                        "aqua-control-detail-title"), False, False, 0)
        explanation = shell._class(Gtk.Label(label=task[3], xalign=0),
                                   "aqua-control-intro")
        explanation.set_line_wrap(True)
        details.pack_start(explanation, False, False, 0)
        tool = available_tool(task[2])
        shell.aqua_control_detail_kind = None
        if category[0] == "connections" or category[0] == "power":
            status = (shell.control_network_label if category[0] == "connections"
                      else shell.control_battery_label)
            clone = shell._class(Gtk.Label(label=status.get_text(), xalign=0),
                                 "aqua-control-live-label")
            shell.aqua_control_detail_status = clone
            shell.aqua_control_detail_kind = category[0]
            details.pack_start(clone, False, False, 3)
        if tool:
            launch = shell._class(Gtk.Button(label="Open " + task[0] + " settings"),
                                  "aqua-control-launch")
            launch.get_accessible().set_name("Open installed " + tool)
            launch.connect("clicked", lambda _button, program=tool: shell._open_tool(program))
            details.pack_start(launch, False, False, 3)
            details.pack_start(shell._class(Gtk.Label(
                label="This opens an installed Linux settings utility. Changes there are real.",
                xalign=0), "aqua-control-task-note"), False, False, 0)
        elif task[2]:
            missing = shell._class(Gtk.Label(
                label="Unavailable: install " + " or ".join(task[2]) +
                      " to configure this feature.", xalign=0), "aqua-control-unavailable")
            missing.set_line_wrap(True)
            details.pack_start(missing, False, False, 5)

        kind = DETAIL_PROBES.get((category[0], task[0]))
        if kind:
            result_heading = shell._class(Gtk.Label(label="Checking live devices…", xalign=0),
                                           "aqua-control-live-label")
            result_heading.set_line_wrap(True)
            details.pack_start(result_heading, False, False, 4)
            result_body = shell._class(Gtk.Label(label="", xalign=0),
                                        "aqua-control-probe-result")
            result_body.set_line_wrap(True)
            result_body.set_selectable(True)
            details.pack_start(result_body, False, False, 0)
        navigate("detail", category, task)
        serial = request_serial[0]
        native = build_native_controls(shell, Gtk, GLib, details, category[0], task[0],
                                       is_current=lambda: serial == request_serial[0]
                                       and current[0] == "detail" and current[2] == task)
        if native is not None:
            # The functional controls are the primary action; installed XFCE
            # utilities and device-probe explanations remain below as fallbacks.
            details.reorder_child(native.surface, 2)
        details.show_all()
        if kind:
            def worker():
                try:
                    result = probe(kind)
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "Aqua device probe %s failed: %s", kind, type(exc).__name__)
                    result = ProbeResult("Device information", (),
                                         "This device could not be read; try again later")

                def apply():
                    if (serial != request_serial[0] or current[0] != "detail"
                            or current[2] != task):
                        return False
                    result_heading.set_text(result.title)
                    if result.error:
                        result_body.get_style_context().add_class("aqua-control-probe-error")
                        result_body.set_text(result.error)
                    else:
                        result_body.set_text("\n".join(result.lines))
                    return False

                GLib.idle_add(apply)

            threading.Thread(target=worker, daemon=True,
                             name="ricebowl-aqua-" + kind).start()

    def show_home():
        shell.aqua_control_detail_status = None
        if search.get_text():
            search.set_text("")
        navigate("home")

    def go_back(_button=None):
        if current[0] == "detail":
            show_category(current[1])
        elif current[0] in ("category", "search"):
            show_home()
    back.connect("clicked", go_back)

    def search_changed(entry):
        query = entry.get_text().strip()
        if not query:
            show_home()
            return
        clear_box(matches)
        found = search_aqua(query)
        for category, task in found:
            matches.pack_start(task_button(category, task), False, False, 0)
        if not found:
            matches.pack_start(shell._class(Gtk.Label(label="No matching settings", xalign=0),
                                            "aqua-control-intro"), False, False, 6)
        matches.show_all()
        navigate("search")
    search.connect("search-changed", search_changed)

    # Persistent read-only status plus verified live sound adjustments. The
    # central shell refreshes these labels and slider every 20 seconds and
    # immediately reads back the result of writes.
    status = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4),
                          "aqua-control-live")
    shell.control_network_label = shell._class(
        Gtk.Label(label="Network: checking…", xalign=0), "rice-control-detail")
    shell.control_battery_label = shell._class(
        Gtk.Label(label="Battery: checking…", xalign=0), "rice-control-detail")
    shell.control_battery_level = Gtk.LevelBar.new_for_interval(0, 100)
    shell.control_battery_level.set_no_show_all(True)
    shell.volume_status_label = shell._class(
        Gtk.Label(label="Volume: checking…", xalign=0), "rice-control-detail")
    for widget in (shell.control_network_label, shell.control_battery_label,
                   shell.control_battery_level, shell.volume_status_label):
        status.pack_start(widget, False, False, 0)
    shell.volume_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
    shell.volume_scale.set_draw_value(False)
    shell.volume_scale.set_sensitive(False)
    shell.volume_scale.get_accessible().set_name("Actual system output volume")
    shell.volume_scale.connect("value-changed", shell._queue_volume_change)
    status.pack_start(shell.volume_scale, False, False, 0)
    shell.mute_button = shell._class(Gtk.ToggleButton(label="Mute output"), "rice-mute")
    shell.mute_button.set_sensitive(False)
    shell.mute_button.get_accessible().set_name("Mute or unmute actual output")
    shell.mute_button.connect("clicked", shell._toggle_output_mute)
    status.pack_start(shell.mute_button, False, False, 0)
    root.pack_end(status, False, False, 0)

    window.connect("focus-out-event", lambda *_args: shell._schedule_popup_hide("control"))
    window.connect("key-press-event", lambda _widget, event: shell._action_key(event))
    shell.aqua_control_show_home = show_home
    def show_named_category(name):
        for category in AQUA_CATEGORIES:
            if category[0] == name:
                show_category(category)
                return
        show_home()

    def show_named_task(name, task_name):
        for category in AQUA_CATEGORIES:
            if category[0] == name:
                for task in category[4]:
                    if task[0] == task_name:
                        show_detail(category, task)
                        return
        show_named_category(name)

    shell.aqua_control_show_category = show_named_category
    shell.aqua_control_show_task = show_named_task
    show_home()
    return window
