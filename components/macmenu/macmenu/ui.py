"""A compact native macOS-inspired GTK launcher with a warm toggle path."""

import shutil
import subprocess
import logging
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

from . import __version__
from .catalog import installed_apps
from .commands import resolve_command
from .config import config_path, load, parse_backup, sanitize, save, save_backup
from .logging_setup import setup_logging
from .model import ORDER, AppEntry, move_favorite, select_apps, visible_page

BRAND_ASSETS = Path(__file__).resolve().parent.parent / "assets"


PALETTES = {
    "dark": dict(
        surface="#0e1118", sidebar="#151b25", input="#202833", hover="#303c4c",
        active="#214469", text="#f6f8ff", muted="#abb5c6", line="#323c4c",
        accent="#0a84ff", badge="#1b3656", card="#1a222d", danger="#ff6961",
    ),
    "light": dict(
        surface="#f5f7fb", sidebar="#e9edf4", input="#ffffff", hover="#e4ecf7",
        active="#d9eaff", text="#1a2435", muted="#627187", line="#d5deeb",
        accent="#007aff", badge="#e5f1ff", card="#ffffff", danger="#c73536",
    ),
    "graphite": dict(
        surface="#1b1d21", sidebar="#22252a", input="#2b2e33", hover="#383d44",
        active="#3b4653", text="#f5f5f7", muted="#b5bac2", line="#40454c",
        accent="#a5bedc", badge="#3b4653", card="#282b30", danger="#ff7773",
    ),
    "ocean": dict(
        surface="#101c2d", sidebar="#14243a", input="#1b304a", hover="#274463",
        active="#214f76", text="#f5faff", muted="#b4c8dc", line="#31465f",
        accent="#69b8ff", badge="#1b4668", card="#182a41", danger="#ff8a86",
    ),
    "violet": dict(
        surface="#211a2a", sidebar="#2a2235", input="#372c43", hover="#493b59",
        active="#513766", text="#faf6ff", muted="#c7b7d8", line="#50415d",
        accent="#d6aaff", badge="#513766", card="#30263c", danger="#ff8e9f",
    ),
    "glass-dark": dict(
        surface="rgba(20,29,43,.94)", sidebar="rgba(32,44,62,.88)", input="rgba(45,62,82,.85)", hover="#35475f",
        active="#294e76", text="#f8fbff", muted="#b7c9db", line="rgba(179,209,237,.28)",
        accent="#8bc6ff", badge="#294e76", card="rgba(28,42,60,.86)", danger="#ff8f8f",
    ),
    "glass-light": dict(
        surface="rgba(240,248,255,.94)", sidebar="rgba(219,235,249,.89)", input="rgba(255,255,255,.94)", hover="#d8eaf8",
        active="#c8e5f8", text="#1a3048", muted="#4e657c", line="rgba(55,98,142,.24)",
        accent="#136da9", badge="#e0effa", card="rgba(255,255,255,.88)", danger="#b72c36",
    ),
    "aqua": dict(
        surface="#e8f4fb", sidebar="#cae6f4", input="#ffffff", hover="#d0eefa",
        active="#b4dff8", text="#153550", muted="#4b6980", line="#a2cce3",
        accent="#006fae", badge="#d2edfb", card="#f7fcff", danger="#b22c3b",
    ),
}

THEMES = (
    ("system", "Auto"), ("dark", "Midnight"), ("light", "Light"),
    ("graphite", "Graphite"), ("ocean", "Ocean"), ("violet", "Violet"),
    ("glass-dark", "Glass Dark"), ("glass-light", "Glass Light"), ("aqua", "Aqua"),
)

# Freedesktop/XFCE icon names, not bundled imitation macOS application assets.
CATEGORY_ICONS = {
    "Favorites": "starred-symbolic",
    "Recent": "document-open-recent-symbolic",
    "All Apps": "view-grid-symbolic",
    "Development": "applications-engineering-symbolic",
    "Internet": "network-wireless-symbolic",
    "Office": "document-edit-symbolic",
    "Media": "applications-multimedia-symbolic",
    "Graphics": "applications-graphics-symbolic",
    "Games": "applications-games-symbolic",
    "Education": "applications-science-symbolic",
    "System": "preferences-system-symbolic",
    "Utilities": "applications-utilities-symbolic",
    "Other": "preferences-other-symbolic",
}

