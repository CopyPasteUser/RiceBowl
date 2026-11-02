"""Small native GTK3 suite manager, not another always-running desktop daemon."""

from __future__ import annotations

import os
import threading
from pathlib import Path


STYLE = b"""
#macrice-window {
  background: #151920;
  color: #f5f6f8;
}
#macrice-title { color: #f7f8fa; font-size: 21px; font-weight: 700; }
#macrice-subtitle { color: #9fa9b9; font-size: 12px; }
.section-title { color: #e7ebf1; font-size: 13px; font-weight: 700; }
.muted { color: #9fa9b9; font-size: 11px; }
.component-row {
  background: #222834;
  border-radius: 11px;
  padding: 6px 10px;
}
.component-name { color: #f5f6f8; font-weight: 600; }
.installed { color: #9ddbb0; }
.unavailable { color: #c2a9a9; }
button {
  border-radius: 8px;
  min-height: 26px;
  padding: 5px 11px;
  background: #303947;
  border: 1px solid #3c4654;
  color: #f1f4f8;
}
button:hover { background: #3e4a5b; }
button.suggested-action {
  background: #2673cd;
  color: #ffffff;
}
button:focus { outline: 2px solid #8fbfff; outline-offset: 1px; }
combobox button { background: #252c37; color: #f5f6f8; }
"""


