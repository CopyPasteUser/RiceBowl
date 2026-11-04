"""ChromeOS-inspired Settings with genuine Linux destinations and deep navigation.

This is an app-owned GTK3 window, not a ChromeOS system service. A Settings
row only invokes a real allowlisted Linux utility when it is installed.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil

from .frutiger_native_controls import NativeAquaControls


@dataclass(frozen=True)
class SettingAction:
    section: str
    name: str
    description: str
    tools: tuple[str, ...]
    icon: str
    status: str = ""


SECTIONS = (
    ("Network", "network-wireless", "Wi-Fi, Ethernet and VPN"),
    ("Bluetooth", "bluetooth", "Pair and manage devices"),
    ("Device", "computer", "Displays, sound, input and power"),
    ("Personalization", "preferences-desktop-wallpaper", "Wallpaper and appearance"),
    ("Apps", "application-x-executable", "Installed apps and defaults"),
    ("Privacy", "preferences-system-privacy", "Notifications and accessibility"),
    ("About", "dialog-information", "System information and diagnostics"),
)

ACTIONS = (
    SettingAction("Network", "Connections", "Manage genuine Wi-Fi and wired Ethernet connections.",
                  ("nm-connection-editor",), "network-wireless", "network"),
    SettingAction("Network", "VPN", "Review VPN connection profiles and gateways.",
                  ("nm-connection-editor",), "network-vpn"),
    SettingAction("Bluetooth", "Bluetooth devices", "Open the installed Bluetooth device manager.",
                  ("blueman-manager",), "bluetooth"),
    SettingAction("Device", "Sound", "Choose output/input devices and mixer levels.",
                  ("pavucontrol", "xfce4-mixer"), "audio-card", "sound"),
    SettingAction("Device", "Displays", "Configure resolution, external monitors and scaling.",
                  ("xfce4-display-settings",), "video-display"),
    SettingAction("Device", "Mouse and touchpad", "Adjust pointing and touchpad input.",
                  ("xfce4-mouse-settings",), "input-mouse"),
    SettingAction("Device", "Keyboard", "Keyboard layout and shortcut preferences.",
                  ("xfce4-keyboard-settings",), "input-keyboard"),
    SettingAction("Device", "Power", "Battery, sleep and power-management preferences.",
                  ("xfce4-power-manager-settings",), "battery", "battery"),
    SettingAction("Personalization", "Wallpaper", "Set the XFCE desktop wallpaper.",
                  ("xfdesktop-settings",), "preferences-desktop-wallpaper"),
    SettingAction("Personalization", "Appearance", "Adjust supported GTK appearance settings.",
                  ("xfce4-appearance-settings",), "preferences-desktop-theme"),
    SettingAction("Apps", "Installed applications", "Browse installed desktop programs.",
                  ("xfce4-appfinder",), "application-x-executable"),
    SettingAction("Apps", "Default applications", "Choose supported web, mail and file defaults.",
                  ("exo-preferred-applications",), "preferences-desktop-default-applications"),
    SettingAction("Apps", "Manage software", "Open an installed graphical software manager.",
                  ("mintinstall", "gnome-software", "synaptic"), "system-software-install"),
    SettingAction("Privacy", "Notifications", "Configure the installed XFCE notification daemon.",
                  ("xfce4-notifyd-config",), "preferences-system-notifications"),
    SettingAction("Privacy", "Accessibility", "Review available accessibility aids.",
                  ("xfce4-accessibility-settings",), "preferences-desktop-accessibility"),
    SettingAction("About", "System information", "Read the installed Linux system details.",
                  ("xfce4-about",), "dialog-information"),
    SettingAction("About", "Task Manager", "Inspect actual running processes and resource usage.",
                  ("xfce4-taskmanager", "gnome-system-monitor"), "utilities-system-monitor"),
)

# Distinct ChromeOS Settings screens reuse the same live device contracts as
# Quick Settings. Other rows still lead to their genuine XFCE utilities.
NATIVE_DETAILS = {
    "Connections": ("wifi",),
    "Bluetooth devices": ("bluetooth",),
    "Sound": ("output_sound", "audio_devices"),
    "Displays": ("display",),
    "Power": ("battery", "power"),
}


def available_tool(action: SettingAction, which=shutil.which) -> str | None:
    """Return an allowlisted, installed command, never a shell fragment."""
    return next((name for name in action.tools if which(name)), None)


def search_actions(query: str) -> tuple[SettingAction, ...]:
    words = query.casefold().split()
    return tuple(action for action in ACTIONS if all(
        word in (action.name + " " + action.section + " " + action.description).casefold()
        for word in words))


def status_text(action: SettingAction, state) -> str:
    if state is None:
        return "Status temporarily unavailable"
    if action.status == "network":
        return {"wifi": "Wi-Fi connection active", "ethernet": "Ethernet connection active",
                "offline": "No active network route"}.get(state.network, "Network state unknown")
    if action.status == "sound":
        volume = state.sound.percent
        return ("Output level unavailable" if volume is None else
                f"Output volume {volume}%" + (" · muted" if state.sound.muted else ""))
    if action.status == "battery":
        battery = state.battery
        return f"{battery.percent}% · {battery.label}" if battery else "No battery detected"
    return ""


class ChromeSettings:
    """A reusable Material You settings navigator; never fakes backend state."""

    def __init__(self, shell, Gtk, Gdk, GLib):
        self.shell, self.Gtk, self.Gdk, self.GLib = shell, Gtk, Gdk, GLib
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Settings — RiceBowl ChromeOS")
        self.window.set_default_size(860, 570)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_application(shell)
        self.window.connect("delete-event", self._hide)
        self.window.connect("key-press-event", self._key)
        self.history = []
        self.active_section = None
        self.active_action = None
        self.status_labels = []
        self._built = False
        self._native_panels = []

        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "chrome-settings-root")
        header = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10),
                              "chrome-settings-header")
        self.back_button = Gtk.Button(label="‹  Back")
        self.back_button.set_tooltip_text("Return to the previous Settings page")
        self.back_button.connect("clicked", lambda *_: self.back())
        header.pack_start(self.back_button, False, False, 0)
        self.heading = shell._class(Gtk.Label(label="Settings", xalign=0), "chrome-settings-title")
        header.pack_start(self.heading, True, True, 0)
        root.pack_start(header, False, False, 0)
        self.search = Gtk.SearchEntry()
        self.search.get_accessible().set_name("Search ChromeOS-inspired Linux settings")
        self.search.set_placeholder_text("Search settings")
        self.search.connect("search-changed", self._search_changed)
        root.pack_start(self.search, False, False, 0)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        sidebar_scroll = Gtk.ScrolledWindow()
        sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scroll.set_size_request(225, -1)
        sidebar = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4),
                              "chrome-settings-sidebar")
        self.sidebar_buttons = {}
        for section, icon, _description in SECTIONS:
            button = shell._class(Gtk.Button(), "chrome-settings-nav")
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            content.pack_start(shell._icon(icon, Gtk.IconSize.MENU), False, False, 0)
            content.pack_start(Gtk.Label(label=section, xalign=0), True, True, 0)
            button.add(content)
            button.get_accessible().set_name("Open " + section + " settings")
            button.connect("clicked", lambda _button, name=section: self.show_section(name))
            self.sidebar_buttons[section] = button
            sidebar.pack_start(button, False, False, 0)
        sidebar_scroll.add(sidebar)
        body.pack_start(sidebar_scroll, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        body.pack_start(self.stack, True, True, 0)
        self.content = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9),
                                    "chrome-settings-content")
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.content)
        self.stack.add_named(scroller, "page")
        root.pack_start(body, True, True, 0)
        self.window.add(root)
        self.show_home()
        self.window.hide()

    def _hide(self, *_args):
        for panel in self._native_panels:
            panel.suspend()
        self.window.hide()
        return True

    def close(self):
        for panel in self._native_panels:
            panel.dispose()
        self._native_panels.clear()
        self.window.destroy()

    def _key(self, _widget, event):
        if event.keyval == self.Gdk.KEY_Escape:
            if self.search.get_text():
                self.search.set_text("")
            elif self.history:
                self.back()
            else:
                self.window.hide()
            return True
        return False

    def _clear(self):
        for panel in self._native_panels:
            panel.dispose()
        self._native_panels.clear()
        for child in self.content.get_children():
            self.content.remove(child)
        self.status_labels.clear()

    def _label(self, text, style):
        label = self.shell._class(self.Gtk.Label(label=text, xalign=0), style)
        label.set_line_wrap(True)
        return label

    def _page_heading(self, name, description):
        self.heading.set_text(name)
        self.content.pack_start(self._label(name, "chrome-settings-page-title"), False, False, 0)
        self.content.pack_start(self._label(description, "chrome-settings-subtitle"), False, False, 0)

    def _show(self):
        self.back_button.set_sensitive(bool(self.history))
        for section, button in self.sidebar_buttons.items():
            css = button.get_style_context()
            if section == self.active_section:
                css.add_class("chrome-settings-nav-selected")
            else:
                css.remove_class("chrome-settings-nav-selected")
        if not self._built:
            self.window.show_all()
            self._built = True
        self.content.show_all()

    def present(self, section=None):
        if section in {item[0] for item in SECTIONS}:
            self.show_section(section)
        else:
            self.show_home()
        self.window.present()

    def show_home(self, *, record=False):
        if record:
            self.history.append((self.active_section, self.active_action))
        else:
            self.history.clear()
        self.active_section = self.active_action = None
        self._clear()
        self._page_heading("Settings", "Select a category or search available Linux controls.")
        for section, _icon, description in SECTIONS:
            button = self.shell._class(self.Gtk.Button(label=section + "  ›"), "chrome-settings-row")
            button.set_tooltip_text(description)
            button.get_accessible().set_name("Open " + section)
            button.connect("clicked", lambda _button, name=section: self.show_section(name))
            self.content.pack_start(button, False, False, 0)
        self._show()

    def show_section(self, section, *, record=True):
        group = next((item for item in SECTIONS if item[0] == section), None)
        if group is None:
            return
        if self.search.get_text():
            self.search.set_text("")
        if record:
            self.history.append((self.active_section, self.active_action))
        self.active_section, self.active_action = section, None
        self._clear()
        self._page_heading(section, group[2])
        for action in ACTIONS:
            if action.section != section:
                continue
            button = self.shell._class(self.Gtk.Button(), "chrome-settings-row")
            column = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=2)
            column.pack_start(self._label(action.name + "  ›", "chrome-settings-action"),
                              False, False, 0)
            column.pack_start(self._label(action.description, "chrome-settings-subtitle"),
                              False, False, 0)
            button.add(column)
            button.get_accessible().set_name("Open " + action.name)
            button.connect("clicked", lambda _button, item=action: self.show_detail(item))
            self.content.pack_start(button, False, False, 0)
        self._show()

    def show_detail(self, action, *, record=True):
        if record:
            self.history.append((self.active_section, self.active_action))
        self.active_section, self.active_action = action.section, action
        self._clear()
        self._page_heading(action.name, action.description)
        if action.status:
            label = self._label(status_text(action, self.shell._last_status),
                                "chrome-settings-state")
            self.status_labels.append((action, label))
            self.content.pack_start(label, False, False, 0)
        for kind in NATIVE_DETAILS.get(action.name, ()):
            panel = NativeAquaControls(
                self.shell, self.Gtk, self.GLib, self.content,
                is_current=lambda selected=action: self.window.get_visible() and
                    self.active_action == selected,
                style_prefix="chrome", backend=self.shell.chrome_controller.hardware,
                runner=self.shell.chrome_controller.runner)
            getattr(panel, kind)()
            self._native_panels.append(panel)
        tool = available_tool(action)
        button = self.shell._class(self.Gtk.Button(label="Open installed Linux utility"),
                                   "chrome-settings-primary")
        button.set_sensitive(tool is not None)
        if tool is None:
            button.set_label("No supported Linux settings utility installed")
            button.set_tooltip_text("Install " + " or ".join(action.tools) + " to configure this")
        else:
            button.connect("clicked", lambda _button, command=tool: self.shell._open_tool(command))
        self.content.pack_start(button, False, False, 0)
        self._show()
        for panel in self._native_panels:
            panel.refresh()

    def back(self):
        if not self.history:
            self.show_home()
            return
        section, action = self.history.pop()
        if action:
            self.show_detail(action, record=False)
        elif section:
            self.show_section(section, record=False)
        else:
            self.show_home()

    def _search_changed(self, entry):
        query = entry.get_text().strip()
        if not query:
            if self.active_action:
                self.show_detail(self.active_action, record=False)
            elif self.active_section:
                self.show_section(self.active_section, record=False)
            else:
                self.show_home()
            return
        self._clear()
        self.heading.set_text("Search results")
        matches = search_actions(query)
        self.content.pack_start(self._label(f"{len(matches)} settings found", "chrome-settings-subtitle"),
                                False, False, 0)
        for action in matches:
            button = self.shell._class(
                self.Gtk.Button(label=action.section + " · " + action.name + "  ›"),
                "chrome-settings-row")
            button.connect("clicked", lambda _button, item=action: self._select_search_result(item))
            self.content.pack_start(button, False, False, 0)
        if not matches:
            self.content.pack_start(self._label("No matching local settings. Try another term.",
                                                "chrome-settings-subtitle"), False, False, 0)
        self._show()

    def _select_search_result(self, action):
        self.search.set_text("")
        self.show_detail(action)

    def refresh(self):
        for action, label in self.status_labels:
            label.set_text(status_text(action, self.shell._last_status))
