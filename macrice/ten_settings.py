"""Independent Windows 10 Settings shell with verified Linux controls.

This is a native GTK renderer. XFCE and Riceware continue to own all settings;
unsupported Windows-only options are never displayed as fake switches.
"""

from __future__ import annotations

import getpass
import platform
import shutil

from .riceware import pop, spice
from .rice_windows import configure_settings_window, draggable_caption


CATEGORIES = (
    ("system", "System", "Display, sound, notifications, power"),
    ("devices", "Devices", "Bluetooth and connected devices"),
    ("network", "Network & Internet", "Wi-Fi, connections and proxy"),
    ("personalization", "Personalization", "Background, colors and themes"),
    ("apps", "Apps", "Applications and default handlers"),
    ("accounts", "Accounts", "Local Linux user and sign-in"),
    ("time", "Time & Language", "Date, time, region and keyboard"),
    ("accessibility", "Ease of Access", "Accessible input and display"),
    ("privacy", "Privacy", "Actual desktop access and permissions"),
)

CATEGORY_ICONS = {
    "system": "video-display", "devices": "bluetooth-active",
    "network": "network-wireless", "personalization": "preferences-desktop-wallpaper",
    "apps": "applications-system", "accounts": "system-users",
    "time": "preferences-system-time", "accessibility": "preferences-desktop-accessibility",
    "privacy": "changes-prevent",
}

SUBPAGES = {
    "sound": ("system", "Sound"),
    "display": ("system", "Display"),
    "notifications": ("system", "Notifications & actions"),
    "about": ("system", "About"),
}


def page_parent(page):
    return SUBPAGES[page][0] if page in SUBPAGES else "home"