STYLESHEET = """
window.launcher-window {{ background-color: transparent; }}
#surface {{ background-color: {surface}; color: {text}; border-radius: 20px;
    border: 1px solid {line}; }}
.header {{ padding: 12px 12px 11px; }}
.brand-mark {{ margin: 0 3px 0 2px; }}
.mac-rail {{ background-color: {sidebar}; border-right: 1px solid {line};
    padding: 8px 5px 9px; }}
button.rail-button {{ background-image: none; background-color: transparent;
    border: 1px solid transparent; border-radius: 11px; color: {muted};
    min-width: 37px; min-height: 35px; padding: 4px; box-shadow: none; }}
button.rail-button:hover {{ background-color: {hover}; color: {text}; }}
button.rail-button.selected {{ background-color: {active}; color: {accent}; }}
button.rail-button image {{ color: inherit; -gtk-icon-shadow: none; }}
.content {{ background: {surface}; padding: 8px 11px 11px; }}
.content-title {{ color: {text}; font-family: "SF Pro Text", "Inter", sans-serif;
    font-weight: 600; font-size: 13px; }}
.content-count {{ color: {muted}; font-size: 11px; }}
.search-entry {{ color: {text}; caret-color: {text}; background-color: {input};
    background-image: none; border: 1px solid {line}; border-radius: 12px;
    padding: 8px 10px; font-size: 13px; box-shadow: none; }}
.search-entry:focus {{ border: 1px solid {accent};
    box-shadow: none; }}
button.icon-button, button.icon-button:hover, button.icon-button:active {{
    border: 1px solid {line}; background-image: none; background-color: {card};
    border-radius: 999px; min-width: 32px; min-height: 32px;
    padding: 0; color: {text}; box-shadow: none; }}
button.icon-button:hover {{ background-color: {hover}; }}
button.load-more {{ background-image: none; background-color: {card};
    color: {accent}; border: 1px solid {line}; border-radius: 999px;
    padding: 6px 14px; margin-top: 5px; font-size: 11px; box-shadow: none; }}
button.load-more:hover {{ background-color: {hover}; }}
button:focus, row:focus {{ outline: 2px solid {accent}; outline-offset: -2px; }}
.app-panel {{ background-color: {card}; border: 1px solid {line};
    border-radius: 15px; padding: 7px 6px; }}
.app-tile {{ border-radius: 12px; background-color: transparent;
    padding: 6px 4px 3px; }}
.app-tile:hover {{ background-color: {hover}; }}
.app-tile:focus {{ background-color: {active}; }}
.tile-label {{ color: {text}; font-family: "SF Pro Text", "Inter", sans-serif;
    font-size: 11px; font-weight: 500; }}
.empty-title {{ color: {text}; font-size: 14px; font-weight: 600; }}
.empty-hint {{ color: {muted}; font-size: 12px; }}
.macmenu-popup {{ background-color: {card}; border: 1px solid {line};
    border-radius: 11px; padding: 5px; }}
.macmenu-popup menuitem {{ color: {text}; border-radius: 7px; padding: 6px 8px; }}
.macmenu-popup menuitem:hover {{ background-color: {active}; }}
.settings-dialog, .settings-dialog background {{ background-color: {surface}; color: {text}; }}
.settings-dialog stack, .settings-dialog viewport, .settings-dialog scrolledwindow {{
    background-color: {surface}; color: {text}; }}
.settings-dialog label {{ color: {text}; }}
.settings-dialog .setting-help {{ color: {muted}; }}
.settings-title {{ color: {text}; font-family: "SF Pro Display", "Inter", sans-serif;
    font-size: 17px; font-weight: 600; }}
.settings-card {{ background-color: {card}; border: 1px solid {line};
    border-radius: 13px; padding: 4px; }}
.settings-card separator {{ background-color: {line}; min-height: 1px; margin: 0 10px; }}
.theme-choices {{ margin: 4px 0 1px; }}
.settings-dialog button.theme-choice {{ background-image: none; background-color: transparent;
    color: {text}; border: 1px solid transparent; border-radius: 12px;
    min-width: 62px; min-height: 60px; padding: 5px 4px; box-shadow: none; }}
.settings-dialog button.theme-choice:hover {{ background-color: {hover}; }}
.settings-dialog button.theme-choice.selected {{ border: 2px solid {accent};
    background-color: {active}; }}
.theme-preview {{ border-radius: 8px; border: 1px solid {line};
    min-width: 39px; min-height: 24px; font-size: 17px; }}
.theme-preview.preview-system {{ background-color: #657587; color: #ffffff; }}
.theme-name {{ color: {text}; font-size: 10px; }}
.setting-row {{ padding: 8px 10px; }}
.setting-title {{ color: {text}; font-size: 12px; font-weight: 600; }}
.setting-help {{ color: {muted}; font-size: 10px; }}
.settings-dialog button {{ background-image: none; background-color: {input};
    border: 1px solid {line}; border-radius: 9px; color: {text};
    box-shadow: none; padding: 5px 10px; }}
.settings-dialog button:hover {{ background-color: {hover}; }}
.settings-dialog stackswitcher {{ background-color: {card};
    border: 1px solid {line}; border-radius: 999px; padding: 2px; }}
.settings-dialog stackswitcher button {{ background-color: transparent;
    border: 0; border-radius: 999px; padding: 6px 13px; color: {muted}; }}
.settings-dialog stackswitcher button:checked {{ background-color: {active};
    color: {text}; }}
.settings-dialog switch {{ background-color: {line}; border-radius: 999px;
    border: none; min-width: 40px; min-height: 23px; }}
.settings-dialog switch:checked {{ background-color: {accent}; }}
.settings-dialog switch slider {{ background-color: #ffffff; border-radius: 999px;
    min-width: 19px; min-height: 19px; margin: 2px; box-shadow: none; }}
.settings-dialog button.danger-action {{ color: {danger}; }}
scrolledwindow, viewport, flowbox, list {{ background: transparent; }}
scrollbar slider {{ background: {line}; border-radius: 6px; min-width: 5px; }}
scrollbar slider:hover {{ background: {muted}; }}
"""


def css(widget: Gtk.Widget, name: str) -> Gtk.Widget:
    widget.get_style_context().add_class(name)
    return widget


def icon(name: str, pixels: int = 18) -> Gtk.Image:
    image = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.BUTTON)
    image.set_pixel_size(pixels)
    return image


def app_icon(app: AppEntry, pixels: int) -> Gtk.Image:
    if app.icon:
        image = Gtk.Image.new_from_gicon(app.icon, Gtk.IconSize.DIALOG)
        image.set_pixel_size(pixels)
        return image
    return icon("application-x-executable", pixels)


