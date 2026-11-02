"""RiceHub: a native, on-demand XFCE rice gallery and recovery workbench.

No extra daemon, browser, compositor, root privileges or hidden profile writes.
The working macOS implementation is shared with MacRice. Windows 7 and
Windows 10 also offer real, user-local XFCE/X11 appearance profiles.
"""

from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path

from .hub_art import aspect_fill
from .hub_catalog import FAMILIES, FAMILY_BY_KEY, recent_backups, search_families


HUB_VERSION = "0.6.0rc1"

# A restrained native palette. All GTK CSS colors and font choices live here.
TOKENS = {
    "window": "#141b25", "sidebar": "#101721", "surface": "#1c2734",
    "surface_alt": "#233142", "hover": "#293c51", "active": "#304a64",
    "border": "#344658", "text": "#f3f7fc", "muted": "#a7b8ca",
    "quiet": "#7f95ad", "accent": "#9bcafa", "accent_ink": "#17283a",
    "success": "#a2d7bf", "warning": "#eec691", "error": "#ffaaa5",
    "preview_veil": "rgba(16,23,33,.91)", "font": "Inter, sans-serif",
}

CSS = """/* RiceHub native GTK3 app screen — measured, accessible, low-motion. */
#ricehub-window {{ background: {window}; color: {text}; }}
#ricehub-sidebar {{ background: {sidebar}; border-right: 1px solid {border}; }}
#ricehub-content {{ background: {window}; }}
.hub-brand {{ color: {text}; font-family: {font}; font-size: 20px; font-weight: 700; }}
.hub-overline {{ color: {quiet}; font-size: 11px; }}
.hub-header {{ color: {text}; font-family: {font}; font-size: 25px; font-weight: 700; }}
.hub-section {{ color: {text}; font-family: {font}; font-size: 16px; font-weight: 700; }}
.hub-title {{ color: {text}; font-family: {font}; font-size: 14px; font-weight: bold; }}
.hub-body {{ color: {muted}; font-family: {font}; font-size: 12px; }}
.hub-hint {{ color: {quiet}; font-family: {font}; font-size: 11px; }}
.hub-good {{ color: {success}; font-size: 11px; font-weight: bold; }}
.hub-soon {{ color: {warning}; font-size: 11px; font-weight: bold; }}
.hub-error {{ color: {error}; font-size: 12px; }}
.hub-metric {{ color: {text}; font-family: {font}; font-size: 12px; }}
.hub-status {{ color: {muted}; font-size: 11px; }}
.hub-card {{ background: {surface}; border: 1px solid {border}; border-radius: 13px; padding: 13px; }}
.hub-info {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 11px; padding: 13px; }}
.hub-preview-footer {{ background: {preview_veil}; padding: 14px 17px; }}
.hub-preview-frame {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 14px; }}
.hub-placeholder {{ color: {muted}; font-family: {font}; font-size: 14px; }}
button.hub-nav, button.hub-card-button, button.hub-action, button.hub-primary {{
  background-image: none; box-shadow: none; border-radius: 9px; color: {text};
  border: 1px solid transparent; padding: 9px 12px; min-height: 34px;
}}
button.hub-nav {{ background-color: transparent; }}
button.hub-nav:hover, button.hub-card-button:hover {{ background: {hover}; }}
button.hub-nav.hub-selected {{ background: {active}; color: {text}; }}
button.hub-card-button {{ background: {surface}; border-color: {border}; padding: 14px; }}
button.hub-card-button.hub-selected {{ border-color: {accent}; background: {surface_alt}; }}
button.hub-action {{ background: {surface_alt}; border-color: {border}; }}
button.hub-action:hover {{ background: {hover}; }}
button.hub-primary {{ background: {accent}; color: {accent_ink}; font-weight: bold; }}
button.hub-primary:hover {{ background: {success}; color: {accent_ink}; }}
button:focus {{ outline: 2px solid {accent}; outline-offset: 1px; }}
button:disabled {{ opacity: .45; }}
entry, combobox button {{ background: {surface_alt}; color: {text}; border: 1px solid {border};
  border-radius: 8px; padding: 7px 9px; min-height: 27px; }}
entry:focus {{ border-color: {accent}; }}
scrolledwindow, viewport {{ background: transparent; border: none; }}
""".format(**TOKENS).encode("utf-8")


