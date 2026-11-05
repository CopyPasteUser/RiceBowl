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
    ("gaming", "Gaming", "Game controllers and input"),
    ("search", "Search", "Find apps and local files"),
    ("updates", "Update & Security", "Linux software updates and backups"),
)

# Theme icons are looked up through the active system theme, with a standard
# symbolic fallback. Unlike proprietary OS glyphs these are installed assets.
CATEGORY_ICONS = {
    "system": "computer-symbolic", "devices": "input-keyboard-symbolic",
    "network": "network-wireless-symbolic",
    "personalization": "preferences-desktop-wallpaper-symbolic",
    "apps": "view-app-grid-symbolic", "accounts": "avatar-default-symbolic",
    "time": "preferences-system-time-symbolic",
    "accessibility": "preferences-desktop-accessibility-symbolic",
    "privacy": "changes-prevent-symbolic", "gaming": "input-gaming-symbolic",
    "search": "system-search-symbolic", "updates": "software-update-available-symbolic",
}

SUBPAGES = {
    "sound": ("system", "Sound"),
    "display": ("system", "Display"),
    "notifications": ("system", "Notifications & actions"),
    "about": ("system", "About"),
}


def page_parent(page):
    return SUBPAGES[page][0] if page in SUBPAGES else "home"


def search_destinations(query):
    """Search actual navigable pages and their Linux-backed settings terms."""
    terms = query.casefold().split()
    if not terms:
        return ()
    keywords = {
        "system": "power sleep brightness resolution speakers",
        "devices": "bluetooth mouse keyboard pairing touchpad",
        "network": "wifi wi-fi ethernet vpn connection proxy radio",
        "personalization": "wallpaper colors fonts windows themes taskbar",
        "apps": "default applications startup file associations",
        "accounts": "user login sign-in sign in password",
        "time": "calendar timezone language region layouts",
        "accessibility": "scaling magnifier keyboard screenreader",
        "privacy": "permissions notifications tracking",
        "gaming": "controller game joystick",
        "search": "find files applications tracker",
        "updates": "mint update software backup restore security",
        "sound": "volume speakers output mute mixer audio",
        "display": "brightness resolution scaling monitors screen",
        "notifications": "quiet focus assist do not disturb dnd",
        "about": "linux os version computer system information",
    }
    entries = [(key, title, desc) for key, title, desc in CATEGORIES]
    entries.extend((key, title, next(desc for name, _title, desc in CATEGORIES
                                    if name == parent))
                   for key, (parent, title) in SUBPAGES.items())
    return tuple((key, title, desc) for key, title, desc in entries
                 if all(word in (title + " " + desc + " " + keywords.get(key, "")).casefold()
                        for word in terms))


