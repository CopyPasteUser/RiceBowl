"""RiceBowl's compact GTK3 rice selector and recovery workbench.

The catalog previews actual virtual-X11 captures of installable desktop styles.
No extra daemon, browser, compositor or root privileges are required.
"""

from __future__ import annotations

import os
import threading
import traceback
from pathlib import Path

from .hub_art import FAMILY_ICONS, PREVIEW_FILES, aspect_contain, aspect_fill
from .hub_catalog import FAMILIES, FAMILY_BY_KEY, recent_backups, search_families


# The hub has no independent release number: the package tag can lag main.
# These are the canonical hub-only runtime visual tokens.
TOKENS = {
    "window": "#121b26", "sidebar": "#0e1520", "surface": "#1b2837",
    "surface_alt": "#223449", "hover": "#2a4057", "active": "#25425f",
    "border": "#31485e", "text": "#f4f8fc", "muted": "#bdcad8",
    "quiet": "#91a9bf", "accent": "#9ad3ff", "accent_ink": "#102437",
    "success": "#a2d7bf", "warning": "#eec691", "error": "#ffaaa5",
    "preview_veil": "#1b293a", "font": "Cantarell, Inter, sans-serif",
}

CSS = """/* RiceBowl native GTK3 app screen — measured, accessible, low-motion. */
#ricebowl-window {{ background: {window}; color: {text}; }}
#ricebowl-sidebar {{ background: {sidebar}; border-right: 1px solid {border}; }}
#ricebowl-content {{ background: {window}; }}
.hub-brand {{ color: {text}; font-family: {font}; font-size: 21px; font-weight: 700; }}
.hub-overline {{ color: {quiet}; font-size: 11px; }}
.hub-header {{ color: {text}; font-family: {font}; font-size: 24px; font-weight: 700; }}
.hub-section {{ color: {text}; font-family: {font}; font-size: 16px; font-weight: 700; }}
.hub-title {{ color: {text}; font-family: {font}; font-size: 13px; font-weight: 700; }}
.hub-body {{ color: {muted}; font-family: {font}; font-size: 13px; }}
.hub-hint {{ color: {quiet}; font-family: {font}; font-size: 12px; }}
.hub-good {{ color: {success}; font-size: 11px; font-weight: bold; }}
.hub-soon {{ color: {warning}; font-size: 11px; font-weight: bold; }}
.hub-error {{ color: {error}; font-size: 12px; }}
.hub-metric {{ color: {text}; font-family: {font}; font-size: 12px; }}
.hub-status {{ color: {muted}; font-size: 11px; }}
.hub-card {{ background: {surface}; border: 1px solid {border}; border-radius: 11px; padding: 12px; }}
.hub-info {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 10px; padding: 11px; }}
.hub-preview-footer {{ background: {preview_veil}; padding: 12px 15px; }}
.hub-preview-frame {{ background: {sidebar}; border: 1px solid {border}; border-radius: 11px; }}
.hub-placeholder {{ color: {muted}; font-family: {font}; font-size: 14px; }}
button.hub-nav, button.hub-card-button, button.hub-action, button.hub-primary {{
  background-image: none; box-shadow: none; border-radius: 9px; color: {text};
  border: 1px solid transparent; padding: 8px 11px; min-height: 32px;
}}
button.hub-nav {{ background-color: transparent; }}
button.hub-nav:hover, button.hub-card-button:hover {{ background: {hover}; }}
button.hub-nav.hub-selected {{ background: {active}; color: {text}; border-left: 3px solid {accent}; }}
button.hub-card-button {{ background: {surface}; border-color: {border}; padding: 9px 10px; border-radius: 9px; }}
button.hub-card-button.hub-selected {{ border-color: {accent}; background: {active}; }}
button.hub-card-button:active, button.hub-nav:active {{ background: {active}; }}
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


def quick_update_label(plan) -> str:
    """Use one truthful action for both the preview and confirmed update."""
    if plan is not None and plan.needed:
        return "Install update…"
    return "Check for updates"


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
        print("RiceBowl needs a graphical XFCE session.", file=__import__("sys").stderr)
        return 1
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GdkPixbuf", "2.0")
        gi.require_version("Pango", "1.0")
        from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango
    except (ImportError, ValueError) as exc:
        print(f"RiceBowl needs GTK3/PyGObject: {exc}", file=__import__("sys").stderr)
        return 1

    from .cli import open_component
    from .environment import detect, installed_components
    from .installer import InstallOptions, install, project_root
    from .performance import PROFILES as PERFORMANCE_PROFILES, apply_profile, measure_processes
    from .rice import STYLES, apply, plan, restore

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
            super().__init__(application=application, title="RiceBowl — XFCE Rices")
            self.set_name("ricebowl-window")
            self.set_default_size(1040, 680)
            self.set_size_request(760, 500)
            self.set_position(Gtk.WindowPosition.CENTER)
            self._busy = False
            self._selected = "macos"
            self._active_page = "discover"
            self._nav_buttons = {}
            self._family_buttons = {}
            self._component_buttons = {}
            self._image_cache = {}
            self._preview_style = "night"
            self._preview_rendered = None
            self._update_plan = None
            self._update_activity = None
            try:
                self.set_icon_from_file(str(project_root() / "assets/ricebowl-symbolic.svg"))
            except (OSError, GLib.Error):
                pass

            layout = horizontal(0)
            self.add(layout)
            self._build_sidebar(layout)
            area = vertical(0)
            area.set_name("ricebowl-content")
            layout.pack_start(area, True, True, 0)
            self.pages = Gtk.Stack()
            self.pages.set_transition_type(Gtk.StackTransitionType.NONE)
            area.pack_start(self.pages, True, True, 0)
            self._build_discover()
            self._build_desktop()
            self._build_components()
            self._build_performance()
            self._build_backups()

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
            side = vertical(15)
            side.set_name("ricebowl-sidebar")
            side.set_size_request(180, -1)
            side.set_margin_top(20)
            side.set_margin_bottom(16)
            side.set_margin_start(11)
            side.set_margin_end(11)
            layout.pack_start(side, False, False, 0)

            brand = horizontal(11)
            symbol = project_root() / "assets/ricebowl-symbolic.svg"
            if symbol.is_file():
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(symbol), 36, 36, True)
                    brand.pack_start(Gtk.Image.new_from_pixbuf(pixbuf), False, False, 0)
                except GLib.Error:
                    pass
            title = vertical(2)
            title.pack_start(label("RiceBowl", "hub-brand"), False, False, 0)
            title.pack_start(label("Desktop styles", "hub-hint"), False, False, 0)
            brand.pack_start(title, True, True, 0)
            side.pack_start(brand, False, False, 6)

            for key, name, symbol in (
                ("discover", "Rices", "view-grid-symbolic"),
                ("desktop", "Current desktop", "video-display-symbolic"),
                ("components", "macOS tools", "applications-system-symbolic"),
                ("performance", "Performance", "utilities-system-monitor-symbolic"),
                ("backups", "Recovery", "document-revert-symbolic"),
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
            side.pack_start(label("RICEBOWL UPDATES", "hub-overline"), False, False, 0)
            self.quick_update_button = action(quick_update_label(None),
                                              lambda _: self._quick_update(), True)
            self.quick_update_button.set_tooltip_text(
                "Check the official repository, review changes, then confirm before installing")
            side.pack_start(self.quick_update_button, False, False, 0)
            self.quick_update_status = label("Manual · No auto-install", "hub-hint", True)
            side.pack_start(self.quick_update_status, False, False, 0)
            side.pack_start(label("7 styles · XFCE/X11", "hub-hint"), False, False, 0)
            side.pack_start(label("Local · Reversible", "hub-hint"), False, False, 0)

        def _page(self, key, title, intro):
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            body = vertical(14)
            for side in ("start", "end"):
                getattr(body, "set_margin_" + side)(22)
            body.set_margin_top(22)
            body.set_margin_bottom(24)
            body.pack_start(label(title, "hub-header"), False, False, 0)
            body.pack_start(label(intro, "hub-body", True), False, False, 0)
            scroll.add(body)
            self.pages.add_named(scroll, key)
            return body

        def _build_discover(self):
            body = self._page("discover", "Choose a rice", "Seven installable desktop styles. Your Linux apps stay yours.")
            workspace = horizontal(14)
            body.pack_start(workspace, False, False, 0)

            browser = vertical(9)
            browser.set_size_request(200, -1)
            workspace.pack_start(browser, False, False, 0)
            browser.pack_start(label("DESKTOP STYLES", "hub-overline"), False, False, 0)
            finder = horizontal(5)
            browser.pack_start(finder, False, False, 0)
            self.search = Gtk.SearchEntry()
            self.search.set_placeholder_text("Filter styles")
            self.search.get_accessible().set_name("Filter desktop styles")
            self.search.connect("search-changed", self._filter_families)
            finder.pack_start(self.search, True, True, 0)
            self.search_clear = cls(Gtk.Button.new_from_icon_name("edit-clear-symbolic", Gtk.IconSize.MENU), "hub-action")
            self.search_clear.set_tooltip_text("Clear style filter")
            self.search_clear.get_accessible().set_name("Clear style filter")
            self.search_clear.connect("clicked", self._clear_filter)
            self.search_clear.set_no_show_all(True)
            finder.pack_start(self.search_clear, False, False, 0)

            self.gallery = Gtk.FlowBox()
            self.gallery.set_selection_mode(Gtk.SelectionMode.NONE)
            self.gallery.set_min_children_per_line(1)
            self.gallery.set_max_children_per_line(1)
            self.gallery.set_row_spacing(6)
            browser.pack_start(self.gallery, False, False, 0)
            for family in FAMILIES:
                self._family_card(family)
            self.empty = label("No matching style. Clear the filter to see all seven.", "hub-hint", True)
            self.empty.set_no_show_all(True)
            browser.pack_start(self.empty, False, False, 0)

            details = vertical(11)
            workspace.pack_start(details, True, True, 0)
            self.preview = cls(vertical(0), "hub-preview-frame")
            details.pack_start(self.preview, False, False, 0)
            canvas = Gtk.DrawingArea()
            canvas.set_size_request(-1, 245)
            canvas.connect("size-allocate", self._resize_preview)
            self.preview_canvas = canvas
            image_layer = Gtk.Overlay()
            image_layer.add(canvas)
            self.preview_image = Gtk.Image()
            self.preview_image.set_halign(Gtk.Align.CENTER)
            self.preview_image.set_valign(Gtk.Align.CENTER)
            image_layer.add_overlay(self.preview_image)
            self.preview.pack_start(image_layer, False, False, 0)
            summary = cls(vertical(5), "hub-preview-footer")
            self.preview_title = label("macOS · Aurora", "hub-section")
            self.preview_description = label("", "hub-body", True)
            self.preview_caption = label("Wallpaper preview · macOS components", "hub-hint")
            summary.pack_start(self.preview_title, False, False, 0)
            summary.pack_start(self.preview_description, False, False, 0)
            summary.pack_start(self.preview_caption, False, False, 0)
            self.preview.pack_start(summary, False, False, 0)

            details.pack_start(label("APPEARANCE", "hub-overline"), False, False, 0)
            self.style_picker = Gtk.ComboBoxText()
            self._rebuilding_picker = False
            for key in FAMILY_BY_KEY["macos"].styles:
                style = STYLES[key]
                self.style_picker.append(key, style.name)
            self.style_picker.set_active_id("night")
            self.style_picker.set_tooltip_text("Choose a complete desktop appearance")
            self.style_picker.connect("changed", self._on_style_changed)
            details.pack_start(self.style_picker, False, False, 0)
            controls = horizontal(9)
            details.pack_start(controls, False, False, 0)
            self.plan_button = action("Check", lambda _: self._plan_selected())
            self.plan_button.set_tooltip_text("Read-only requirements check before applying")
            controls.pack_start(self.plan_button, True, True, 0)
            self.apply_button = action("Apply rice", lambda _: self._plan_selected(apply_after=True), True)
            controls.pack_start(self.apply_button, True, True, 0)
            details.pack_start(label("Applying a rice saves a restore point first.", "hub-hint", True), False, False, 0)

        def _family_card(self, family):
            button = cls(Gtk.Button(), "hub-card-button")
            button.set_size_request(196, 53)
            contents = horizontal(9)
            icon_path = project_root() / "assets" / FAMILY_ICONS[family.key]
            try:
                icon = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon_path), 30, 30, True)
                contents.pack_start(Gtk.Image.new_from_pixbuf(icon), False, False, 0)
            except GLib.Error:
                contents.pack_start(Gtk.Image.new_from_icon_name("preferences-desktop-theme-symbolic", Gtk.IconSize.MENU), False, False, 0)
            text = vertical(2)
            title = label(family.title, "hub-title")
            subtitle = label(family.subtitle, "hub-hint")
            # Names must not force the sidebar wider on older 1024px laptops.
            for item in (title, subtitle):
                item.set_ellipsize(Pango.EllipsizeMode.END)
                item.set_max_width_chars(21)
                item.set_tooltip_text(item.get_text())
            text.pack_start(title, False, False, 0)
            text.pack_start(subtitle, False, False, 0)
            contents.pack_start(text, True, True, 0)
            button.add(contents)
            button.get_accessible().set_name(f"Select {family.title}")
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
            body = self._page("components", "macOS tools", "Individual Aurora components. Other rice shells are managed automatically.")
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
            body = self._page("performance", "Performance", "Control Center resource policy and on-demand process measurements.")
            pane = cls(vertical(13), "hub-card")
            body.pack_start(pane, False, False, 0)
            pane.pack_start(label("Performance profile", "hub-section"), False, False, 0)
            self.performance_picker = Gtk.ComboBoxText()
            for key, description in (("light", "Light — lower background work"),
                                     ("balanced", "Balanced — recommended"),
                                     ("visual", "Visual — smoother effects")):
                self.performance_picker.append(key, description)
            self.performance_picker.set_tooltip_text("Select a profile to apply; RiceBowl does not assume your current preference")
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
            body = self._page("backups", "Recovery", "Restore previous desktop settings without overwriting newer personal changes.")
            body.pack_start(label("SYSTEM HEALTH", "hub-overline"), False, False, 0)
            body.pack_start(label("Check the current XFCE session and installed backends without modifying system settings.",
                                  "hub-hint", True), False, False, 0)
            self.doctor_button = action("Run read-only system check", lambda _: self._run_doctor())
            body.pack_start(self.doctor_button, False, False, 0)
            self.doctor_summary = label("Not checked yet", "hub-hint", True)
            body.pack_start(self.doctor_summary, False, False, 0)
            doctor_scroll = Gtk.ScrolledWindow()
            doctor_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            doctor_scroll.set_size_request(-1, 152)
            self.doctor_results = vertical(6)
            doctor_scroll.add(self.doctor_results)
            body.pack_start(doctor_scroll, False, False, 0)
            body.pack_start(label("SAFE UPDATES", "hub-overline"), False, False, 0)
            body.pack_start(label("Preview a fast-forward revision from the official repository. "
                                  "Updates are never installed automatically.", "hub-hint", True),
                            False, False, 0)
            self.update_label = label("Not checked yet. Existing Rice and personal settings are preserved.",
                                      "hub-hint", True)
            body.pack_start(self.update_label, False, False, 0)
            updates = horizontal(9)
            body.pack_start(updates, False, False, 0)
            self.update_check_button = action("Check GitHub revision", lambda _: self._check_update())
            self.update_apply_button = action("Install checked revision…", lambda _: self._confirm_update(), True)
            self.update_apply_button.set_sensitive(False)
            updates.pack_start(self.update_check_button, False, False, 0)
            updates.pack_start(self.update_apply_button, False, False, 0)
            body.pack_start(label("RESTORE POINTS", "hub-overline"), False, False, 0)
            self.backup_list = cls(vertical(11), "hub-card")
            body.pack_start(self.backup_list, False, False, 0)
            buttons = horizontal(10)
            body.pack_start(buttons, False, False, 0)
            buttons.pack_start(action("Refresh", lambda _: self._refresh_backups()), False, False, 0)
            self.restore_button = action("Restore previous desktop", lambda _: self._restore_confirmed(), True)
            buttons.pack_start(self.restore_button, False, False, 0)
            body.pack_start(label("Restore only reverts settings still controlled by RiceBowl. Later personal changes are preserved and reported.",
                                  "hub-hint", True), False, False, 0)
            body.pack_start(label("THEME REPAIR", "hub-overline"), False, False, 0)
            self.repair_button = action("Repair selected rice assets…", lambda _: self._repair_selected())
            self.repair_button.set_tooltip_text(
                "Back up and replace only the rice selected on the Rices page; does not switch your desktop.")
            body.pack_start(self.repair_button, False, False, 0)
            body.pack_start(label("Use only if Check reports conflicting theme files. Select a non-macOS rice on the Rices page first.",
                                  "hub-hint", True), False, False, 0)
            body.pack_start(label("Hardware acceptance: multi-monitor, login/resume and Plank autostart still need testing on Mint XFCE.",
                                  "hub-hint", True), False, False, 0)
            self._refresh_backups()

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
            self.preview_title.set_text(family.title)
            self.preview_description.set_text(family.description)
            self.repair_button.set_visible(family.available and key != "macos")
            if family.available:
                self._rebuilding_picker = True
                self.style_picker.remove_all()
                for style_id in family.styles:
                    self.style_picker.append(style_id, STYLES[style_id].name)
                self.style_picker.set_active_id(family.styles[0])
                self._rebuilding_picker = False
                self._on_style_changed()

        def _on_style_changed(self, *_args):
            if self._rebuilding_picker:
                return
            style_id = self.style_picker.get_active_id() or "night"
            if style_id not in STYLES:
                return
            self._preview_style = style_id
            if self._selected in PREVIEW_FILES:
                asset = PREVIEW_FILES[self._selected]
                key = "capture:" + asset
                path = project_root() / "assets/hub-previews" / asset
                self.preview_caption.set_text("Real X11 capture · example variant")
            else:
                asset = STYLES[style_id].wallpaper
                key = "wallpaper:" + asset
                path = project_root() / "assets/wallpapers" / asset
                self.preview_caption.set_text("Wallpaper preview · macOS components")
            if key not in self._image_cache:
                try:
                    self._image_cache[key] = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                        str(path), 1200, 675, True)
                except GLib.Error:
                    self._image_cache[key] = None
            if self._image_cache[key] is None and self._selected in PREVIEW_FILES:
                wallpaper = STYLES[style_id].wallpaper
                key = "wallpaper:" + wallpaper
                if key not in self._image_cache:
                    try:
                        self._image_cache[key] = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                            str(project_root() / "assets/wallpapers" / wallpaper), 1200, 675, True)
                    except GLib.Error:
                        self._image_cache[key] = None
                self.preview_caption.set_text("Wallpaper preview · screenshot unavailable")
            self._preview_asset = key
            self._preview_rendered = None
            self._resize_preview(None, self.preview_canvas.get_allocation())

        def _resize_preview(self, _widget, allocation):
            """Fit actual desktop captures; never crop their menus or taskbars."""
            width = allocation.width
            height = allocation.height
            if width <= 0 or height <= 0:
                return
            asset = getattr(self, "_preview_asset", None)
            if asset is None:
                return
            key = asset, width, height
            if key == self._preview_rendered:
                return
            pixbuf = self._image_cache.get(asset)
            if pixbuf is not None:
                self.preview_image.set_from_pixbuf(
                    (aspect_contain if asset.startswith("capture:") else aspect_fill)(
                        pixbuf, width, height, GdkPixbuf.InterpType.BILINEAR))
            else:
                self.preview_image.clear()
            self._preview_rendered = key

        def _filter_families(self, *_args):
            query = self.search.get_text()
            shown = {family.key for family in search_families(query)}
            for key, button in self._family_buttons.items():
                button.get_parent().set_visible(key in shown)
            self.empty.set_visible(not shown)
            self.search_clear.set_visible(bool(query))
            if shown and self._selected not in shown:
                self._select_family(next(family.key for family in FAMILIES if family.key in shown))

        def _clear_filter(self, *_args):
            self.search.set_text("")
            self.search.grab_focus()

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
            for name in ("apply_button", "plan_button", "repair_button", "install_button", "restore_button",
                         "performance_button", "measure_button", "doctor_button",
                         "update_check_button", "update_apply_button", "quick_update_button"):
                button = getattr(self, name, None)
                if button:
                    button.set_sensitive(not busy)
            if not busy and hasattr(self, "performance_button"):
                self.performance_button.set_sensitive(
                    self.performance_picker.get_active_id() in PERFORMANCE_PROFILES)
            if not busy and hasattr(self, "restore_button"):
                self.restore_button.set_sensitive(bool(recent_backups()))
            if not busy and hasattr(self, "update_apply_button"):
                self.update_apply_button.set_sensitive(bool(self._update_plan and self._update_plan.needed))

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
            if error and self._update_activity:
                self._update_plan = None
                self.quick_update_button.set_label(quick_update_label(None))
                self.quick_update_status.set_text("Update failed · See details below")
                self.update_label.set_text("Update failed: " + error[:180])
            self._update_activity = None
            if error:
                self._notify(error, error=True)
            elif completed:
                completed(result)
            else:
                self._notify("Done.")
            return False

        def _confirm(self, title, details, proceed, confirm_label):
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE, text=title)
            dialog.format_secondary_text(details)
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button(confirm_label, Gtk.ResponseType.OK)
            dialog.set_default_response(Gtk.ResponseType.CANCEL)
            accepted = dialog.run() == Gtk.ResponseType.OK
            dialog.destroy()
            if accepted:
                proceed()

        def _repair_selected(self):
            from .rice import repair_assets
            selected = self.style_picker.get_active_id()
            if selected not in STYLES or self._selected == "macos":
                return
            self._confirm(
                f"Repair local assets for {STYLES[selected].name}?",
                "Only this Rice's local theme and icon bundle will be replaced. "
                "Existing files are archived in a dated, private backup directory "
                "before replacement. The desktop theme is not switched.",
                lambda: self._work(
                    "Backing up and repairing local theme assets…",
                    lambda: repair_assets(selected),
                    lambda backups: self._notify(
                        "Theme assets repaired. " +
                        (f"{len(backups)} backup(s) saved. " if backups else "") +
                        "Run Check requirements again."),
                ),
                "Repair assets",
            )

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
                        "Apply rice",
                    )

            self._work("Checking installed themes and desktop settings…", lambda: plan(selected), ready)

        def _after_apply(self, backup, style_id):
            def activate():
                from .shell_session import install_login_reconciler, sync_theme
                try:
                    install_login_reconciler()
                    startup_warnings = ()
                except OSError as exc:
                    startup_warnings = (f"Login sync: {exc}",)
                return startup_warnings + sync_theme(STYLES[style_id].gtk)

            def finished(warnings):
                if warnings:
                    self._notify("Rice saved, but taskbar switching needs attention: " + "; ".join(warnings), error=True)
                else:
                    self._notify("Rice applied successfully. Recovery snapshot saved.")
                self._refresh_backups()
                self._refresh_system()

            # The GTK/D-Bus handoff may wait for a taskbar to map. Never block
            # the Hub's main thread during that readiness check.
            self._work("Starting and verifying desktop taskbar…", activate, finished)

        def _restore_confirmed(self):
            backups = recent_backups()
            if not backups:
                self._notify("No active Rice backup is available.", error=True)
                return
            self._confirm(
                "Restore the previous desktop?",
                "RiceBowl will restore the latest saved snapshot. Settings changed afterward are kept and reported.",
                lambda: self._work("Restoring your desktop…", restore, self._after_restore),
                "Restore desktop",
            )

        def _run_doctor(self):
            from .doctor import diagnose
            self.doctor_summary.set_text("Checking the current session…")
            self._work("Running read-only RiceBowl health checks…", diagnose, self._show_doctor)

        def _show_doctor(self, checks):
            from .doctor import summary
            for child in tuple(self.doctor_results.get_children()):
                child.destroy()
            for item in checks:
                caption = ("✓" if item.status == "ok" else "!" if item.status == "warning" else "·")
                details = item.message + (" — " + item.advice if item.advice else "")
                self.doctor_results.pack_start(label(caption + " " + details, "hub-hint", True),
                                               False, False, 0)
            self.doctor_results.show_all()
            ok, warnings, optional = summary(checks)
            self.doctor_summary.set_text(f"{ok} ready · {warnings} need attention · {optional} optional")
            self._notify("Health check complete." if not warnings else
                         f"Health check found {warnings} issue(s); review Recovery.",
                         error=bool(warnings))

        def _quick_update(self):
            if self._update_plan is not None and self._update_plan.needed:
                self._confirm_update()
            else:
                self._check_update()

        def _check_update(self):
            from .updater import inspect
            self._update_plan = None
            self._update_activity = "check"
            self.update_apply_button.set_sensitive(False)
            self.update_label.set_text("Checking the official repository…")
            self.quick_update_button.set_label(quick_update_label(None))
            self.quick_update_status.set_text("Checking trusted origin/main…")
            self._work("Checking available RiceBowl revision…",
                       lambda: inspect(refresh=True), self._show_update)

        def _show_update(self, plan):
            self._update_plan = plan
            self.update_label.set_text(
                f"Installed source {plan.current[:12]} · origin/main {plan.available[:12]} · "
                f"{plan.commits} new commit(s)" if plan.needed else
                f"Source already up to date at {plan.current[:12]}")
            self.update_apply_button.set_sensitive(plan.needed)
            self.quick_update_button.set_label(quick_update_label(plan))
            self.quick_update_status.set_text(
                f"{plan.commits} new commit(s) · Confirm to install" if plan.needed else
                "Already up to date")
            self._notify("A checked fast-forward update is available." if plan.needed else
                         "RiceBowl source is up to date.")

        def _confirm_update(self):
            from .updater import apply as apply_update
            plan = self._update_plan
            if not plan or not plan.needed:
                return
            self._confirm(
                "Install this checked RiceBowl revision?",
                "Update from " + plan.current[:12] + " to " + plan.available[:12] +
                ". Current installed files are archived. The manager may need restarting; "
                "existing desktop theme settings will not be switched.",
                lambda: self._install_checked_update(apply_update, plan),
                "Install update",
            )

        def _install_checked_update(self, apply_update, plan):
            self._update_activity = "install"
            self.quick_update_status.set_text("Installing verified revision…")
            self._work("Installing checked update with recovery…",
                       lambda: apply_update(source=plan.source,
                                            expected_revision=plan.available),
                       self._update_finished)

        def _update_finished(self, plan):
            self._update_plan = None
            self.update_apply_button.set_sensitive(False)
            self.update_label.set_text("Installed " + plan.available[:12] +
                                       ". Restart RiceBowl to load updated code.")
            self.quick_update_button.set_label(quick_update_label(None))
            self.quick_update_status.set_text("Installed · Restart RiceBowl")
            self._notify("Update installed. Restart RiceBowl; active rice was not switched.")

        def _after_restore(self, backup):
            def reconcile():
                from .rice import XfceBackend
                from .shell_session import sync_theme
                try:
                    return sync_theme(XfceBackend().get("xfconf", "xsettings", "/Net/ThemeName"))
                except (OSError, RuntimeError) as exc:
                    return (str(exc),)

            def finished(warnings):
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

            self._work("Restoring and verifying desktop taskbar…", reconcile, finished)

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
                "Install / repair",
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
                    self.measure_label.set_text("No running RiceBowl components or Plank were detected.")
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
        print(f"RiceBowl CSS could not be loaded: {exc}", file=__import__("sys").stderr)
        return 1
    screen = Gdk.Screen.get_default()
    if screen is None:
        print("RiceBowl: GTK could not find a desktop display.", file=__import__("sys").stderr)
        return 1
    Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    app = Gtk.Application(application_id="io.github.ricehub.xfce", flags=Gio.ApplicationFlags.FLAGS_NONE)
    windows = []
    startup_failed = False

    def activate(application):
        nonlocal startup_failed
        if not _activate_hub_window(application, windows, HubWindow):
            startup_failed = True
        elif os.environ.get("RICEBOWL_HUB_SMOKE") == "1":
            # CI only: exercise every rice and navigation path under virtual X11
            # without touching XFCE settings, then exit before any user action.
            GLib.idle_add(smoke_test)

    def smoke_test():
        nonlocal startup_failed
        try:
            window = windows[0]
            for family in FAMILIES:
                window._select_family(family.key)
                assert window._selected == family.key
                assert window.style_picker.get_active_id() == family.styles[0]
                assert window._image_cache.get(window._preview_asset) is not None, family.key
            window.search.set_text("Windows XP")
            # Gtk.SearchEntry debounces the user-facing search-changed signal.
            # Exercise the filter deterministically without waiting on a timer.
            window._filter_families()
            assert window._selected == "winxp"
            window._clear_filter()
            assert window.search.get_text() == ""
            for page in ("desktop", "components", "performance", "backups", "discover"):
                window._switch_page(page)
                assert window.pages.get_visible_child_name() == page
        except Exception:
            startup_failed = True
            traceback.print_exc()
        finally:
            app.quit()
        return False

    app.connect("activate", activate)
    status = app.run(["ricebowl"])
    return 1 if startup_failed else status