def _activate_hub_window(application, windows, factory) -> bool:
    """Never leave a registered but invisible Gtk.ApplicationWindow behind.

    Gtk.ApplicationWindow registers with the primary GApplication in its base
    constructor. If building the rest of the interface raises, GTK can retain
    that hidden window and its D-Bus name indefinitely. Subsequent launches
    silently forward to the broken primary instance and return success.
    """
    try:
        if windows:
            windows[0].present()
            return True
        window = factory(application)
        windows.append(window)
        window.connect("destroy", lambda *_: windows.clear())
        window.show_all()
        window._select_family(window._selected)
        window._filter_families()
        return True
    except Exception:
        traceback.print_exc()
        for registered in application.get_windows():
            try:
                registered.destroy()
            except Exception:
                traceback.print_exc()
        windows.clear()
        application.quit()
        return False


def run() -> int:
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("RiceHub needs a graphical XFCE session.", file=__import__("sys").stderr)
        return 1
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk
    except (ImportError, ValueError) as exc:
        print(f"RiceHub needs GTK3/PyGObject: {exc}", file=__import__("sys").stderr)
        return 1

    from .cli import open_component
    from .environment import detect, installed_components
    from .installer import InstallOptions, install, project_root
    from .performance import PROFILES as PERFORMANCE_PROFILES, apply_profile, measure_processes
    from .rice import STYLES, apply, plan, restore
    from .windows7_proto import install_css as install_windows7_css, teaser as windows7_teaser, show_dialog as show_windows7
    from .windows10_proto import install_css as install_windows10_css, teaser as windows10_teaser, show_dialog as show_windows10
    from .concept_rices import install_css as install_concepts_css, teaser as concept_teaser, show_dialog as show_concept

    def cls(widget, name):
        widget.get_style_context().add_class(name)
        return widget

    def label(value, style="hub-body", wrap=False):
        widget = cls(Gtk.Label(label=value, xalign=0), style)
        widget.set_line_wrap(wrap)
        widget.set_selectable(False)
        return widget

    def action(value, cb, primary=False):
        button = cls(Gtk.Button(label=value), "hub-primary" if primary else "hub-action")
        button.connect("clicked", cb)
        button.get_accessible().set_name(value)
        return button

    def vertical(spacing=10):
        return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)

    def horizontal(spacing=10):
        return Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)

    class HubWindow(Gtk.ApplicationWindow):
        def __init__(self, application):
            super().__init__(application=application, title="RiceHub — XFCE Rices")
            self.set_name("ricehub-window")
            self.set_default_size(1060, 720)
            self.set_size_request(760, 510)
            self.set_position(Gtk.WindowPosition.CENTER)
            self._busy = False
            self._selected = "macos"
            self._active_page = "discover"
            self._nav_buttons = {}
            self._family_buttons = {}
            self._component_buttons = {}
            self._wallpaper_cache = {}
            self._preview_style = "night"
            self._preview_rendered = None
            try:
                self.set_icon_from_file(str(project_root() / "assets/ricehub-symbolic.svg"))
            except (OSError, GLib.Error):
                pass

            layout = horizontal(0)
            self.add(layout)
            self._build_sidebar(layout)
            area = vertical(0)
            area.set_name("ricehub-content")
            layout.pack_start(area, True, True, 0)
            self.pages = Gtk.Stack()
            self.pages.set_transition_type(Gtk.StackTransitionType.NONE)
            area.pack_start(self.pages, True, True, 0)
            self._build_discover()
            self._build_desktop()
            self._build_components()
            self._build_performance()
            self._build_backups()
            self._build_roadmap()

            footer = cls(horizontal(9), "hub-info")
            footer.set_margin_start(20)
            footer.set_margin_end(20)
            footer.set_margin_bottom(12)
            self.feedback = label("Ready. No settings change until you confirm.", "hub-status", True)
            footer.pack_start(self.feedback, True, True, 0)
            area.pack_start(footer, False, False, 0)
            self.connect("key-press-event", self._key)
            self._switch_page("discover")
            self._select_family("macos")
            self._refresh_system()

        def _build_sidebar(self, layout):
            side = vertical(16)
            side.set_name("ricehub-sidebar")
            side.set_size_request(206, -1)
            side.set_margin_top(23)
            side.set_margin_bottom(18)
            side.set_margin_start(14)
            side.set_margin_end(14)
            layout.pack_start(side, False, False, 0)

            brand = horizontal(11)
            symbol = project_root() / "assets/ricehub-symbolic.svg"
            if symbol.is_file():
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(symbol), 36, 36, True)
                    brand.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
                except GLib.Error:
                    pass
            title = vertical(2)
            title.pack_start(label("RiceHub", "hub-brand"), False, False, 0)
            title.pack_start(label("XFCE desktop studio", "hub-hint"), False, False, 0)
            brand.pack_start(title, True, True, 0)
            side.pack_start(brand, False, False, 6)

            for key, name, symbol in (
                ("discover", "Discover rices", "view-grid-symbolic"),
                ("desktop", "My desktop", "video-display-symbolic"),
                ("components", "Components", "applications-system-symbolic"),
                ("performance", "Performance", "utilities-system-monitor-symbolic"),
                ("backups", "Backups & restore", "document-revert-symbolic"),
                ("roadmap", "What's next", "view-list-symbolic"),
            ):
                button = cls(Gtk.Button(), "hub-nav")
                contents = horizontal(11)
                icon = Gtk.Image.new_from_icon_name(symbol, Gtk.IconSize.MENU)
                contents.pack_start(icon, False, False, 0)
                contents.pack_start(label(name, "hub-title"), True, True, 0)
                button.add(contents)
                button.get_accessible().set_name(name)
                button.connect("clicked", lambda _button, page=key: self._switch_page(page))
                side.pack_start(button, False, False, 0)
                self._nav_buttons[key] = button

            side.pack_start(Gtk.Box(), True, True, 0)
            side.pack_start(label(f"RiceHub {HUB_VERSION}", "hub-hint"), False, False, 0)
            side.pack_start(label("Locally managed. No telemetry.", "hub-hint"), False, False, 0)

        def _page(self, key, title, intro):
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            body = vertical(18)
            for side in ("start", "end"):
                getattr(body, "set_margin_" + side)(28)
            body.set_margin_top(27)
            body.set_margin_bottom(30)
            body.pack_start(label(title, "hub-header"), False, False, 0)
            body.pack_start(label(intro, "hub-body", True), False, False, 0)
            scroll.add(body)
            self.pages.add_named(scroll, key)
            return body

        def _build_discover(self):
            body = self._page("discover", "Choose your desktop", "One lightweight XFCE system, different familiar interfaces.")
            self.preview = cls(vertical(0), "hub-preview-frame")
            body.pack_start(self.preview, False, False, 0)
            self.preview_stack = Gtk.Stack()
            self.preview_stack.set_transition_type(Gtk.StackTransitionType.NONE)
            canvas = Gtk.DrawingArea()
            canvas.set_size_request(-1, 190)
            canvas.connect("size-allocate", self._resize_wallpaper)
            image_layer = Gtk.Overlay()
            image_layer.add(canvas)
            self.preview_image = Gtk.Image()
            self.preview_image.set_halign(Gtk.Align.FILL)
            self.preview_image.set_valign(Gtk.Align.FILL)
            image_layer.add_overlay(self.preview_image)
            self.aero_preview_bar = cls(horizontal(8), "w7-taskbar")
            self.aero_preview_bar.set_valign(Gtk.Align.END)
            aero_icon = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(project_root() / "assets/aero-penguin.svg"), 25, 25, True))
            self.aero_preview_bar.pack_start(aero_icon, False, False, 0)
            self.aero_preview_bar.pack_start(label("Start    Files    Browser    Terminal", "w7-clock"), False, False, 0)
            image_layer.add_overlay(self.aero_preview_bar)
            self.preview_stack.add_named(image_layer, "macos")
            install_windows7_css(Gtk, Gdk)
            self.preview_stack.add_named(windows7_teaser(Gtk), "windows7")
            install_windows10_css(Gtk, Gdk)
            self.preview_stack.add_named(windows10_teaser(Gtk), "windows10")
            install_concepts_css(Gtk, Gdk)
            for concept_key in ("winxp", "winclassic", "chromeos", "frutiger"):
                self.preview_stack.add_named(concept_teaser(Gtk, concept_key), concept_key)
            placeholder = vertical(9)
            placeholder.set_valign(Gtk.Align.CENTER)
            placeholder.set_halign(Gtk.Align.CENTER)
            placeholder.set_size_request(-1, 190)
            placeholder.pack_start(label("Preview in development", "hub-section"), False, False, 0)
            placeholder.pack_start(label("This Rice is not available for installation yet.", "hub-placeholder"), False, False, 0)
            self.preview_stack.add_named(placeholder, "future")
            self.preview.pack_start(self.preview_stack, False, False, 0)
            summary = cls(vertical(4), "hub-preview-footer")
            self.preview_title = label("Aurora collection", "hub-section")
            self.preview_description = label("", "hub-body", True)
            summary.pack_start(self.preview_title, False, False, 0)
            summary.pack_start(self.preview_description, False, False, 0)
            self.preview.pack_start(summary, False, False, 0)

            controls = horizontal(10)
            body.pack_start(controls, False, False, 0)
            self.style_picker = Gtk.ComboBoxText()
            self._rebuilding_picker = False
            for key in FAMILY_BY_KEY["macos"].styles:
                style = STYLES[key]
                self.style_picker.append(key, style.name)
            self.style_picker.set_active_id("night")
            self.style_picker.set_tooltip_text("Choose a complete desktop appearance")
            self.style_picker.connect("changed", self._on_style_changed)
            controls.pack_start(self.style_picker, True, True, 0)
            self.plan_button = action("Check requirements", lambda _: self._plan_selected())
            controls.pack_start(self.plan_button, False, False, 0)
            self.apply_button = action("Apply rice", lambda _: self._plan_selected(apply_after=True), True)
            controls.pack_start(self.apply_button, False, False, 0)
            self.prototype_button = action("Explore read-only preview", lambda _: self._show_prototype())
            self.prototype_button.set_no_show_all(True)
            controls.pack_start(self.prototype_button, False, False, 0)
            self.future_note = label("Concept preview only — no settings are changed.", "hub-soon")
            self.future_note.set_no_show_all(True)
            body.pack_start(self.future_note, False, False, 0)

            finder = horizontal(10)
            body.pack_start(finder, False, False, 0)
            self.search = Gtk.SearchEntry()
            self.search.set_placeholder_text("Find a desktop style")
            self.search.get_accessible().set_name("Search desktop styles")
            self.search.connect("search-changed", self._filter_families)
            finder.pack_start(self.search, True, True, 0)

            self.gallery = Gtk.FlowBox()
            self.gallery.set_selection_mode(Gtk.SelectionMode.NONE)
            self.gallery.set_min_children_per_line(1)
            self.gallery.set_max_children_per_line(2)
            self.gallery.set_column_spacing(11)
            self.gallery.set_row_spacing(11)
            body.pack_start(self.gallery, False, False, 0)
            for family in FAMILIES:
                self._family_card(family)
            self.empty = label("Nothing matches. Try a different name or filter.", "hub-hint")
            self.empty.set_no_show_all(True)
            body.pack_start(self.empty, False, False, 0)

        def _family_card(self, family):
            button = cls(Gtk.Button(), "hub-card-button")
            button.set_size_request(250, 95)
            content = vertical(6)
            header = horizontal(9)
            header.pack_start(label(family.title, "hub-title"), True, True, 0)
            header.pack_start(label("Available" if family.available else
                                    "Interactive prototype" if family.prototype else "Coming soon",
                                    "hub-good" if family.available else "hub-soon"), False, False, 0)
            content.pack_start(header, False, False, 0)
            content.pack_start(label(family.subtitle, "hub-body"), False, False, 0)
            button.add(content)
            button.get_accessible().set_name(
                f"{family.title} — " + ("available" if family.available else
                                       "interactive preview only" if family.prototype else "coming soon"))
            button.connect("clicked", lambda _: self._select_family(family.key))
            self.gallery.add(button)
            self._family_buttons[family.key] = button

        def _build_desktop(self):
            body = self._page("desktop", "Your current desktop", "Inspect the current appearance without changing any settings.")
            self.desktop_state = cls(vertical(10), "hub-card")
            body.pack_start(self.desktop_state, False, False, 0)
            self.desktop_fields = {}
            for key, title in (("desktop", "Desktop"), ("gtk_theme", "GTK theme"),
                               ("window_theme", "Window borders"), ("icon_theme", "Icons"),
                               ("cursor_theme", "Cursor"), ("font", "Font"),
                               ("plank_theme", "Plank")):
                row = horizontal(12)
                row.pack_start(label(title, "hub-body"), True, True, 0)
                value = label("Checking…", "hub-metric")
                row.pack_start(value, False, False, 0)
                self.desktop_state.pack_start(row, False, False, 0)
                self.desktop_fields[key] = value
            refresh = action("Refresh desktop status", lambda _: self._refresh_system())
            body.pack_start(refresh, False, False, 0)
            tip = cls(vertical(5), "hub-info")
            tip.pack_start(label("Your current settings stay yours.", "hub-section"), False, False, 0)
            tip.pack_start(label("Applying a rice creates a private snapshot. Restore can preserve preferences you changed afterward.",
                                 "hub-body", True), False, False, 0)
            body.pack_start(tip, False, False, 0)

        def _build_components(self):
            body = self._page("components", "Desktop components", "Start or toggle the tools already installed on your system.")
            section = cls(vertical(10), "hub-card")
            body.pack_start(section, False, False, 0)
            self.component_state = {}
            for name, key, description in (
                ("MacMenu", "menu", "Search and launch applications"),
                ("Control Center", "center", "Network, audio and quick actions"),
                ("MacBar", "bar", "Native top panel"),
                ("Plank", "dock", "Existing bottom dock"),
            ):
                row = horizontal(10)
                text = vertical(3)
                text.pack_start(label(name, "hub-title"), False, False, 0)
                text.pack_start(label(description, "hub-hint"), False, False, 0)
                row.pack_start(text, True, True, 0)
                status = label("Checking…", "hub-hint")
                row.pack_start(status, False, False, 0)
                button = action("Toggle" if key in ("menu", "center") else "Start",
                                lambda _, component=key: self._open_component(component))
                row.pack_start(button, False, False, 0)
                section.pack_start(row, False, False, 0)
                self.component_state[name] = status
                self._component_buttons[name] = button
            maintenance = horizontal(10)
            body.pack_start(maintenance, False, False, 0)
            maintenance.pack_start(action("Check components", lambda _: self._refresh_system()), False, False, 0)
            self.install_button = action("Install / repair bundled apps", lambda _: self._install_confirmed())
            maintenance.pack_start(self.install_button, False, False, 0)
            body.pack_start(label("The installer preserves your XFCE Panel and existing Plank items.", "hub-hint", True),
                            False, False, 0)

        def _build_performance(self):
            body = self._page("performance", "Light by design", "Choose the resource policy for Control Center. No new background service is installed.")
            pane = cls(vertical(13), "hub-card")
            body.pack_start(pane, False, False, 0)
            pane.pack_start(label("Performance profile", "hub-section"), False, False, 0)
            self.performance_picker = Gtk.ComboBoxText()
            for key, description in (("light", "Light — lower background work"),
                                     ("balanced", "Balanced — recommended"),
                                     ("visual", "Visual — smoother effects")):
                self.performance_picker.append(key, description)
            self.performance_picker.set_tooltip_text("Select a profile to apply; RiceHub does not assume your current preference")
            pane.pack_start(self.performance_picker, False, False, 0)
            pane.pack_start(label("Light reduces motion and media artwork; Balanced preserves responsive controls; Visual prioritizes smooth animation.",
                                  "hub-body", True), False, False, 0)
            self.performance_button = action("Apply performance profile", lambda _: self._apply_performance(), True)
            pane.pack_start(self.performance_button, False, False, 0)
            self.performance_button.set_sensitive(False)
            self.performance_picker.connect(
                "changed", lambda picker: self.performance_button.set_sensitive(
                    not self._busy and picker.get_active_id() in PERFORMANCE_PROFILES))

            measure = cls(vertical(12), "hub-card")
            body.pack_start(measure, False, False, 0)
            measure.pack_start(label("Resource snapshot", "hub-section"), False, False, 0)
            measure.pack_start(label("On-demand process PSS and CPU reading. This is a sample, not a performance promise.",
                                     "hub-body", True), False, False, 0)
            self.measure_label = label("Run a check while the desktop components are open.", "hub-metric", True)
            measure.pack_start(self.measure_label, False, False, 0)
            self.measure_button = action("Measure now", lambda _: self._measure())
            measure.pack_start(self.measure_button, False, False, 0)

        def _build_backups(self):
            body = self._page("backups", "Backups & recovery", "MacRice snapshots are private and kept outside the replaceable application bundle.")
            self.backup_list = cls(vertical(11), "hub-card")
            body.pack_start(self.backup_list, False, False, 0)
            buttons = horizontal(10)
            body.pack_start(buttons, False, False, 0)
            buttons.pack_start(action("Refresh history", lambda _: self._refresh_backups()), False, False, 0)
            self.restore_button = action("Restore previous desktop", lambda _: self._restore_confirmed(), True)
            buttons.pack_start(self.restore_button, False, False, 0)
            body.pack_start(label("Restore only reverts settings still controlled by RiceHub. Later personal changes are preserved and reported.",
                                  "hub-hint", True), False, False, 0)
            self._refresh_backups()

        def _build_roadmap(self):
            body = self._page("roadmap", "Quality roadmap",
                              "Seven installable rice families; Linux Mint hardware acceptance remains open.")
            milestones = (
                ("Cross-rice switching", "In validation", "Preserve the coordinated Plank, MacBar and Windows shell transitions and verify login reconciliation on Mint XFCE."),
                ("Windows 10", "Release candidate", "Verify the flat penguin shell, window list, tray, panel coexistence and recovery on actual Mint XFCE hardware."),
                ("Windows 7", "Release candidate", "Check Aero glass, compositor differences, SNI icons and keyboard navigation on real X11 systems."),
                ("XP & Classic", "Installable candidate", "Original GTK/XFWM/icon themes, live shell, safe switching and restore; physical Mint check pending."),
                ("ChromeOS & Y2K", "Installable candidate", "Shelf or glass taskbar, app search, desktop tools and reversible setup; screen-size checks pending."),
                ("All rices", "Acceptance pending", "Validate multi-monitor layouts, HiDPI, restore after login, idle resource use and guided updates."),
            )
            for title, status, detail in milestones:
                panel = cls(vertical(6), "hub-card")
                row = horizontal(10)
                row.pack_start(label(title, "hub-section"), True, True, 0)
                row.pack_start(label(status, "hub-soon"), False, False, 0)
                panel.pack_start(row, False, False, 0)
                panel.pack_start(label(detail, "hub-body", True), False, False, 0)
                body.pack_start(panel, False, False, 0)

        def _switch_page(self, key):
            self._active_page = key
            self.pages.set_visible_child_name(key)
            for page, button in self._nav_buttons.items():
                context = button.get_style_context()
                context.remove_class("hub-selected")
                if page == key:
                    context.add_class("hub-selected")
            if key == "backups":
                self._refresh_backups()

        def _select_family(self, key):
            family = FAMILY_BY_KEY[key]
            self._selected = key
            for current, button in self._family_buttons.items():
                context = button.get_style_context()
                context.remove_class("hub-selected")
                if current == key:
                    context.add_class("hub-selected")
            self.preview_title.set_text(family.title + " — " + family.subtitle)
            self.preview_description.set_text(family.description)
            self.preview_stack.set_visible_child_name(
                "windows7" if key == "windows7" else
                "windows10" if key == "windows10" else
                "macos" if key == "macos" else
                key if family.prototype else "future")
            self.aero_preview_bar.set_visible(key == "windows7")
            self.style_picker.set_visible(family.available)
            self.plan_button.set_visible(family.available)
            self.apply_button.set_visible(family.available)
            self.prototype_button.set_visible(family.prototype)
            self.prototype_button.set_label(
                "Explore Windows 10 preview" if key == "windows10" else
                "Explore Aero Start preview" if key == "windows7" else "Explore desktop prototype")
            self.prototype_button.get_accessible().set_name(self.prototype_button.get_label())
            self.future_note.set_text(
                "Aero is installable; its separate Start preview changes nothing."
                if key == "windows7" else
                "Windows 10 is installable; this separate concept preview changes nothing."
                if key == "windows10" else "This concept preview changes nothing.")
            self.future_note.set_visible(family.prototype or not family.available)
            if family.available:
                self._rebuilding_picker = True
                self.style_picker.remove_all()
                for style_id in family.styles:
                    self.style_picker.append(style_id, STYLES[style_id].name)
                self.style_picker.set_active_id(family.styles[0])
                self._rebuilding_picker = False
                self._on_style_changed()

        def _show_prototype(self):
            if self._selected == "windows7":
                show_windows7(self, Gtk, Gdk, GLib)
            elif self._selected == "windows10":
                show_windows10(self, Gtk, Gdk, GLib)
            elif self._selected in ("winxp", "winclassic", "chromeos", "frutiger"):
                show_concept(self, Gtk, Gdk, GLib, self._selected)

        def _on_style_changed(self, *_args):
            if self._rebuilding_picker:
                return
            style_id = self.style_picker.get_active_id() or "night"
            if style_id not in STYLES:
                return
            self._preview_style = style_id
            wallpaper = STYLES[style_id].wallpaper
            if wallpaper not in self._wallpaper_cache:
                path = project_root() / "assets/wallpapers" / wallpaper
                try:
                    self._wallpaper_cache[wallpaper] = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(path), 1200, 500, True)
                except GLib.Error:
                    self._wallpaper_cache[wallpaper] = None
            self._preview_rendered = None
            allocation = self.preview_stack.get_allocation()
            self._resize_wallpaper(None, allocation)

        def _resize_wallpaper(self, _widget, allocation):
            """Fit wallpaper without a Cairo draw callback or wide minimum size."""
            width = allocation.width
            height = allocation.height
            if width <= 0 or height <= 0:
                return
            wallpaper = STYLES[self._preview_style].wallpaper
            key = wallpaper, width, height
            if key == self._preview_rendered:
                return
            pixbuf = self._wallpaper_cache.get(wallpaper)
            if pixbuf is not None:
                self.preview_image.set_from_pixbuf(
                    aspect_fill(pixbuf, width, height, GdkPixbuf.InterpType.BILINEAR))
            else:
                self.preview_image.clear()
            self._preview_rendered = key

        def _filter_families(self, *_args):
            shown = {family.key for family in search_families(self.search.get_text())}
            for key, button in self._family_buttons.items():
                button.get_parent().set_visible(key in shown)
            self.empty.set_visible(not shown)
            if shown and self._selected not in shown:
                self._select_family(next(family.key for family in FAMILIES if family.key in shown))

        def _key(self, _widget, event):
            if event.state & Gdk.ModifierType.CONTROL_MASK and event.keyval in (Gdk.KEY_f, Gdk.KEY_F):
                self._switch_page("discover")
                self.search.grab_focus()
                return True
            return False

        def _notify(self, message, error=False):
            self.feedback.set_text(message)
            context = self.feedback.get_style_context()
            context.remove_class("hub-error")
            context.remove_class("hub-status")
            context.add_class("hub-error" if error else "hub-status")

        def _set_busy(self, busy):
            self._busy = busy
            for name in ("apply_button", "plan_button", "prototype_button", "install_button", "restore_button",
                         "performance_button", "measure_button"):
                button = getattr(self, name, None)
                if button:
                    button.set_sensitive(not busy)
            if not busy and hasattr(self, "performance_button"):
                self.performance_button.set_sensitive(
                    self.performance_picker.get_active_id() in PERFORMANCE_PROFILES)
            if not busy and hasattr(self, "restore_button"):
                self.restore_button.set_sensitive(bool(recent_backups()))

        def _work(self, message, job, completed=None):
            if self._busy:
                return
            self._set_busy(True)
            self._notify(message)

            def worker():
                try:
                    result, error = job(), None
                except Exception as exc:
                    result, error = None, str(exc)
                GLib.idle_add(self._finished, result, error, completed)

            threading.Thread(target=worker, daemon=True).start()

        def _finished(self, result, error, completed):
            self._set_busy(False)
            if error:
                self._notify(error, error=True)
            elif completed:
                completed(result)
            else:
                self._notify("Done.")
            return False

        def _confirm(self, title, details, proceed):
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE, text=title)
            dialog.format_secondary_text(details)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Continue", Gtk.ResponseType.OK)
            accepted = dialog.run() == Gtk.ResponseType.OK
            dialog.destroy()
            if accepted:
                proceed()

        def _plan_selected(self, apply_after=False):
            if not FAMILY_BY_KEY[self._selected].available:
                return
            selected = self.style_picker.get_active_id()
            if selected not in STYLES:
                return

            def ready(outcome):
                changes, _apps, _source, _target = outcome
                count = sum(change["before"] != change["after"] for change in changes)
                message = f"{STYLES[selected].name} is ready. {count} desktop fields would change."
                self._notify(message)
                if apply_after:
                    self._confirm(
                        f"Apply {STYLES[selected].name}?",
                        "This changes GTK, windows, Thunar, Plank, MacBar, menu, Control Center and wallpaper. "
                        "A private backup will be saved. No system packages are removed.",
                        lambda: self._work("Applying the complete desktop rice…",
                                           lambda: apply(selected),
                                           lambda backup: self._after_apply(backup, selected)),
                    )

            self._work("Checking installed themes and desktop settings…", lambda: plan(selected), ready)

        def _after_apply(self, backup, style_id):
            from .shell_session import sync_theme
            from .shell_session import install_login_reconciler
            try:
                install_login_reconciler()
                startup_warnings = ()
            except OSError as exc:
                startup_warnings = (f"Login sync: {exc}",)
            warnings = startup_warnings + sync_theme(STYLES[style_id].gtk)
            if warnings:
                self._notify("Rice saved, but taskbar switching needs attention: " + "; ".join(warnings), error=True)
            else:
                self._notify("Rice applied successfully. Recovery snapshot saved.")
            self._refresh_backups()
            self._refresh_system()

        def _restore_confirmed(self):
            backups = recent_backups()
            if not backups:
                self._notify("No active Rice backup is available.", error=True)
                return
            self._confirm(
                "Restore the previous desktop?",
                "RiceHub will restore the latest MacRice snapshot. Settings changed afterward are kept and reported.",
                lambda: self._work("Restoring your desktop…", restore, self._after_restore),
            )

        def _after_restore(self, backup):
            try:
                from .rice import XfceBackend
                from .shell_session import sync_theme
                warnings = sync_theme(XfceBackend().get("xfconf", "xsettings", "/Net/ThemeName"))
            except (OSError, RuntimeError) as exc:
                warnings = (str(exc),)
            skipped = backup / "skipped.json"
            message = "Desktop restored"
            if skipped.is_file():
                import json
                message += "; newer edits preserved: " + ", ".join(json.loads(skipped.read_text(encoding="utf-8")))
            if warnings:
                message += "; taskbar switching needs attention: " + "; ".join(warnings)
                self._notify(message, error=True)
            else:
                self._notify(message + ".")
            self._refresh_backups()
            self._refresh_system()

        def _refresh_backups(self):
            if not hasattr(self, "backup_list"):
                return
            for child in self.backup_list.get_children():
                self.backup_list.remove(child)
            records = recent_backups()
            if not records:
                self.backup_list.pack_start(label("No active restore points yet. Apply an available rice to create one.",
                                                  "hub-body", True), False, False, 0)
            for record in records:
                row = horizontal(10)
                style = STYLES.get(record.style)
                row.pack_start(label(style.name if style else record.style, "hub-title"), True, True, 0)
                row.pack_start(label(record.created, "hub-hint"), False, False, 0)
                self.backup_list.pack_start(row, False, False, 0)
            self.backup_list.show_all()
            if hasattr(self, "restore_button") and not self._busy:
                self.restore_button.set_sensitive(bool(records))

        def _refresh_system(self):
            def worker():
                try:
                    desktop = detect().as_dict()
                    available = installed_components()
                except Exception as exc:
                    GLib.idle_add(self._notify, "Desktop detection unavailable: " + str(exc), True)
                    return
                GLib.idle_add(self._set_system_info, desktop, available)
            threading.Thread(target=worker, daemon=True).start()

        def _set_system_info(self, desktop, available):
            for key, field in self.desktop_fields.items():
                field.set_text(str(desktop.get(key) or "Not detected"))
            for name, field in self.component_state.items():
                ready = available.get(name, False)
                field.set_text("Installed" if ready else "Missing")
                self._component_buttons[name].set_sensitive(ready)
            return False

        def _open_component(self, key):
            try:
                open_component(key)
                self._notify(f"{key.title()} launch requested.")
            except (OSError, RuntimeError, ValueError) as exc:
                self._notify(str(exc), error=True)

        def _install_confirmed(self):
            self._confirm(
                "Install or repair bundled apps?",
                "Runs the three existing user-local installers. Preserves Plank and the XFCE Panel. "
                "Previously installed app versions are backed up by their installers.",
                lambda: self._work("Installing bundled components…",
                                   lambda: install(InstallOptions(no_start=True)),
                                   lambda _: self._after_install()),
            )

        def _after_install(self):
            self._notify("Components installed. Existing running apps may need one restart after this upgrade.")
            self._refresh_system()

        def _apply_performance(self):
            selected = self.performance_picker.get_active_id()
            if selected not in PERFORMANCE_PROFILES:
                return
            self._work(f"Saving {selected.title()} settings…", lambda: apply_profile(selected),
                       lambda _: self._notify(f"{selected.title()} performance profile saved."))

        def _measure(self):
            def finished(processes):
                if not processes:
                    self.measure_label.set_text("No running MacRice components or Plank were detected.")
                else:
                    self.measure_label.set_text("\n".join(
                        f"{item['name']}: "
                        + (f"{item['pss_kib'] / 1024:.1f} MiB PSS" if item["pss_kib"] is not None
                           else "PSS unavailable")
                        + (f" · {item['cpu_percent']:.1f}% CPU" if item["cpu_percent"] is not None
                           else " · CPU unavailable") for item in processes))
                self._notify("Resource snapshot complete.")
            self._work("Measuring running processes…", measure_processes, finished)

    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS)
    except GLib.Error as exc:
        print(f"RiceHub CSS could not be loaded: {exc}", file=__import__("sys").stderr)
        return 1
    screen = Gdk.Screen.get_default()
    if screen is None:
        print("RiceHub: GTK could not find a desktop display.", file=__import__("sys").stderr)
        return 1
    Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    app = Gtk.Application(application_id="io.github.ricehub.xfce", flags=Gio.ApplicationFlags.FLAGS_NONE)
    windows = []
    startup_failed = False

    def activate(application):
        nonlocal startup_failed
        if not _activate_hub_window(application, windows, HubWindow):
            startup_failed = True

    app.connect("activate", activate)
    status = app.run(["ricehub"])
    return 1 if startup_failed else status