class TenSettings:
    def __init__(self, shell, Gtk, Gdk, GLib, runner):
        self.shell, self.Gtk, self.Gdk, self.GLib, self.runner = shell, Gtk, Gdk, GLib, runner
        self.closed = False
        self.epoch = 0
        self.current = "home"
        self._positioned = False
        self._pending = set()
        self._rendering_switches = set()
        self._volume_source = 0
        self._brightness_source = 0
        self._sliders = {}
        self._switches = {}
        self._status_labels = {}
        self._category_buttons = {}
        self._control_feedback = {}
        self._last_errors = {}
        self._syncing_search = False
        self._search_origin = "home"
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Settings · Windows 10")
        self.window.set_decorated(False)
        self.window.set_default_size(940, 650)
        configure_settings_window(self.window, Gdk, role="ricebowl-windows10-settings")
        from .window_geometry import restore_and_track

        self._positioned = restore_and_track(
            self.window, "ricebowl-windows10-settings", Gdk, GLib)
        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0),
                            "ten-settings-root")
        toolbar = shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8),
                               "ten-settings-toolbar")
        self.back = shell._class(Gtk.Button(label="‹"), "ten-settings-back")
        self.back.get_accessible().set_name("Back to previous settings level")
        self.back.connect("clicked", lambda _button: self._go_back())
        toolbar.pack_start(self.back, False, False, 0)
        self.breadcrumb = shell._class(Gtk.Label(label="Settings", xalign=0),
                                       "ten-settings-caption")
        toolbar.pack_start(draggable_caption(self.window, self.breadcrumb, Gtk, Gdk),
                           True, True, 0)
        refresh = shell._class(Gtk.Button(label="↻"), "ten-settings-chrome")
        refresh.get_accessible().set_name("Refresh current settings and hardware state")
        refresh.connect("clicked", lambda _button: self.refresh())
        toolbar.pack_end(refresh, False, False, 0)
        close = shell._class(Gtk.Button(label="×"), "ten-settings-close")
        close.get_accessible().set_name("Close Settings")
        close.connect("clicked", lambda _button: self.hide())
        toolbar.pack_end(close, False, False, 0)
        root.pack_start(toolbar, False, False, 0)

        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.sidebar = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5),
                                    "ten-settings-sidebar")
        self.sidebar.set_size_request(224, -1)
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Find a setting")
        self.search.get_accessible().set_name("Search Windows 10 settings categories")
        self.search.connect("search-changed", self._search_changed)
        self.sidebar.pack_start(self.search, False, False, 9)
        home = shell._class(Gtk.Button(label="⌂   Home"), "ten-settings-home-link")
        home.connect("clicked", lambda _button: self.navigate("home"))
        self.sidebar.pack_start(home, False, False, 7)
        nav_scroll = Gtk.ScrolledWindow()
        nav_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        nav_scroll.set_shadow_type(Gtk.ShadowType.NONE)
        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for key, title, _desc in CATEGORIES:
            button = shell._class(Gtk.Button(label=title), "ten-settings-nav")
            button.set_halign(Gtk.Align.FILL)
            button.get_child().set_xalign(0)
            button.get_accessible().set_name("Settings: " + title)
            button.connect("clicked", lambda _button, name=key: self.navigate(name))
            nav_box.pack_start(button, False, False, 0)
            self._category_buttons[key] = button
        nav_scroll.add(nav_box)
        self.sidebar.pack_start(nav_scroll, True, True, 0)
        main.pack_start(self.sidebar, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        self.stack.add_named(self._build_home(), "home")
        self.stack.add_named(self._build_results(), "results")
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

    def _go_back(self):
        self.navigate(self._search_origin if self.current == "results" else
                      page_parent(self.current))

    def _key(self, _window, event):
        if event.keyval == self.Gtk.accelerator_parse("Escape")[0]:
            if self.current == "home":
                self.hide()
            else:
                self._go_back()
            return True
        if event.keyval == self.Gtk.accelerator_parse("<Control>f")[0] and \
                event.state & self.Gdk.ModifierType.CONTROL_MASK:
            (self.home_search if self.current == "home" else self.search).grab_focus()
            return True
        return False

    def _page(self, title, description):
        Gtk = self.Gtk
        body = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12),
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
        page, body = self._page("Windows Settings", "Find the Linux setting you need")
        for widget in body.get_children()[:2]:
            widget.set_halign(Gtk.Align.CENTER)
        body.get_style_context().add_class("ten-settings-home")
        self.home_search = Gtk.SearchEntry()
        self.home_search.set_placeholder_text("Find a setting")
        self.home_search.get_accessible().set_name("Search settings")
        self.home_search.set_size_request(330, -1)
        self.home_search.set_halign(Gtk.Align.CENTER)
        self.home_search.connect("search-changed", self._search_changed)
        body.pack_start(self.home_search, False, False, 15)
        grid = Gtk.Grid(row_spacing=8, column_spacing=8)
        grid.set_column_homogeneous(True)
        for index, (key, title, description) in enumerate(CATEGORIES):
            tile = self.shell._class(Gtk.Button(), "ten-settings-tile")
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            icon = self._icon(CATEGORY_ICONS[key], Gtk.IconSize.DIALOG)
            content.pack_start(icon, False, False, 0)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            title_label = self.shell._class(Gtk.Label(label=title, xalign=0),
                                             "ten-settings-tile-title")
            title_label.set_line_wrap(True)
            labels.pack_start(title_label, False, False, 0)
            detail = self.shell._class(Gtk.Label(label=description, xalign=0), "ten-muted")
            detail.set_line_wrap(True)
            labels.pack_start(detail, False, False, 0)
            content.pack_start(labels, True, True, 0)
            tile.add(content)
            tile.get_accessible().set_name("Open " + title)
            tile.connect("clicked", lambda _button, target=key: self.navigate(target))
            grid.attach(tile, index % 3, index // 3, 1, 1)
        body.pack_start(grid, False, False, 0)
        return page

    def _icon(self, name, size):
        theme = self.Gtk.IconTheme.get_default()
        if theme is not None and not theme.has_icon(name):
            name = "preferences-system-symbolic"
        return self.Gtk.Image.new_from_icon_name(name, size)

    def _build_results(self):
        page, body = self._page("Search results", "Select a result to open its settings.")
        self.results_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL,
                                         spacing=3)
        body.pack_start(self.results_box, False, False, 0)
        self.no_results = self.shell._class(self.Gtk.Label(
            label="No matching settings. Try another search term.", xalign=0),
            "ten-settings-empty")
        body.pack_start(self.no_results, False, False, 12)
        return page

    def _populate_results(self, query):
        for child in self.results_box.get_children():
            self.results_box.remove(child)
        matches = search_destinations(query)
        self.no_results.set_visible(not matches)
        for key, title, description in matches:
            row = self.shell._class(self.Gtk.Button(), "ten-settings-row")
            content = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL,
                                   spacing=14)
            content.pack_start(self._icon(CATEGORY_ICONS.get(
                key, CATEGORY_ICONS[SUBPAGES[key][0]] if key in SUBPAGES else
                "preferences-system-symbolic"), self.Gtk.IconSize.BUTTON), False, False, 0)
            labels = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=3)
            labels.pack_start(self.shell._class(self.Gtk.Label(label=title, xalign=0),
                                                 "ten-settings-row-title"), False, False, 0)
            labels.pack_start(self.shell._class(self.Gtk.Label(label=description, xalign=0),
                                                 "ten-muted"), False, False, 0)
            content.pack_start(labels, True, True, 0)
            content.pack_end(self.Gtk.Label(label="›"), False, False, 0)
            row.add(content)
            row.connect("clicked", lambda _button, target=key: self.navigate(target))
            row.get_accessible().set_name("Open " + title)
            self.results_box.pack_start(row, False, False, 0)
        self.results_box.show_all()

    def _search_changed(self, entry):
        if self._syncing_search:
            return
        query = entry.get_text().strip()
        self._syncing_search = True
        try:
            other = self.search if entry is self.home_search else self.home_search
            if other.get_text() != entry.get_text():
                other.set_text(entry.get_text())
        finally:
            self._syncing_search = False
        if query:
            if self.current != "results":
                self._search_origin = self.current
            self._populate_results(query)
            self._activate_page("results")
            if entry is self.home_search:
                self.search.grab_focus()
        elif self.current == "results":
            self._activate_page(self._search_origin)

    def _clear_search(self):
        self._syncing_search = True
        try:
            self.search.set_text("")
            self.home_search.set_text("")
        finally:
            self._syncing_search = False

    def _section(self, body, title):
        label = self.shell._class(self.Gtk.Label(label=title, xalign=0),
                                  "ten-settings-section")
        body.pack_start(label, False, False, 6)

    def _action(self, body, title, command=None, callback=None, description=None):
        button = self.shell._class(self.Gtk.Button(), "ten-settings-row")
        button.set_halign(self.Gtk.Align.FILL)
        button.get_accessible().set_name(title)
        selected = command if command and shutil.which(command) else None
        button.set_sensitive(callback is not None or selected is not None)
        row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=10)
        labels = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=4)
        labels.pack_start(self.shell._class(self.Gtk.Label(label=title, xalign=0),
                                             "ten-settings-row-title"), False, False, 0)
        if description or (command and not selected):
            note = description if (callback or selected) else \
                "Not installed · install the corresponding Linux settings tool"
            subtitle = self.shell._class(self.Gtk.Label(label=note or "", xalign=0),
                                           "ten-muted")
            subtitle.set_line_wrap(True)
            labels.pack_start(subtitle, False, False, 0)
        row.pack_start(labels, True, True, 0)
        row.pack_end(self.shell._class(self.Gtk.Label(label="›"),
                                       "ten-settings-chevron"), False, False, 0)
        button.add(row)
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
            self._section(body, "System settings")
            for name in ("display", "sound", "notifications", "about"):
                self._action(body, SUBPAGES[name][1], callback=lambda target=name:
                             self.navigate(target), description={
                                 "display": "Brightness, monitors and resolution",
                                 "sound": "Output volume, mute and audio devices",
                                 "notifications": "Focus assist and notification preferences",
                                 "about": "Linux version and device architecture"}[name])
            self._action(body, "Power management", "xfce4-power-manager-settings")
        elif key == "network":
            self._section(body, "Network status")
            self._switch(body, "wifi", "Wi-Fi radio")
            self._status(body, "network")
            self._action(body, "Show available Wi-Fi networks",
                         callback=lambda: self.shell._toggle_ten_network())
            self._action(body, "Advanced NetworkManager settings", "nm-connection-editor")
        elif key == "devices":
            self._section(body, "Bluetooth & devices")
            self._switch(body, "bluetooth", "Bluetooth radio")
            self._status(body, "bluetooth")
            self._action(body, "Bluetooth devices and pairing", "blueman-manager")
            self._action(body, "Mouse and touchpad", "xfce4-mouse-settings")
            self._action(body, "Keyboard", "xfce4-keyboard-settings")
        elif key == "personalization":
            self._section(body, "Personalize your desktop")
            self._action(body, "Desktop background", "xfdesktop-settings")
            self._action(body, "Appearance and fonts", "xfce4-appearance-settings")
            self._action(body, "Window manager", "xfwm4-settings")
        elif key == "apps":
            self._section(body, "App settings")
            self._action(body, "Default applications", "xfce4-mime-settings")
            self._action(body, "Session and startup", "xfce4-session-settings")
        elif key == "accounts":
            self._section(body, "Your local account")
            body.pack_start(self.shell._class(self.Gtk.Label(
                label="Signed in as " + getpass.getuser(), xalign=0), "ten-action-detail"),
                False, False, 0)
            self._action(body, "User account settings", "users-admin")
        elif key == "time":
            self._section(body, "Date, time and language")
            self._action(body, "Calendar and time", "xfce4-datetime-settings")
            self._action(body, "Keyboard layouts", "xfce4-keyboard-settings")
        elif key == "accessibility":
            self._section(body, "Accessibility")
            self._action(body, "Accessibility", "xfce4-accessibility-settings")
            self._action(body, "Display scaling", "xfce4-display-settings")
        elif key == "privacy":
            self._section(body, "Linux privacy settings")
            note = self.shell._class(self.Gtk.Label(
                label="System privacy permissions are controlled by Linux and XFCE. "
                      "Windows-only privacy switches are intentionally unavailable.",
                xalign=0), "ten-muted")
            note.set_line_wrap(True)
            body.pack_start(note, False, False, 0)
            self._action(body, "Notification preferences", "xfce4-notifyd-config")
        elif key == "gaming":
            self._section(body, "Game input")
            self._action(body, "Game controller configuration", "jstest-gtk")
            self._action(body, "Input devices", "xfce4-mouse-settings")
        elif key == "search":
            self._section(body, "Find applications and files")
            self._action(body, "Application finder", "xfce4-appfinder")
            self._action(body, "File search", "catfish")
        elif key == "updates":
            self._section(body, "Linux updates and security")
            # This is explicitly an external, user-confirmed graphical handoff,
            # never a silent package installation or a pretend Windows Update.
            self._action(body, "Linux Mint Update Manager", "mintupdate")
            self._action(body, "Backup and restore", "timeshift-gtk")
            self._action(body, "Software manager", "mintinstall")
        return page

    def _build_subpage(self, key, title):
        page, body = self._page(title, "Changes are applied to your Linux desktop")
        if key == "sound":
            self._section(body, "Output")
            self._slider(body, "audio", "Output volume", 0, 100)
            self._switch(body, "audio_mute", "Mute output")
            self._action(body, "Advanced sound mixer", "pavucontrol")
        elif key == "display":
            self._section(body, "Brightness and display")
            self._slider(body, "brightness", "Screen brightness", 1, 100)
            self._action(body, "Resolution and monitor arrangement", "xfce4-display-settings")
        elif key == "notifications":
            self._section(body, "Notifications")
            self._switch(body, "quiet", "Focus assist (Do Not Disturb)")
            self._action(body, "Notification preferences", "xfce4-notifyd-config")
        elif key == "about":
            self._section(body, "Device specifications")
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
        row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=16)
        title_label = self.shell._class(self.Gtk.Label(label=title, xalign=0),
                                        "ten-settings-row-title")
        row.pack_start(title_label, True, True, 0)
        button = self.shell._class(self.Gtk.Switch(), "ten-settings-switch")
        button.set_sensitive(False)
        button.get_accessible().set_name(title)
        button.connect("state-set", self._switch_state_set, name)
        row.pack_end(button, False, False, 0)
        body.pack_start(row, False, False, 0)
        feedback = self.shell._class(self.Gtk.Label(label="Checking availability…", xalign=0),
                                     "ten-settings-feedback")
        feedback.set_line_wrap(True)
        body.pack_start(feedback, False, False, 0)
        self._control_feedback[name] = feedback
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
        feedback = self.shell._class(self.Gtk.Label(label="Checking availability…", xalign=0),
                                     "ten-settings-feedback")
        feedback.set_line_wrap(True)
        body.pack_start(feedback, False, False, 0)
        self._control_feedback[name] = feedback
        self._sliders[name] = slider

    def show(self, page="home"):
        if self.closed:
            return
        rect = self.shell._desktop_rect()
        width, height = min(940, rect.width - 24), min(650, rect.height - 72)
        if width < 460 or height < 310:
            self.shell._error("The display is too small for Settings.")
            return
        self.window.show_all()
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
        self._clear_search()
        self._activate_page(page)

    def _activate_page(self, page):
        self.current = page
        self.stack.set_visible_child_name(page)
        hide_sidebar = page == "home"
        self.sidebar.set_no_show_all(hide_sidebar)
        if hide_sidebar:
            self.sidebar.hide()
        else:
            self.sidebar.show_all()
        for name, button in self._category_buttons.items():
            context = button.get_style_context()
            if name == (SUBPAGES[page][0] if page in SUBPAGES else page):
                context.add_class("ten-settings-nav-selected")
            else:
                context.remove_class("ten-settings-nav-selected")
        title = next((text for key, text, _desc in CATEGORIES if key == page),
                     SUBPAGES[page][1] if page in SUBPAGES else
                     "Search results" if page == "results" else "Settings")
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
            available = response.error is None and result is not None and \
                getattr(result, "status", None) == "ok"
            result = result.value if available else None
        switch_name = "audio_mute" if name == "audio" else name
        if switch_name in self._switches:
            button = self._switches[switch_name]
            state = (result if name in ("wifi", "quiet") else
                     result.powered if name == "bluetooth" and result else
                     result.muted if name == "audio" and result else None)
            valid = available and type(state) is bool
            button.set_sensitive(valid and switch_name not in self._pending)
            self._rendering_switches.add(switch_name)
            try:
                button.set_active(state if valid else False)
            finally:
                self._rendering_switches.discard(switch_name)
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
                "Unavailable: " + (response.error or "no supported backend") if not available else
                ("Active route: " + {"wifi": "Wi-Fi", "ethernet": "Ethernet",
                                     "offline": "Offline", "vpn": "VPN"}.get(
                                         str(result), "Unknown") if name == "network" else
                 "Bluetooth: " + ("on" if result.powered else "off") if name == "bluetooth" else
                 str(result)))
        feedback_name = "audio_mute" if name == "audio" else name
        for target in (feedback_name, name):
            label = getattr(self, "_control_feedback", {}).get(target)
            if label is not None and target not in self._pending:
                label.set_text(self._last_errors[target] if target in self._last_errors else
                               "Ready · changes verified by Linux" if available else
                               "Unavailable · " + (response.error or "backend not found"))

    def _switch_state_set(self, _button, requested, name):
        if name in self._rendering_switches:
            return False
        self._toggle(name, requested=requested)
        return True  # Keep old visual state until read-back confirms the write.

    def _toggle(self, name, *, requested=None):
        if name in self._pending:
            return
        button = self._switches[name]
        if requested is None:  # Older toggle-button adapter compatibility.
            old = not button.get_active()
            button.set_active(old)
            requested = not old
        button.set_sensitive(False)
        self._pending.add(name)
        if name in getattr(self, "_control_feedback", {}):
            self._control_feedback[name].set_text("Applying change…")
        self._last_errors.pop(name, None)
        action = {"wifi": "wifi", "bluetooth": "bluetooth_power",
                  "audio_mute": "audio_mute"}.get(name)
        self._request("write-" + name,
                      lambda: pop.set_quiet_mode(requested) if name == "quiet" else
                      spice.change(action, requested),
                      lambda response, expected=requested: self._written(name, expected, response),
                      on_stale=lambda: self._stale_write(name))

    def _stale_write(self, name):
        self._pending.discard(name)
        if self.window.get_visible():
            self.refresh()

    def _written(self, name, expected, response):
        self._pending.discard(name)
        success = response.error is None and (
            response.value is expected if name == "quiet" else
            getattr(response.value, "status", None) == "ok")
        self._switches[name].set_tooltip_text(
            "Verified" if success else response.error or
            (getattr(response.value, "reason", "Unavailable") if name != "quiet" else
             "Unavailable"))
        if not success:
            self._last_errors[name] = "Change failed · " + (
                response.error or getattr(response.value, "reason", "No verified result"))
        if name in getattr(self, "_control_feedback", {}):
            self._control_feedback[name].set_text(
                "Change verified" if success else self._last_errors[name])
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
        self._last_errors.pop(name, None)
        self._sliders[name].set_sensitive(False)
        if name in self._control_feedback:
            self._control_feedback[name].set_text("Applying change…")
        action = "audio_volume" if name == "audio" else "brightness"

        def done(response):
            self._pending.discard(name)
            success = response.error is None and getattr(response.value, "status", None) == "ok"
            self._sliders[name].set_tooltip_text("Verified" if success else
                                                 "Could not verify the change")
            if not success:
                self._last_errors[name] = "Change failed · " + (
                    response.error or getattr(response.value, "reason", "No verified result"))
            if name in self._control_feedback:
                self._control_feedback[name].set_text(
                    "Change verified" if success else self._last_errors[name])
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