class LauncherWindow(Gtk.ApplicationWindow):
    PAGE_SIZE = 30

    def __init__(self, application: Gtk.Application):
        super().__init__(application=application, title="MacMenu")
        self.log = logging.getLogger("macmenu")
        self.settings = load()
        self.apps = installed_apps()
        self.by_id = {app.app_id: app for app in self.apps}
        self.category = "All Apps"
        self._preferences_open = False
        self._preferences_dialog = None
        self._menu_open = False
        self._focus_out_source = None
        self._css_provider = None
        self._config_monitor = None
        self._config_reload_source = 0
        self._render_limit = self.PAGE_SIZE
        self._last_selection = None
        self._brand_pixbufs = {}
        # Reuse the same GTK tiles during search instead of destroying widgets
        # and reloading icons for every keystroke.
        self._tile_pool = []
        self.set_default_size(572, 486)
        self.set_size_request(420, 350)
        self.set_resizable(True)
        self.set_decorated(False)
        self.set_app_paintable(False)
        self.set_skip_taskbar_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        css(self, "launcher-window")
        try:
            self.set_icon(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(BRAND_ASSETS / "macmenu-app.svg"), 64, 64, True
            ))
        except GLib.Error:
            self.log.warning("Could not load the MacMenu application icon")
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", self.on_focus_out)
        self.connect("delete-event", self.on_close)
        self.connect("destroy", lambda *_: self.cancel_focus_out())
        self.connect("destroy", self._stop_config_watch)

        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        surface.set_name("surface")
        self.add(surface)

        header = css(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9), "header")
        surface.pack_start(header, False, False, 0)

        self.brand_image = css(Gtk.Image(), "brand-mark")
        self.brand_image.set_tooltip_text("MacMenu — Linux application launcher")
        self.brand_image.get_accessible().set_name("MacMenu")
        header.pack_start(self.brand_image, False, False, 0)

        self.search = css(Gtk.SearchEntry(), "search-entry")
        self.search.set_placeholder_text("Search applications")
        self.search.set_activates_default(False)
        self.search.connect("search-changed", self.on_search)
        header.pack_start(self.search, True, True, 0)

        more_button = self.make_icon_button("view-more-symbolic", "More options", self.show_system_menu)
        header.pack_end(more_button, False, False, 0)

        middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        surface.pack_start(middle, True, True, 0)
        # One compact macOS-style navigation rail; no alternate Whisker UI.
        self.mac_rail = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "mac-rail")
        self.mac_rail.set_size_request(53, -1)
        middle.pack_start(self.mac_rail, False, False, 0)
        self.rail_buttons = {}
        self.rail_categories = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        rail_scroll = Gtk.ScrolledWindow()
        rail_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        rail_scroll.add(self.rail_categories)
        self.mac_rail.pack_start(rail_scroll, True, True, 0)

        right = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "content")
        middle.pack_start(right, True, True, 0)
        category_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        right.pack_start(category_bar, False, False, 0)
        self.content_heading = css(Gtk.Label(xalign=0), "content-title")
        category_bar.pack_start(self.content_heading, False, False, 0)
        category_bar.pack_start(Gtk.Box(), True, True, 0)
        self.count_label = css(Gtk.Label(xalign=1), "content-count")
        self.count_label.set_no_show_all(True)
        category_bar.pack_end(self.count_label, False, False, 0)
        panel = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "app-panel")
        right.pack_start(panel, True, True, 0)
        self.stack = Gtk.Stack()
        panel.pack_start(self.stack, True, True, 0)

        self.grid = Gtk.FlowBox()
        self.grid.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.grid.set_activate_on_single_click(True)
        self.grid.set_min_children_per_line(3)
        self.grid.set_max_children_per_line(4)
        self.grid.set_column_spacing(4)
        self.grid.set_row_spacing(2)
        self.grid.connect("child-activated", self.on_grid_activated)
        self.grid_scroll = Gtk.ScrolledWindow()
        self.grid_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.grid_scroll.add(self.grid)
        self.stack.add_named(self.grid_scroll, "apps")

        self.empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        self.empty.set_valign(Gtk.Align.CENTER)
        self.empty.set_halign(Gtk.Align.CENTER)
        self.empty.pack_start(icon("system-search-symbolic", 44), False, False, 0)
        self.empty_title = css(Gtk.Label(label="No applications found"), "empty-title")
        self.empty_hint = css(Gtk.Label(label="Try another search or category."), "empty-hint")
        self.empty.pack_start(self.empty_title, False, False, 0)
        self.empty.pack_start(self.empty_hint, False, False, 0)
        self.stack.add_named(self.empty, "empty")

        self.more_button = css(Gtk.Button(), "load-more")
        self.more_button.set_no_show_all(True)
        self.more_button.set_visible(False)
        self.more_button.set_halign(Gtk.Align.CENTER)
        self.more_button.connect("clicked", self.show_more)
        right.pack_start(self.more_button, False, False, 0)

        self.apply_theme()
        self._watch_config()
        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.connect("notify::gtk-theme-name", self.on_system_theme_changed)
        self.populate_categories()
        self.render()

    def make_icon_button(self, name: str, tooltip: str, callback) -> Gtk.Button:
        button = css(Gtk.Button(), "icon-button")
        button.add(icon(name))
        button.set_tooltip_text(tooltip)
        button.set_can_focus(True)
        button.connect("clicked", callback)
        return button

    def make_rail_button(self, name: str, label: str, callback) -> Gtk.Button:
        button = css(Gtk.Button(), "rail-button")
        theme = Gtk.IconTheme.get_default()
        if theme and not theme.has_icon(name):
            alternative = name.removesuffix("-symbolic")
            name = alternative if theme.has_icon(alternative) else "application-x-executable-symbolic"
        button.add(icon(name, 19))
        button.set_tooltip_text(label)
        button.get_accessible().set_name(label)
        button.connect("clicked", callback)
        return button

    def apply_theme(self) -> None:
        screen = Gdk.Screen.get_default()
        if self._css_provider is None:
            self._css_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_screen(
                screen, self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        preview_styles = "\n".join(
            f".theme-preview.preview-{name} {{ background-color: {colors['surface']}; "
            f"color: {colors['accent']}; border-color: {colors['line']}; }}"
            for name, colors in PALETTES.items()
        )
        self._css_provider.load_from_data(
            (STYLESHEET.format(**PALETTES[self.effective_theme()]) + preview_styles).encode()
        )
        # A single cached 26px bitmap per palette keeps every warm toggle free
        # of SVG decoding, while Light gets the necessary ink-on-light contrast.
        artwork = "macmenu-penguin-ink.svg" if self.effective_theme() in ("light", "glass-light", "aqua") else "macmenu-penguin.svg"
        if artwork not in self._brand_pixbufs:
            try:
                self._brand_pixbufs[artwork] = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(BRAND_ASSETS / artwork), 26, 26, True
                )
            except GLib.Error:
                self.brand_image.set_from_icon_name("start-here-symbolic", Gtk.IconSize.BUTTON)
                self.brand_image.set_pixel_size(26)
                return
        self.brand_image.set_from_pixbuf(self._brand_pixbufs[artwork])

    def effective_theme(self) -> str:
        if self.settings["theme"] != "system":
            return self.settings["theme"]
        gtk_settings = Gtk.Settings.get_default()
        name = gtk_settings.get_property("gtk-theme-name") if gtk_settings else ""
        return "dark" if "dark" in name.casefold() else "light"

    def on_system_theme_changed(self, _settings, _param) -> None:
        if self.settings["theme"] == "system":
            self.apply_theme()

    def _watch_config(self) -> None:
        """Update a resident launcher immediately when MacRice changes its theme."""
        try:
            self._config_monitor = Gio.File.new_for_path(str(config_path().parent)).monitor_directory(
                Gio.FileMonitorFlags.NONE, None,
            )
            self._config_monitor.connect("changed", self._on_config_changed)
        except GLib.Error as exc:
            self.log.warning("Cannot monitor MacMenu settings: %s", exc)

    def _on_config_changed(self, _monitor, file, other_file, _event) -> None:
        if not any(item and item.get_basename() == "settings.json" for item in (file, other_file)):
            return
        if self._config_reload_source:
            GLib.source_remove(self._config_reload_source)
        self._config_reload_source = GLib.timeout_add(90, self._reload_config_theme)

    def _reload_config_theme(self) -> bool:
        self._config_reload_source = 0
        new_theme = load()["theme"]
        if new_theme != self.settings["theme"]:
            self.settings["theme"] = new_theme
            self.apply_theme()
            self.update_theme_buttons()
        return GLib.SOURCE_REMOVE

    def _stop_config_watch(self, *_args) -> None:
        if self._config_reload_source:
            GLib.source_remove(self._config_reload_source)
            self._config_reload_source = 0
        if self._config_monitor:
            self._config_monitor.cancel()
            self._config_monitor = None

    def persist(self) -> None:
        try:
            save(self.settings)
        except OSError as exc:
            self.log.exception("Could not save preferences")
            self.show_error(f"Preferences could not be saved:\n{exc}")

    def populate_categories(self) -> None:
        selected = self.category
        for child in self.rail_categories.get_children():
            self.rail_categories.remove(child)
        self.rail_buttons.clear()
        available = {app.category for app in self.apps}
        for name in ORDER:
            if name not in ("Favorites", "Recent", "All Apps") and name not in available:
                continue
            rail_button = self.make_rail_button(
                CATEGORY_ICONS[name], name, lambda _, category=name: self.select_category(category)
            )
            self.rail_buttons[name] = rail_button
            self.rail_categories.pack_start(rail_button, False, False, 0)
        self.rail_categories.show_all()
        if selected not in self.rail_buttons:
            self.category = "All Apps"
        self.update_rail_selection()

    def update_rail_selection(self) -> None:
        for name, button in self.rail_buttons.items():
            context = button.get_style_context()
            if name == self.category:
                context.add_class("selected")
            else:
                context.remove_class("selected")

    def select_category(self, category: str) -> None:
        if category not in self.rail_buttons:
            return
        if self.category != category:
            self.category = category
            self.render()
        self.search.grab_focus()

    def show_system_menu(self, button: Gtk.Button) -> None:
        menu = Gtk.Menu()
        css(menu, "macmenu-popup")
        preferences = Gtk.MenuItem(label="Preferences…")
        preferences.connect("activate", lambda _: GLib.idle_add(self.open_preferences))
        menu.append(preferences)
        menu.append(Gtk.SeparatorMenuItem())
        actions = (
            ("Open Files", ["exo-open", "--launch", "FileManager"]),
            ("Open Terminal", ["exo-open", "--launch", "TerminalEmulator"]),
            ("System Settings", ["xfce4-settings-manager"]),
        )
        for label, command in actions:
            item = Gtk.MenuItem(label=label)
            item.connect("activate", lambda _, c=command: self.run_action(c))
            menu.append(item)
        menu.attach_to_widget(self, None)
        self._menu_open = True

        def close_menu(active_menu):
            self._menu_open = False
            active_menu.destroy()
            if not self.get_visible() and not self.settings["instant_toggle"]:
                GLib.idle_add(self.dispose_if_hidden)

        menu.connect("selection-done", close_menu)
        menu.show_all()
        menu.popup_at_widget(button, Gdk.Gravity.SOUTH_EAST, Gdk.Gravity.NORTH_EAST, None)

    def render(self) -> None:
        query = self.search.get_text()
        selection = (query, self.category)
        changed_selection = selection != self._last_selection
        selected = select_apps(
            self.apps, query, self.category, self.settings["favorites"], self.settings["recent"]
        )
        if changed_selection:
            # Show a modest catalog in full; reserve incremental creation for
            # genuinely large app lists, without a redundant sticky footer.
            self._render_limit = len(selected) if len(selected) <= 48 else self.PAGE_SIZE
            self._last_selection = selection
        self.content_heading.set_text(
            "Search results" if query else "All Applications" if self.category == "All Apps" else self.category
        )
        self.update_rail_selection()
        visible, remaining = visible_page(selected, self._render_limit)
        shown = len(visible)
        if changed_selection:
            self.grid.unselect_all()
        count = f"{shown} / {len(selected)}" if remaining else str(len(selected))
        self.count_label.set_text(f"{count} apps")
        self.count_label.set_visible(bool(query))
        self.more_button.set_visible(bool(remaining))
        if remaining:
            self.more_button.set_label(f"Show {min(self.PAGE_SIZE, remaining)} more")
        if not selected:
            self.render_grid([])
            if not query and self.category == "Favorites":
                self.empty_title.set_text("No favorites yet")
                self.empty_hint.set_text("Right-click an app and choose Add to Favorites.")
            elif not query and self.category == "Recent" and not self.settings["history_enabled"]:
                self.empty_title.set_text("Recent apps are off")
                self.empty_hint.set_text("Enable history in Preferences if you need it.")
            elif not query and self.category == "Recent":
                self.empty_title.set_text("Nothing opened yet")
                self.empty_hint.set_text("Apps you open from MacMenu will appear here.")
            else:
                self.empty_title.set_text("No applications found")
                self.empty_hint.set_text("Try a different search or category.")
            self.stack.set_visible_child_name("empty")
            return
        self.render_grid(visible)
        self.stack.set_visible_child_name("apps")
        if changed_selection:
            self.grid_scroll.get_vadjustment().set_value(0)

    def show_more(self, _button) -> None:
        self._render_limit += self.PAGE_SIZE
        self.render()

    def render_grid(self, apps: list[AppEntry]) -> None:
        pixels = {"small": 38, "normal": 46, "large": 54}[self.settings["icon_size"]]
        for index, app in enumerate(apps):
            if index == len(self._tile_pool):
                tile = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4), "app-tile")
                tile.set_size_request(106, 80)
                tile.set_halign(Gtk.Align.CENTER)
                image = app_icon(app, pixels)
                tile.pack_start(image, False, False, 0)
                label = css(Gtk.Label(label=app.name), "tile-label")
                label.set_max_width_chars(14)
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.set_justify(Gtk.Justification.CENTER)
                label.set_tooltip_text(app.name)
                tile.pack_start(label, False, False, 0)
                wrapper = Gtk.EventBox()
                wrapper.set_visible_window(False)
                wrapper.add(tile)
                wrapper.connect("button-press-event", lambda w, e: self.on_app_context_click(w, e, w.app_id))
                self.grid.add(wrapper)
                child = self.grid.get_children()[-1]
                child.connect("popup-menu", lambda w: self.on_app_context_keyboard(w, w.app_id))
                child.tile_icon = image
                child.tile_label = label
                child.tile_wrapper = wrapper
                child.app_id = None
                child.icon_pixels = None
                self._tile_pool.append(child)
                child.show_all()
            child = self._tile_pool[index]
            if child.app_id != app.app_id or child.icon_pixels != pixels:
                if app.icon:
                    child.tile_icon.set_from_gicon(app.icon, Gtk.IconSize.DIALOG)
                else:
                    child.tile_icon.set_from_icon_name("application-x-executable", Gtk.IconSize.BUTTON)
                child.tile_icon.set_pixel_size(pixels)
                child.tile_label.set_text(app.name)
                child.tile_label.set_tooltip_text(app.name)
                child.set_tooltip_text(f"{app.name} · Right-click for app actions")
                child.app_id = app.app_id
                child.tile_wrapper.app_id = app.app_id
                child.icon_pixels = pixels
            child.show()
        for child in self._tile_pool[len(apps):]:
            child.hide()
        # A user can page through hundreds of apps; retain at most two pages
        # after narrowing the result set, so the warm process stays modest.
        keep = max(self.PAGE_SIZE * 2, len(apps))
        while len(self._tile_pool) > keep:
            child = self._tile_pool.pop()
            self.grid.remove(child)

    def toggle_favorite(self, app: AppEntry) -> None:
        favorites = self.settings["favorites"]
        if app.app_id in favorites:
            favorites.remove(app.app_id)
        else:
            favorites.append(app.app_id)
        self.persist()
        self.render()

    def on_app_context_click(self, _widget, event, app_id: str) -> bool:
        if event.button != 3:
            return False
        self.show_app_menu(app_id, event)
        return True

    def on_app_context_keyboard(self, _widget, app_id: str) -> bool:
        self.show_app_menu(app_id)
        return True

    def show_app_menu(self, app_id: str, event=None, anchor=None) -> None:
        app = self.by_id.get(app_id)
        if app is None:
            return
        menu = Gtk.Menu()
        css(menu, "macmenu-popup")

        def add_item(text: str, callback) -> None:
            item = Gtk.MenuItem(label=text)
            item.connect("activate", lambda _: callback())
            menu.append(item)

        add_item("Open", lambda: self.launch(app_id))
        favorited = app_id in self.settings["favorites"]
        add_item(
            "Remove from Favorites" if favorited else "Add to Favorites",
            lambda: self.toggle_favorite(app),
        )
        if favorited:
            add_item("Move Favorite Up", lambda: self.reorder_favorite(app_id, -1))
            add_item("Move Favorite Down", lambda: self.reorder_favorite(app_id, 1))
        actions = app.launcher.list_actions() if hasattr(app.launcher, "list_actions") else []
        if actions:
            menu.append(Gtk.SeparatorMenuItem())
            for action_id in actions:
                label = app.launcher.get_action_name(action_id) or action_id
                add_item(label, lambda a=action_id: self.launch_desktop_action(app, a))
        menu.attach_to_widget(self, None)
        self._menu_open = True
        def close_menu(active_menu):
            self._menu_open = False
            active_menu.destroy()
            if not self.get_visible() and not self.settings["instant_toggle"]:
                GLib.idle_add(self.dispose_if_hidden)
        menu.connect("selection-done", close_menu)
        menu.show_all()
        if event is not None:
            menu.popup_at_pointer(event)
        else:
            menu.popup_at_widget(anchor or self, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def reorder_favorite(self, app_id: str, direction: int) -> None:
        self.settings["favorites"] = move_favorite(self.settings["favorites"], app_id, direction)
        self.persist()
        self.render()

    def launch_desktop_action(self, app: AppEntry, action_id: str) -> None:
        try:
            context = Gdk.Display.get_default().get_app_launch_context()
            app.launcher.launch_action(action_id, context)
        except (GLib.Error, OSError) as exc:
            self.log.exception("Desktop action failed")
            self.show_error(f"Could not run an action for {app.name}:\n{exc}")
            return
        self.dismiss()

    def on_search(self, _entry) -> None:
        self.render()

    def on_grid_activated(self, _grid, child) -> None:
        self.launch(child.app_id)

    def launch(self, app_id: str) -> None:
        app = self.by_id.get(app_id)
        if not app:
            return
        try:
            context = Gdk.Display.get_default().get_app_launch_context()
            started = app.launcher.launch([], context)
        except (GLib.Error, OSError) as exc:
            self.log.warning("Could not launch app: %s", app.app_id, exc_info=True)
            self.show_error(f"Could not open {app.name}:\n{exc}")
            return
        if not started:
            self.show_error(f"Could not open {app.name}.")
            return
        if self.settings["history_enabled"]:
            recent = self.settings["recent"]
            if app_id in recent:
                recent.remove(app_id)
            recent.insert(0, app_id)
            del recent[20:]
            self.persist()
        self.dismiss()

    def run_action(self, command: list[str]) -> None:
        if not shutil.which(command[0]):
            self.log.warning("System action unavailable: %s", command[0])
            self.show_error(f"{command[0]} is not installed on this system.")
            return
        try:
            subprocess.Popen(command, start_new_session=True)
        except OSError as exc:
            self.log.warning("System action failed: %s", command[0], exc_info=True)
            self.show_error(f"Could not run this action:\n{exc}")
            return
        self.dismiss()

    def show_error(self, message: str) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=self._preferences_dialog or self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.CLOSE, text="MacMenu · Action failed",
        )
        dialog.format_secondary_text(message)
        was_open = self._preferences_open
        self._preferences_open = True
        dialog.run()
        dialog.destroy()
        self._preferences_open = was_open

    def confirm(self, title: str, description: str, action: str, parent=None) -> bool:
        dialog = Gtk.MessageDialog(
            transient_for=parent or self, modal=True, message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.NONE, text=title,
        )
        dialog.format_secondary_text(description)
        cancel = dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button(action, Gtk.ResponseType.ACCEPT)
        cancel.grab_focus()
        approved = dialog.run() == Gtk.ResponseType.ACCEPT
        dialog.destroy()
        return approved

    def open_preferences(self, _button=None) -> None:
        if self._preferences_open:
            return
        self._preferences_open = True
        dialog = Gtk.Dialog(title="MacMenu Preferences", transient_for=self, modal=True)
        self._preferences_dialog = dialog
        css(dialog, "settings-dialog")
        dialog.add_button("Done", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(510, 532)
        content = dialog.get_content_area()
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        shell.set_border_width(14)
        content.pack_start(shell, True, True, 0)
        shell.pack_start(css(Gtk.Label(label="Preferences", xalign=0), "settings-title"), False, False, 0)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        stack.set_transition_duration(120)
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(stack)
        switcher.set_halign(Gtk.Align.START)
        shell.pack_start(switcher, False, False, 0)
        shell.pack_start(stack, True, True, 0)

        def page(name: str, title: str) -> Gtk.Box:
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            container.set_border_width(3)
            card = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "settings-card")
            container.pack_start(card, False, False, 0)
            scroll.add(container)
            stack.add_titled(scroll, name, title)
            return card

        appearance = page("appearance", "Appearance")
        privacy = page("privacy", "Privacy & Data")

        def setting_row(card: Gtk.Box, title: str, description: str, widget: Gtk.Widget) -> None:
            if card.get_children():
                card.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 0)
            row = css(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12), "setting-row")
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            labels.pack_start(css(Gtk.Label(label=title, xalign=0), "setting-title"), False, False, 0)
            help_label = css(Gtk.Label(label=description, xalign=0), "setting-help")
            help_label.set_line_wrap(True)
            help_label.set_max_width_chars(32)
            labels.pack_start(help_label, False, False, 0)
            row.pack_start(labels, True, True, 0)
            widget.set_valign(Gtk.Align.CENTER)
            row.pack_end(widget, False, False, 0)
            card.pack_start(row, False, False, 0)

        theme_row = css(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "setting-row")
        theme_row.pack_start(css(Gtk.Label(label="Color theme", xalign=0), "setting-title"), False, False, 0)
        theme_row.pack_start(css(Gtk.Label(label="Auto follows the XFCE appearance.", xalign=0), "setting-help"), False, False, 0)
        theme_choices = css(Gtk.Grid(column_spacing=5, row_spacing=5, column_homogeneous=True), "theme-choices")
        self._theme_buttons = {}
        for index, (theme_id, name) in enumerate(THEMES):
            button = css(Gtk.Button(), "theme-choice")
            preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            preview = css(Gtk.Label(label="●" if theme_id != "system" else "◐"), "theme-preview")
            css(preview, f"preview-{theme_id}")
            preview_box.pack_start(preview, False, False, 0)
            preview_box.pack_start(css(Gtk.Label(label=name), "theme-name"), False, False, 0)
            button.add(preview_box)
            button.set_tooltip_text(f"Use {name} theme")
            button.get_accessible().set_name(f"{name} theme")
            button.connect("clicked", self.select_theme, theme_id)
            theme_choices.attach(button, index % 3, index // 3, 1, 1)
            self._theme_buttons[theme_id] = button
        theme_row.pack_start(theme_choices, False, False, 0)
        appearance.pack_start(theme_row, False, False, 0)
        self.update_theme_buttons()

        for key, label, description, options in (
            ("icon_size", "Icon size", "Scale app icons in the launcher.",
             [("small", "Small"), ("normal", "Regular"), ("large", "Large")]),
            ("position", "Menu position", "Where the launcher opens.",
             [("panel", "Near pointer"), ("top-left", "Top left"), ("bottom-left", "Bottom left")]),
        ):
            combo = Gtk.ComboBoxText()
            for option_id, option_label in options:
                combo.append(option_id, option_label)
            combo.set_active_id(self.settings[key])
            combo.connect("changed", self.on_preference, key)
            setting_row(appearance, label, description, combo)

        background_switch = Gtk.Switch()
        background_switch.set_active(self.settings["instant_toggle"])
        background_switch.connect("notify::active", self.on_background_preference)
        setting_row(appearance, "Instant reopening", "Keep the small launcher ready in memory.", background_switch)

        history_switch = Gtk.Switch()
        history_switch.set_active(self.settings["history_enabled"])
        history_switch.connect("notify::active", self.on_history_preference)
        setting_row(privacy, "Recent apps", "Save launches locally; switching off clears them.", history_switch)

        clear_button = Gtk.Button(label="Clear history")
        self._history_clear_button = clear_button
        clear_button.set_sensitive(bool(self.settings["recent"]))
        clear_button.connect("clicked", lambda _: self.clear_history(clear_button))
        setting_row(privacy, "History", "Remove recently opened apps.", clear_button)

        backup_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=7)
        export_button = Gtk.Button(label="Export…")
        import_button = Gtk.Button(label="Import…")
        export_button.connect("clicked", lambda _: self.export_settings(dialog))
        import_button.connect("clicked", lambda _: self.import_settings(dialog))
        backup_actions.pack_start(export_button, False, False, 0)
        backup_actions.pack_start(import_button, False, False, 0)
        setting_row(privacy, "Backup", "Save favorites and preferences as JSON.", backup_actions)

        reset_button = css(Gtk.Button(label="Reset…"), "danger-action")
        reset_button.connect("clicked", lambda _: self.reset_settings(dialog))
        setting_row(privacy, "Reset preferences", "Restore defaults, clear favorites and history.", reset_button)
        stack.set_visible_child_name("appearance")
        dialog.show_all()
        dialog.run()
        dialog.destroy()
        self._theme_buttons = {}
        self._preferences_dialog = None
        self._preferences_open = False
        self.search.grab_focus()

    def on_history_preference(self, switch: Gtk.Switch, _param) -> None:
        value = switch.get_active()
        if value == self.settings["history_enabled"]:
            return
        if not value and self.settings["recent"] and not self.confirm(
            "Turn off recent apps?",
            "Your saved launch history will be permanently cleared.",
            "Turn Off & Clear", self._preferences_dialog,
        ):
            switch.set_active(True)
            return
        self.settings["history_enabled"] = value
        if not value:
            self.settings["recent"] = []
            self._history_clear_button.set_sensitive(False)
        self.persist()
        self.render()

    def clear_history(self, button: Gtk.Button) -> None:
        if not self.settings["recent"]:
            return
        if self.confirm("Clear recent apps?", "This removes your saved MacMenu launch history.",
                        "Clear History", self._preferences_dialog):
            self.settings["recent"] = []
            self.persist()
            button.set_sensitive(False)
            self.render()

    def export_settings(self, parent: Gtk.Dialog) -> None:
        picker = Gtk.FileChooserDialog(
            title="Export MacMenu Preferences", transient_for=parent,
            action=Gtk.FileChooserAction.SAVE,
        )
        picker.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Export", Gtk.ResponseType.ACCEPT)
        picker.set_current_name("macmenu-preferences.json")
        picker.set_do_overwrite_confirmation(True)
        target = Path(picker.get_filename()) if picker.run() == Gtk.ResponseType.ACCEPT else None
        picker.destroy()
        if target is not None:
            try:
                save_backup(self.settings, target)
            except OSError as exc:
                self.log.exception("Preference export failed")
                self.show_error(f"Could not export preferences:\n{exc}")

    def import_settings(self, parent: Gtk.Dialog) -> None:
        picker = Gtk.FileChooserDialog(
            title="Import MacMenu Preferences", transient_for=parent,
            action=Gtk.FileChooserAction.OPEN,
        )
        picker.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Import", Gtk.ResponseType.ACCEPT)
        filter_json = Gtk.FileFilter()
        filter_json.set_name("JSON backups")
        filter_json.add_pattern("*.json")
        picker.add_filter(filter_json)
        source = Path(picker.get_filename()) if picker.run() == Gtk.ResponseType.ACCEPT else None
        picker.destroy()
        if source is None:
            return
        try:
            with source.open("rb") as file:
                raw = file.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise ValueError("File too large (128 KiB maximum).")
            restored = parse_backup(raw.decode("utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            self.show_error(f"Could not read the backup:\n{exc}")
            return
        if not self.confirm(
            "Replace your preferences?",
            "The backup replaces your theme, favorites, and history. "
            "Export your current settings first if you want to keep them.",
            "Import & Replace", parent,
        ):
            return
        self.settings = restored
        self.persist()
        self.apply_theme()
        self.get_application().sync_background_hold(self.settings["instant_toggle"])
        self.render()
        self.position_window()
        parent.response(Gtk.ResponseType.CLOSE)

    def reset_settings(self, parent: Gtk.Dialog) -> None:
        if not self.confirm(
            "Reset MacMenu?",
            "All favorites, recent apps, and personal settings will be removed.",
            "Reset Everything", parent,
        ):
            return
        self.settings = sanitize({})
        self.persist()
        self.apply_theme()
        self.get_application().sync_background_hold(self.settings["instant_toggle"])
        self.render()
        self.position_window()
        parent.response(Gtk.ResponseType.CLOSE)

    def on_preference(self, combo: Gtk.ComboBoxText, key: str) -> None:
        value = combo.get_active_id()
        if value is None or self.settings[key] == value:
            return
        self.settings[key] = value
        self.persist()
        if key == "theme":
            self.apply_theme()
        elif key == "icon_size":
            self.render()
        else:
            self.position_window()

    def select_theme(self, _button: Gtk.Button, theme: str) -> None:
        if theme not in dict(THEMES) or self.settings["theme"] == theme:
            return
        self.settings["theme"] = theme
        self.persist()
        self.apply_theme()
        self.update_theme_buttons()

    def update_theme_buttons(self) -> None:
        for theme, button in getattr(self, "_theme_buttons", {}).items():
            context = button.get_style_context()
            if theme == self.settings["theme"]:
                context.add_class("selected")
            else:
                context.remove_class("selected")

    def on_background_preference(self, switch: Gtk.Switch, _param) -> None:
        value = switch.get_active()
        if self.settings["instant_toggle"] != value:
            self.settings["instant_toggle"] = value
            self.persist()
            self.get_application().sync_background_hold(value)

    def position_window(self) -> None:
        display = Gdk.Display.get_default()
        position = self.settings["position"]
        pointer_position = None
        if position == "panel" and display.get_default_seat():
            pointer = display.get_default_seat().get_pointer()
            if pointer:
                _, px, py = pointer.get_position()
                pointer_position = (px, py)
        monitor = display.get_monitor_at_point(*pointer_position) if pointer_position else None
        monitor = monitor or display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return
        bounds = monitor.get_workarea()
        width = max(420, min(572, bounds.width - 28))
        height = max(350, min(486, bounds.height - 28))
        self.resize(width, height)
        x = bounds.x + 14
        y = bounds.y + 14
        if position == "bottom-left":
            y = bounds.y + bounds.height - height - 14
        elif position == "panel" and pointer_position:
            px, py = pointer_position
            x = max(bounds.x + 14, min(px - 30, bounds.x + bounds.width - width - 14))
            if py >= bounds.y + bounds.height / 2:
                y = bounds.y + bounds.height - height - 14
        self.move(x, max(bounds.y, y))

    def show_launcher(self) -> None:
        self.cancel_focus_out()
        if self.search.get_text():
            self.search.set_text("")
        self.show_all()
        # show_all() can reveal pooled hidden children; restore the visible set
        # before GTK paints the frame.
        self.render()
        self.position_window()
        self.present()
        self.search.grab_focus()

    def refresh_catalog(self) -> None:
        self.apps = installed_apps()
        self.by_id = {app.app_id: app for app in self.apps}
        for child in self._tile_pool:
            child.app_id = None
        self.populate_categories()
        self.render()

    def on_key_press(self, _window, event) -> bool:
        if event.keyval == Gdk.KEY_Escape and not self._preferences_open:
            self.dismiss()
            return True
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval in (Gdk.KEY_r, Gdk.KEY_R):
                self.refresh_catalog()
                return True
            if event.keyval == Gdk.KEY_k:
                self.search.grab_focus()
                self.search.select_region(0, -1)
                return True
            if event.keyval == Gdk.KEY_comma:
                self.open_preferences()
                return True
        if event.state & Gdk.ModifierType.MOD1_MASK:
            category = {
                Gdk.KEY_1: "Favorites", Gdk.KEY_2: "Recent", Gdk.KEY_3: "All Apps",
            }.get(event.keyval)
            if category:
                self.select_category(category)
                return True
        if event.keyval == Gdk.KEY_Down and self.search.is_focus():
            first = self.grid.get_child_at_index(0) if self.stack.get_visible_child_name() == "apps" else None
            if first:
                first.grab_focus()
                return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and self.search.is_focus():
            selected = select_apps(self.apps, self.search.get_text(), self.category, self.settings["favorites"], self.settings["recent"])
            if selected:
                self.launch(selected[0].app_id)
            return True
        return False

    def on_focus_out(self, _window, _event) -> bool:
        if self.get_visible() and not self._preferences_open and not self._menu_open:
            # The XFCE Super-key shortcut can briefly steal focus before its
            # separate process delivers --toggle. Let the explicit command
            # win over the implicit click-away dismissal.
            self.cancel_focus_out()
            self._focus_out_source = GLib.timeout_add(350, self.dismiss_if_unfocused)
        return False

    def cancel_focus_out(self) -> None:
        if self._focus_out_source is not None:
            GLib.source_remove(self._focus_out_source)
            self._focus_out_source = None

    def dismiss_if_unfocused(self) -> bool:
        self._focus_out_source = None
        if self.get_visible() and not self.is_active() and not self._preferences_open and not self._menu_open:
            self.dismiss()
        return False

    def dismiss(self) -> None:
        self.cancel_focus_out()
        self.hide()
        if not self.settings["instant_toggle"]:
            GLib.idle_add(self.dispose_if_hidden)

    def dispose_if_hidden(self) -> bool:
        if not self.get_visible() and not self._preferences_open and not self._menu_open:
            self.destroy()
        return False

    def on_close(self, _window, _event) -> bool:
        self.dismiss()
        return True


class MacMenu(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.xfce.MacMenu",
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.window = None
        self._held = False
        self._refresh_source = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

    def ensure_window(self) -> LauncherWindow:
        if self.window is None:
            self.window = LauncherWindow(self)
            self.window.connect("destroy", self.on_window_destroyed)
            if not getattr(self, "_monitor_connected", False):
                Gio.AppInfoMonitor.get().connect("changed", self.on_apps_changed)
                self._monitor_connected = True
        self.sync_background_hold(self.window.settings["instant_toggle"])
        return self.window

    def sync_background_hold(self, enabled: bool) -> None:
        if enabled and not self._held:
            self.hold()
            self._held = True
        elif not enabled and self._held:
            self.release()
            self._held = False

    def on_window_destroyed(self, window: LauncherWindow) -> None:
        if self.window is window:
            self.window = None

    def do_activate(self) -> None:
        self.perform("toggle")

    def do_command_line(self, command_line) -> int:
        try:
            action = resolve_command(list(command_line.get_arguments())[1:])
        except ValueError as exc:
            command_line.printerr_literal(f"{exc}\n")
            return 2
        if action == "version":
            command_line.print_literal(f"MacMenu {__version__}\n")
            return 0
        self.perform(action)
        return 0

    def perform(self, action: str) -> None:
        if action in ("hide", "quit") and self.window and self.window._preferences_dialog:
            # A modal Gtk.Dialog runs a nested event loop; close it first so
            # the launcher cannot leave an orphaned dialog behind.
            self.window._preferences_dialog.response(Gtk.ResponseType.CLOSE)
            GLib.idle_add(self.perform, action)
            return
        if action == "quit":
            if self.window:
                self.window.destroy()
                self.window = None
            if self._held:
                self.release()
                self._held = False
            self.quit()
            return
        if action == "hide":
            if self.window:
                self.window.dismiss()
            return
        window = self.ensure_window()
        if action == "toggle" and window.get_visible() and not window._preferences_open:
            window.dismiss()
        elif window._preferences_open and window._preferences_dialog:
            window._preferences_dialog.present()
        else:
            window.show_launcher() if not window.get_visible() else window.present()
            if action == "preferences":
                GLib.idle_add(window.open_preferences)

    def on_apps_changed(self, _monitor) -> None:
        if self.window:
            if self._refresh_source:
                GLib.source_remove(self._refresh_source)
            self._refresh_source = GLib.timeout_add(300, self.refresh_catalog_after_change)

    def refresh_catalog_after_change(self) -> bool:
        self._refresh_source = None
        if self.window:
            self.window.refresh_catalog()
        return False


def main() -> int:
    setup_logging()
    return MacMenu().run(sys.argv)