class TenSettings:
    def __init__(self, shell, Gtk, Gdk, GLib, runner):
        self.shell, self.Gtk, self.GLib, self.runner = shell, Gtk, GLib, runner
        self.closed = False
        self.epoch = 0
        self.current = "home"
        self._positioned = False
        self._pending = set()
        self._volume_source = 0
        self._brightness_source = 0
        self._sliders = {}
        self._switches = {}
        self._status_labels = {}
        self._category_buttons = {}
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Settings · Windows 10")
        self.window.set_decorated(False)
        self.window.set_default_size(880, 600)
        configure_settings_window(self.window, Gdk, role="ricebowl-windows10-settings")
        from .window_geometry import restore_and_track

        self._positioned = restore_and_track(
            self.window, "ricebowl-windows10-settings", Gdk, GLib)
        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                            "ten-settings-root")
        toolbar = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10),
                               "ten-settings-toolbar")
        self.back = shell._class(Gtk.Button(label="‹"), "ten-settings-action")
        self.back.get_accessible().set_name("Back to previous settings level")
        self.back.connect("clicked", lambda _button: self.navigate(page_parent(self.current)))
        toolbar.pack_start(self.back, False, False, 0)
        self.breadcrumb = shell._class(Gtk.Label(label="Settings", xalign=0),
                                       "ten-action-title")
        toolbar.pack_start(draggable_caption(self.window, self.breadcrumb, Gtk, Gdk),
                           True, True, 0)
        refresh = shell._class(Gtk.Button(label="Refresh"), "ten-settings-action")
        refresh.get_accessible().set_name("Refresh current settings and hardware state")
        refresh.connect("clicked", lambda _button: self.refresh())
        toolbar.pack_end(refresh, False, False, 0)
        close = shell._class(Gtk.Button(label="×"), "ten-rail-button")
        close.get_accessible().set_name("Close Settings")
        close.connect("clicked", lambda _button: self.hide())
        toolbar.pack_end(close, False, False, 0)
        root.pack_start(toolbar, False, False, 0)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        sidebar = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3),
                               "ten-settings-sidebar")
        sidebar.set_size_request(218, -1)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Find a setting")
        self.search.get_accessible().set_name("Search Windows 10 settings categories")
        self.search.connect("search-changed", self._filter)
        sidebar.pack_start(self.search, False, False, 4)
        home = shell._class(Gtk.Button(label="⌂   Home"), "ten-settings-nav")
        home.connect("clicked", lambda _button: self.navigate("home"))
        sidebar.pack_start(home, False, False, 0)
        for key, title, _desc in CATEGORIES:
            button = shell._class(Gtk.Button(label=title), "ten-settings-nav")
            button.set_halign(Gtk.Align.FILL)
            button.get_child().set_xalign(0)
            button.get_accessible().set_name("Settings: " + title)
            button.connect("clicked", lambda _button, name=key: self.navigate(name))
            sidebar.pack_start(button, False, False, 0)
            self._category_buttons[key] = button
        main.pack_start(sidebar, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.add_named(self._build_home(), "home")
        for key, title, desc in CATEGORIES:
            self.stack.add_named(self._build_category(key, title, desc), key)
        for key, (_parent, title) in SUBPAGES.items():
            self.stack.add_named(self._build_subpage(key, title), key)
        main.pack_start(self.stack, True, True, 0)
        root.pack_start(main, True, True, 0)
        self.window.add(root)
        self.window.connect("delete-event", lambda *_args: self._on_delete())
        self.window.connect("key-press-event", self._key)

    def _on_delete(self):
        self.hide()
        return True

    def _key(self, _window, event):
        if event.keyval == self.Gtk.accelerator_parse("Escape")[0]:
            if self.current == "home":
                self.hide()
            else:
                self.navigate(page_parent(self.current))
            return True
        return False

    def _page(self, title, description):
        Gtk = self.Gtk
        body = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11),
                                 "ten-settings-page")
        body.pack_start(self.shell._class(Gtk.Label(label=title, xalign=0),
                                          "ten-settings-heading"), False, False, 0)
        text = self.shell._class(Gtk.Label(label=description, xalign=0), "ten-muted")
        text.set_line_wrap(True)
        body.pack_start(text, False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(body)
        return scroll, body

    def _build_home(self):
        Gtk = self.Gtk
        page, body = self._page("Windows Settings", "Find a setting or explore a category below.")
        grid = Gtk.Grid(row_spacing=9, column_spacing=9)
        grid.set_column_homogeneous(True)
        for index, (key, title, description) in enumerate(CATEGORIES):
            tile = self.shell._class(Gtk.Button(), "ten-settings-tile")
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            icon = Gtk.Image.new_from_icon_name(CATEGORY_ICONS[key], Gtk.IconSize.DIALOG)
            icon.set_pixel_size(30)
            icon.get_style_context().add_class("ten-settings-tile-icon")
            content.pack_start(icon, False, False, 0)
            content.pack_start(self.shell._class(Gtk.Label(label=title, xalign=0),
                                                 "ten-network-name"), False, False, 0)
            detail = self.shell._class(Gtk.Label(label=description, xalign=0), "ten-muted")
            detail.set_line_wrap(True)
            content.pack_start(detail, False, False, 0)
            tile.add(content)
            tile.get_accessible().set_name("Open " + title)
            tile.connect("clicked", lambda _button, target=key: self.navigate(target))
            grid.attach(tile, index % 3, index // 3, 1, 1)
        body.pack_start(grid, False, False, 0)
        return page

    def _action(self, body, title, command=None, callback=None):
        button = self.shell._class(self.Gtk.Button(label=title), "ten-settings-action")
        button.set_halign(self.Gtk.Align.START)
        button.get_accessible().set_name(title)
        selected = command if command and shutil.which(command) else None
        button.set_sensitive(callback is not None or selected is not None)
        if callback:
            button.connect("clicked", lambda _button: callback())
        elif selected:
            button.connect("clicked", lambda _button: self.shell._open_tool(selected))
        else:
            button.set_tooltip_text("Required Linux settings tool is not installed")
        body.pack_start(button, False, False, 0)

    def _build_category(self, key, title, description):
        page, body = self._page(title, description)
        if key == "system":
            for name in ("display", "sound", "notifications", "about"):
                self._action(body, SUBPAGES[name][1], callback=lambda target=name:
                             self.navigate(target))
            self._action(body, "Power management", "xfce4-power-manager-settings")
        elif key == "network":
            self._switch(body, "wifi", "Wi-Fi radio")
            self._status(body, "network")
            self._action(body, "Show available Wi-Fi networks",
                         callback=lambda: self.shell._toggle_ten_network())
            self._action(body, "Advanced NetworkManager settings", "nm-connection-editor")
        elif key == "devices":
            self._switch(body, "bluetooth", "Bluetooth radio")
            self._status(body, "bluetooth")
            self._action(body, "Bluetooth devices and pairing", "blueman-manager")
            self._action(body, "Mouse and touchpad", "xfce4-mouse-settings")
            self._action(body, "Keyboard", "xfce4-keyboard-settings")
        elif key == "personalization":
            self._action(body, "Desktop background", "xfdesktop-settings")
            self._action(body, "Appearance and fonts", "xfce4-appearance-settings")
            self._action(body, "Window manager", "xfwm4-settings")
        elif key == "apps":
            self._action(body, "Default applications", "xfce4-mime-settings")
            self._action(body, "Session and startup", "xfce4-session-settings")
        elif key == "accounts":
            body.pack_start(self.shell._class(self.Gtk.Label(
                label="Signed in as " + getpass.getuser(), xalign=0), "ten-action-detail"),
                False, False, 0)
            self._action(body, "User account settings", "users-admin")
        elif key == "time":
            self._action(body, "Calendar and time", "xfce4-datetime-settings")
            self._action(body, "Keyboard layouts", "xfce4-keyboard-settings")
        elif key == "accessibility":
            self._action(body, "Accessibility", "xfce4-accessibility-settings")
            self._action(body, "Display scaling", "xfce4-display-settings")
        elif key == "privacy":
            note = self.shell._class(self.Gtk.Label(
                label="System privacy permissions are controlled by Linux and XFCE. "
                      "Windows-only privacy switches are intentionally unavailable.",
                xalign=0), "ten-muted")
            note.set_line_wrap(True)
            body.pack_start(note, False, False, 0)
            self._action(body, "Notification preferences", "xfce4-notifyd-config")
        return page

    def _build_subpage(self, key, title):
        page, body = self._page(title, "Live Linux settings · changes require verified readback")
        if key == "sound":
            self._slider(body, "audio", "Output volume", 0, 100)
            self._switch(body, "audio_mute", "Mute output")
            self._action(body, "Advanced sound mixer", "pavucontrol")
        elif key == "display":
            self._slider(body, "brightness", "Screen brightness", 1, 100)
            self._action(body, "Resolution and monitor arrangement", "xfce4-display-settings")
        elif key == "notifications":
            self._switch(body, "quiet", "Focus assist (Do Not Disturb)")
            self._action(body, "Notification preferences", "xfce4-notifyd-config")
        elif key == "about":
            body.pack_start(self.shell._class(self.Gtk.Label(
                label=f"{platform.system()} · {platform.release()} · {platform.machine()}",
                xalign=0), "ten-action-detail"), False, False, 0)
        return page

    def _status(self, body, name):
        label = self.shell._class(self.Gtk.Label(label="Reading status…", xalign=0),
                                  "ten-action-detail")
        label.set_line_wrap(True)
        body.pack_start(label, False, False, 0)
        self._status_labels[name] = label

    def _switch(self, body, name, title):
        button = self.shell._class(self.Gtk.ToggleButton(label=title), "ten-live-switch")
        button.set_sensitive(False)
        button.get_accessible().set_name("Toggle " + title)
        button.connect("clicked", lambda _button, kind=name: self._toggle(kind))
        button.set_halign(self.Gtk.Align.START)
        body.pack_start(button, False, False, 0)
        self._switches[name] = button

    def _slider(self, body, name, title, lower, upper):
        box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(self.shell._class(self.Gtk.Label(label=title, xalign=0),
                                         "ten-action-detail"), False, False, 0)
        slider = self.Gtk.Scale.new_with_range(self.Gtk.Orientation.HORIZONTAL,
                                                lower, upper, 5)
        slider.set_sensitive(False)
        slider.set_draw_value(True)
        slider.get_accessible().set_name(title)
        slider.connect("value-changed", lambda _slider, kind=name: self._queue_slider(kind))
        box.pack_start(slider, False, False, 0)
        body.pack_start(box, False, False, 0)
        self._sliders[name] = slider

    def _filter(self, entry):
        query = entry.get_text().casefold().strip()
        for key, title, desc in CATEGORIES:
            self._category_buttons[key].set_visible(not query or
                query in (title + " " + desc).casefold())

    def show(self, page="home"):
        if self.closed:
            return
        rect = self.shell._desktop_rect()
        width, height = min(880, rect.width - 24), min(600, rect.height - 72)
        if width < 460 or height < 310:
            self.shell._error("The display is too small for Settings.")
            return
        self.window.show_all()
        self._filter(self.search)
        if not self._positioned:
            self.window.resize(width, height)
            self.window.move(rect.x + (rect.width - width) // 2,
                             rect.y + (rect.height - height - 40) // 2)
            self._positioned = True
        self.navigate(page)
        self.window.present()

    def hide(self):
        self.epoch += 1
        for source in (self._volume_source, self._brightness_source):
            if source:
                self.GLib.source_remove(source)
        self._volume_source = self._brightness_source = 0
        self.window.hide()

    def navigate(self, page):
        if page not in ("home", *(key for key, _, _ in CATEGORIES), *SUBPAGES):
            page = "home"
        self.current = page
        self.stack.set_visible_child_name(page)
        title = next((text for key, text, _desc in CATEGORIES if key == page),
                     SUBPAGES[page][1] if page in SUBPAGES else "Settings")
        self.breadcrumb.set_text("Settings  /  " + title if page != "home" else "Settings")
        self.back.set_sensitive(page != "home")
        self.refresh()

    def _request(self, name, operation, callback, *, on_stale=None):
        epoch = self.epoch

        def ready(response):
            if self.closed:
                return
            if self.window.get_visible() and epoch == self.epoch:
                callback(response)
            elif on_stale is not None:
                on_stale()

        self.runner.submit("ten-settings-" + name, operation, ready)

    def refresh(self):
        if self.closed or not self.window.get_visible():
            return
        capabilities = {
            "network": ("wifi", "network"),
            "devices": ("bluetooth",),
            "sound": ("audio",),
            "display": ("brightness",),
            "notifications": ("quiet",),
        }.get(self.current, ())
        for capability in capabilities:
            self._request(capability, lambda name=capability: (
                pop.quiet_mode() if name == "quiet" else spice.read(name)),
                lambda response, name=capability: self._render_capability(name, response))

    def _render_capability(self, name, response):
        if name == "quiet":
            result = response.value if response.error is None else None
            available = type(result) is bool
        else:
            result = response.value
            available = response.error is None and result.status == "ok"
            result = result.value if available else None
        switch_name = "audio_mute" if name == "audio" else name
        if switch_name in self._switches:
            button = self._switches[switch_name]
            state = (result if name in ("wifi", "quiet") else
                     result.powered if name == "bluetooth" and result else
                     result.muted if name == "audio" and result else None)
            valid = available and type(state) is bool
            button.set_sensitive(valid and switch_name not in self._pending)
            button.set_active(state if valid else False)
        if name in self._sliders:
            slider = self._sliders[name]
            value = result.percent if name == "audio" and result else result
            valid = available and type(value) is int
            slider.set_sensitive(valid and name not in self._pending)
            if valid:
                self._pending.add("programmatic-" + name)
                try:
                    slider.set_value(value)
                finally:
                    self._pending.discard("programmatic-" + name)
        if name in self._status_labels:
            self._status_labels[name].set_text(
                "Unavailable: no supported backend" if not available else
                ("Connected route: " + str(result) if name == "network" else
                 "Bluetooth: " + ("on" if result.powered else "off") if name == "bluetooth" else
                 str(result)))

    def _toggle(self, name):
        if name in self._pending:
            return
        button = self._switches[name]
        old = not button.get_active()  # GTK toggled before clicked callback.
        button.set_active(old)
        button.set_sensitive(False)
        self._pending.add(name)
        action = {"wifi": "wifi", "bluetooth": "bluetooth_power",
                  "audio_mute": "audio_mute"}.get(name)
        self._request("write-" + name,
                      lambda: pop.set_quiet_mode(not old) if name == "quiet" else
                      spice.change(action, not old),
                      lambda response, expected=not old: self._written(name, expected, response),
                      on_stale=lambda: self._stale_write(name))

    def _stale_write(self, name):
        self._pending.discard(name)
        if self.window.get_visible():
            self.refresh()

    def _written(self, name, expected, response):
        self._pending.discard(name)
        success = response.error is None and (
            response.value is expected if name == "quiet" else
            response.value.status == "ok")
        self._switches[name].set_tooltip_text(
            "Verified" if success else response.error or
            (response.value.reason if name != "quiet" else "Unavailable"))
        self.refresh()

    def _queue_slider(self, name):
        if "programmatic-" + name in self._pending or name in self._pending:
            return
        source_name = "_volume_source" if name == "audio" else "_brightness_source"
        source = getattr(self, source_name)
        if source:
            self.GLib.source_remove(source)
        setattr(self, source_name, self.GLib.timeout_add(300, self._write_slider, name))

    def _write_slider(self, name):
        setattr(self, "_volume_source" if name == "audio" else "_brightness_source", 0)
        if name in self._pending or not self.window.get_visible():
            return False
        value = int(round(self._sliders[name].get_value()))
        self._pending.add(name)
        self._sliders[name].set_sensitive(False)
        action = "audio_volume" if name == "audio" else "brightness"

        def done(response):
            self._pending.discard(name)
            self._sliders[name].set_tooltip_text(
                "Verified" if response.error is None and
                response.value.status == "ok" else "Could not verify the change")
            self.refresh()

        self._request("write-" + name, lambda: spice.change(action, value), done,
                      on_stale=lambda: self._stale_write(name))
        return False

    def close(self):
        if self.closed:
            return
        self.hide()
        for source in (self._volume_source, self._brightness_source):
            if source:
                self.GLib.source_remove(source)
        self.closed = True
        self.window.destroy()