def run() -> int:
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        print("MacRice Manager needs a graphical XFCE session.", file=__import__("sys").stderr)
        return 1
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
    except (ImportError, ValueError) as exc:
        print(f"GTK3/PyGObject is unavailable: {exc}", file=__import__("sys").stderr)
        return 1

    from .cli import open_component
    from .environment import detect, installed_components
    from .installer import InstallOptions, install
    from .performance import PROFILES, apply_profile
    from .themes import PRESETS, _read_preferences, apply_preset
    from .environment import config_home

    class Manager(Gtk.ApplicationWindow):
        def __init__(self, app):
            super().__init__(application=app, title="MacRice Settings")
            self.set_name("macrice-window")
            self.set_default_size(545, 640)
            self.set_resizable(True)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_border_width(22)
            self._busy = False
            self._status_labels = {}

            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.add(scroll)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=19)
            outer.set_border_width(1)
            scroll.add(outer)
            self._header(outer)
            self._components(outer, installed_components, open_component)
            self._appearance(outer, PRESETS, apply_preset)
            self._performance(outer, PROFILES, apply_profile)
            self._setup(outer, InstallOptions, install)
            self._detect_profile(detect)

        def _header(self, outer):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
            outer.pack_start(row, False, False, 0)
            symbol = Path(__file__).resolve().parents[1] / "assets/macrice-symbolic.svg"
            if symbol.exists():
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(symbol), 52, 52, True)
                icon = Gtk.Image.new_from_pixbuf(pixbuf)
                row.pack_start(icon, False, False, 0)
            titles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            row.pack_start(titles, True, True, 0)
            title = Gtk.Label(label="MacRice", xalign=0)
            title.set_name("macrice-title")
            titles.pack_start(title, False, False, 0)
            subtitle = Gtk.Label(label="Your XFCE desktop, working together.", xalign=0)
            subtitle.set_name("macrice-subtitle")
            titles.pack_start(subtitle, False, False, 0)

        def _section(self, outer, title):
            label = Gtk.Label(label=title, xalign=0)
            label.get_style_context().add_class("section-title")
            outer.pack_start(label, False, False, 0)

        def _components(self, outer, detector, launch):
            group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
            outer.pack_start(group, False, False, 0)
            title = Gtk.Label(label="Components", xalign=0)
            title.get_style_context().add_class("section-title")
            group.pack_start(title, False, False, 0)
            for name, action in (("MacMenu", "menu"), ("Control Center", "center"),
                                 ("MacBar", "bar"), ("Plank", "dock")):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                row.get_style_context().add_class("component-row")
                group.pack_start(row, False, False, 0)
                label = Gtk.Label(label=name, xalign=0)
                label.get_style_context().add_class("component-name")
                row.pack_start(label, True, True, 0)
                status = Gtk.Label(label="Checking…")
                self._status_labels[name] = status
                row.pack_start(status, False, False, 0)
                button = Gtk.Button(label="Open" if action in ("menu", "center") else "Start")
                button.set_tooltip_text(
                    "Toggle" if action in ("menu", "center")
                    else "Start the existing dock" if action == "dock"
                    else "Start the standalone top bar"
                )
                button.connect("clicked", lambda _widget, component=action: self._launch(component, launch))
                row.pack_start(button, False, False, 0)
                if action == "dock":
                    prefs = Gtk.Button(label="Settings")
                    prefs.set_tooltip_text("Open Plank's own preferences. Existing dock items are preserved.")
                    prefs.connect("clicked", self._plank_preferences)
                    row.pack_start(prefs, False, False, 0)
                    self._dock_buttons = (button, prefs)
            self._refresh = detector
            self._update_status()

        def _launch(self, component, launch):
            try:
                launch(component)
            except Exception as exc:
                self._message("Could not launch " + component + ": " + str(exc), error=True)

        def _plank_preferences(self, _widget):
            from .plank import open_dock
            try:
                open_dock(show_preferences=True)
            except (OSError, RuntimeError) as exc:
                self._message("Plank settings unavailable: " + str(exc), error=True)

        def _update_status(self):
            current = self._refresh()
            for name, label in self._status_labels.items():
                ready = current.get(name, False)
                label.set_text("Installed" if ready else "Not installed")
                context = label.get_style_context()
                context.remove_class("installed")
                context.remove_class("unavailable")
                context.add_class("installed" if ready else "unavailable")
            for button in self._dock_buttons:
                button.set_sensitive(current.get("Plank", False))

        def _appearance(self, outer, presets, apply):
            group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
            outer.pack_start(group, False, False, 0)
            title = Gtk.Label(label="Appearance", xalign=0)
            title.get_style_context().add_class("section-title")
            group.pack_start(title, False, False, 0)
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            group.pack_start(row, False, False, 0)
            self._theme = Gtk.ComboBoxText()
            for name in presets:
                self._theme.append_text(name)
            self._theme.set_active(0)
            self._theme.set_tooltip_text("Styles the three bundled apps only; Plank is managed by its own preferences")
            row.pack_start(self._theme, True, True, 0)
            button = Gtk.Button(label="Apply theme")
            button.get_style_context().add_class("suggested-action")
            button.connect("clicked", lambda _button: self._apply_theme(apply))
            row.pack_start(button, False, False, 0)
            caption = Gtk.Label(
                label="App colors only. Your GTK theme, icons and Plank dock stay untouched.",
                xalign=0,
            )
            caption.set_line_wrap(True)
            caption.get_style_context().add_class("muted")
            group.pack_start(caption, False, False, 0)
            self._detected = Gtk.Label(label="Detecting your current XFCE appearance…", xalign=0)
            self._detected.get_style_context().add_class("muted")
            self._detected.set_line_wrap(True)
            group.pack_start(self._detected, False, False, 0)

        def _detect_profile(self, detector):
            def worker():
                try:
                    profile = detector()
                    text = f"XFCE: {profile.gtk_theme or 'unknown'}  ·  Icons: {profile.icon_theme or 'unknown'}"
                    if profile.plank_theme or profile.plank_position or profile.plank_icon_size:
                        text += ("\nDock: " + (profile.plank_theme or "default")
                                 + " · " + (profile.plank_position or "position unknown")
                                 + " · " + (profile.plank_icon_size or "?") + " px")
                except Exception:
                    text = "Appearance detection unavailable; manual presets still work."
                GLib.idle_add(self._detected.set_text, text)
            threading.Thread(target=worker, daemon=True).start()

        def _apply_theme(self, apply):
            theme = self._theme.get_active_text()
            if not theme:
                return
            try:
                apply(theme)
            except Exception as exc:
                self._message("Theme unchanged: " + str(exc), error=True)
            else:
                self._message(f"{theme} saved. Running MacRice apps update their colors automatically.")

        def _performance(self, outer, profiles, apply):
            group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            outer.pack_start(group, False, False, 0)
            self._section(group, "Performance")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            group.pack_start(row, False, False, 0)
            self._profile = Gtk.ComboBoxText()
            for name in profiles:
                self._profile.append(name, name.title())
            try:
                current_profile = _read_preferences(config_home() / "macos-control-center/config.json").get("resource_profile", "balanced")
            except (OSError, ValueError):
                current_profile = "balanced"
            self._profile.set_active_id("visual" if current_profile == "responsive" else current_profile if current_profile in profiles else "balanced")
            self._profile.set_tooltip_text("Control Center resource usage, animation and artwork")
            row.pack_start(self._profile, True, True, 0)
            button = Gtk.Button(label="Apply profile")
            button.connect("clicked", lambda _button: self._apply_profile(apply))
            row.pack_start(button, False, False, 0)
            caption = Gtk.Label(
                label="Light minimizes background work; Balanced suits laptops; Visual allows smooth effects. Other app features stay available.",
                xalign=0,
            )
            caption.set_line_wrap(True)
            caption.get_style_context().add_class("muted")
            group.pack_start(caption, False, False, 0)

        def _apply_profile(self, apply):
            profile = self._profile.get_active_id()
            if profile:
                try:
                    apply(profile)
                except Exception as exc:
                    self._message("Profile unchanged: " + str(exc), error=True)
                else:
                    self._message(f"{profile.title()} profile saved; Control Center updates while running.")

        def _setup(self, outer, options_type, installer):
            group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
            outer.pack_start(group, False, False, 0)
            title = Gtk.Label(label="Setup & maintenance", xalign=0)
            title.get_style_context().add_class("section-title")
            group.pack_start(title, False, False, 0)
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            group.pack_start(row, False, False, 0)
            self._install_button = Gtk.Button(label="Install / Repair")
            self._install_button.connect(
                "clicked", lambda _button: self._confirm_install(installer, options_type)
            )
            row.pack_start(self._install_button, False, False, 0)
            refresh = Gtk.Button(label="Refresh status")
            refresh.connect("clicked", lambda _button: self._update_status())
            row.pack_start(refresh, False, False, 0)
            preview = Gtk.Button(label="Desktop preview")
            preview.set_tooltip_text("See the whole Rice, apply it safely, or restore your last desktop")
            preview.connect("clicked", self._open_preview)
            row.pack_start(preview, False, False, 0)
            self._feedback = Gtk.Label(label="Ready", xalign=0)
            self._feedback.set_line_wrap(True)
            self._feedback.get_style_context().add_class("muted")
            group.pack_start(self._feedback, False, False, 0)
            self._log = Gtk.Label(label="", xalign=0)
            self._log.set_line_wrap(True)
            self._log.get_style_context().add_class("muted")
            group.pack_start(self._log, False, False, 0)

        def _open_preview(self, _widget):
            current = getattr(self, "_preview_window", None)
            if current is not None and current.get_visible():
                current.present()
                return
            from .preview import open_preview
            try:
                self._preview_window = open_preview(self)
            except Exception as exc:
                self._message("Could not show desktop preview: " + str(exc), error=True)

        def _confirm_install(self, installer, options_type):
            if self._busy:
                return
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True,
                message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
                text="Install or repair the three bundled apps?",
            )
            dialog.format_secondary_text(
                "Only user-local application files will be updated. Your XFCE Panel, "
                "your Plank dock, icon theme, preferences and notes will be kept."
            )
            dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
            dialog.add_button("Install", Gtk.ResponseType.OK)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.OK:
                return
            self._busy = True
            self._install_button.set_sensitive(False)
            self._message("Installing…")

            def worker():
                try:
                    installer(options_type(), output=lambda line: GLib.idle_add(self._log.set_text, line))
                    GLib.idle_add(self._install_finished, None)
                except Exception as exc:
                    GLib.idle_add(self._install_finished, str(exc))
            threading.Thread(target=worker, daemon=True).start()

        def _install_finished(self, error):
            self._busy = False
            self._install_button.set_sensitive(True)
            self._update_status()
            if error:
                self._message("Installation stopped: " + error, error=True)
            else:
                self._message("Installation complete. Existing XFCE settings were kept.")
            return False

        def _message(self, message, error=False):
            self._feedback.set_text(message)
            context = self._feedback.get_style_context()
            context.remove_class("unavailable")
            if error:
                context.add_class("unavailable")

    class Application(Gtk.Application):
        def __init__(self):
            super().__init__(application_id="io.github.copypasteuser.MacRice")
            self.window = None

        def do_activate(self):
            if self.window is None:
                self.window = Manager(self)
            self.window.show_all()
            self.window.present()

    provider = Gtk.CssProvider()
    provider.load_from_data(STYLE)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )
    return Application().run([])
