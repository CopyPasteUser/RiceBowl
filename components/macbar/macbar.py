#!/usr/bin/python3
"""MacBar: a lightweight X11/GTK3 top panel for XFCE with no task list."""

from __future__ import annotations

import configparser
import ctypes
import ctypes.util
import datetime as dt
import json
import logging
import os
import shutil
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GdkX11", "3.0")
from gi.repository import Gdk, GdkPixbuf, GdkX11, Gio, GLib, Gtk  # noqa: E402

from status import Volume, clock_text, network_status, parse_pactl, parse_wpctl, read_battery  # noqa: E402


LOG = logging.getLogger("macbar")
APP_ID = "io.github.macbar.panel"
VERSION = "1.0.0"
HEIGHT = 30
DEFAULT_CONFIG = {
    "theme": "dark",
    "height": HEIGHT,
    "menu_command": ["macmenu", "--toggle"],
    "control_center_command": ["macos-control-center", "--toggle"],
    "menu_icon": "",
    "show_battery_percent": True,
}
THEMES = {
    "dark": {"bg": "rgba(20,22,29,.91)", "fg": "#f6f6fa", "hover": "rgba(255,255,255,.13)", "line": "rgba(255,255,255,.16)"},
    "light": {"bg": "rgba(245,246,249,.93)", "fg": "#1f2430", "hover": "rgba(0,0,0,.07)", "line": "rgba(0,0,0,.12)"},
}


def load_config() -> dict:
    path = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "macbar" / "config.json"
    if not path.exists():
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("config must be an object")
        settings = {**DEFAULT_CONFIG, **data}
        if settings["theme"] not in {"dark", "light"}:
            raise ValueError("theme must be dark or light")
        if type(settings["height"]) is not int or not 26 <= settings["height"] <= 48:
            raise ValueError("height must be 26..48")
        if not isinstance(settings["menu_icon"], str):
            raise ValueError("menu_icon must be a path or icon name")
        if not isinstance(settings["show_battery_percent"], bool):
            raise ValueError("show_battery_percent must be true or false")
        for key in ("menu_command", "control_center_command"):
            cmd = settings[key]
            if not isinstance(cmd, list) or not cmd or not all(isinstance(c, str) and c for c in cmd):
                raise ValueError(f"{key} must be a nonempty array of strings")
        return settings
    except (OSError, ValueError, TypeError) as exc:
        LOG.warning("Ignoring invalid config %s: %s", path, exc)
        return DEFAULT_CONFIG.copy()


def menu_icon(configured: str) -> str:
    if configured:
        return str(Path(configured).expanduser())
    desktop_file = Path.home() / ".local/share/applications/macmenu.desktop"
    if desktop_file.exists():
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(desktop_file, encoding="utf-8")
            return parser.get("Desktop Entry", "Icon", fallback="start-here-symbolic")
        except (OSError, configparser.Error):
            pass
    return "start-here-symbolic"


def icon(name: str, size: int = 16) -> Gtk.Image:
    widget = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.MENU)
    widget.set_pixel_size(size)
    return widget


def button(tooltip: str, child: Gtk.Widget) -> Gtk.Button:
    widget = Gtk.Button()
    widget.set_relief(Gtk.ReliefStyle.NONE)
    # GTK tooltips can be placed outside the screen above top-edge dock windows.
    # Accessible names retain the description without creating a popup.
    widget.set_has_tooltip(False)
    widget.get_accessible().set_name(tooltip)
    widget.add(child)
    widget.get_style_context().add_class("bar-button")
    return widget


def indicator(tooltip: str, child: Gtk.Widget) -> Gtk.Box:
    """Read-only status display: no accidental click action or popup."""
    widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    widget.set_has_tooltip(False)
    widget.get_accessible().set_name(tooltip)
    widget.pack_start(child, False, False, 0)
    widget.get_style_context().add_class("bar-indicator")
    return widget


def describe(widget: Gtk.Widget, description: str) -> None:
    """Update the accessible label without an off-screen GTK tooltip."""
    widget.get_accessible().set_name(description)


class MacBar(Gtk.Application):
    def __init__(self, replace_xfce: bool = False) -> None:
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.settings = load_config()
        self.window: Gtk.Window | None = None
        self.audio_busy = False
        self.audio_process: Gio.Subprocess | None = None
        self.network_proxy = None
        self.network_active_types: tuple[str, ...] = ()
        self.network_generation = 0
        self.network_state = 0
        self.network_primary = ""
        self.last_volume: Volume | None = None
        self.replace_xfce = replace_xfce
        self.replace_attempts = 0
        self.monitor_width = 1024
        self.last_battery = None

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            return
        if Gdk.Display.get_default() is None or not isinstance(Gdk.Display.get_default(), GdkX11.X11Display):
            LOG.error("MacBar requires an X11 desktop session")
            self.quit()
            return
        self._style()
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("MacBar")
        window.set_name("macbar-window")
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_accept_focus(False)
        window.set_skip_taskbar_hint(True)
        window.set_skip_pager_hint(True)
        window.set_type_hint(Gdk.WindowTypeHint.DOCK)
        window.stick()
        window.connect("realize", self._on_realize)
        window.connect("destroy", lambda *_: self.quit())
        self.window = window

        shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        shell.get_style_context().add_class("macbar-shell")
        window.add(shell)

        start_icon = menu_icon(self.settings["menu_icon"])
        if Path(start_icon).is_file():
            try:
                pixels = GdkPixbuf.Pixbuf.new_from_file_at_scale(start_icon, 19, 19, True)
                image = Gtk.Image.new_from_pixbuf(pixels)
            except GLib.Error as exc:
                LOG.warning("Menu icon could not be loaded: %s", exc)
                image = icon("start-here-symbolic", 19)
        else:
            image = icon(start_icon, 19)
        self.menu_button = button("Open / close MacMenu", image)
        self.menu_button.get_style_context().add_class("app-launcher")
        self.menu_button.connect("clicked", lambda _: self._launch("menu_command", self.menu_button))
        shell.pack_start(self.menu_button, False, False, 5)

        spacer = Gtk.Box()
        shell.pack_start(spacer, True, True, 0)

        self.network_image = icon("network-offline-symbolic")
        self.network_indicator = indicator("Network disconnected", self.network_image)
        shell.pack_start(self.network_indicator, False, False, 0)

        self.audio_image = icon("audio-volume-medium-symbolic")
        self.audio_indicator = indicator("Volume", self.audio_image)

        self.battery_box = Gtk.Box(spacing=4)
        self.battery_image = icon("battery-good-symbolic")
        self.battery_text = Gtk.Label()
        self.battery_box.pack_start(self.battery_image, False, False, 0)
        self.battery_box.pack_start(self.battery_text, False, False, 0)
        self.battery_indicator = indicator("Battery", self.battery_box)

        self.cc_button = button("Open / close Control Center", icon("preferences-system-symbolic", 17))
        self.cc_button.connect("clicked", lambda _: self._launch("control_center_command", self.cc_button))
        self.cc_button.get_style_context().add_class("control-center")

        self.clock_label = Gtk.Label()
        self.clock_label.get_style_context().add_class("clock-label")
        self.clock_indicator = indicator("Local time", self.clock_label)

        for item in (self.audio_indicator, self.battery_indicator, self.cc_button, self.clock_indicator):
            shell.pack_start(item, False, False, 0)

        self._position()
        window.show_all()
        self._battery_tick()
        self._clock_tick()
        self._query_volume()
        self._init_network()
        if self.replace_xfce:
            GLib.timeout_add(1200, self._replace_panel)
        GLib.timeout_add_seconds(60, self._battery_tick)
        GLib.timeout_add_seconds(15, self._volume_tick)
        screen = Gdk.Screen.get_default()
        screen.connect("monitors-changed", lambda *_: self._position())
        screen.connect("size-changed", lambda *_: self._position())

    def _replace_panel(self) -> bool:
        if self.window and not self.window.get_mapped():
            self.replace_attempts += 1
            if self.replace_attempts < 5:
                return GLib.SOURCE_CONTINUE
            LOG.warning("MacBar did not map within six seconds; leaving XFCE Panel running")
            return GLib.SOURCE_REMOVE
        if self.window and shutil.which("xfce4-panel"):
            try:
                Gio.Subprocess.new(["xfce4-panel", "--quit"], Gio.SubprocessFlags.NONE)
            except GLib.Error as exc:
                LOG.warning("Could not stop xfce4-panel: %s", exc)
        return GLib.SOURCE_REMOVE

    def _style(self) -> None:
        colors = THEMES[self.settings["theme"]]
        css = f"""
            #macbar-window {{ background: transparent; }}
            .macbar-shell {{ background-color: {colors['bg']}; border-bottom: 1px solid {colors['line']}; }}
            .bar-button {{ background: transparent; background-image: none; box-shadow: none; border: 0;
                           color: {colors['fg']}; border-radius: 5px; padding: 2px 7px;
                           min-width: 20px; min-height: 20px; }}
            .bar-button:hover {{ background: {colors['hover']}; }}
            .bar-button:focus {{ outline: 1px solid #0a84ff; outline-offset: -1px; }}
            .bar-button:active {{ background: {colors['hover']}; }}
            .bar-button.launch-error {{ color: #ff453a; }}
            .bar-indicator {{ color: {colors['fg']}; padding: 2px 7px; min-height: 20px; }}
            .clock-label {{ color: {colors['fg']}; font-family: sans-serif; font-size: 12px; font-weight: 500; padding: 0 4px; }}
            .app-launcher {{ padding: 2px 8px; }}
            .control-center:hover {{ color: #0a84ff; }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _position(self) -> None:
        if not self.window:
            return
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            LOG.warning("No X11 monitor geometry available")
            return
        rect = monitor.get_geometry()
        self.geometry = rect
        self.monitor_width = rect.width
        height = self.settings["height"]
        self.window.move(rect.x, rect.y)
        self.window.resize(rect.width, height)
        self.window.set_size_request(rect.width, height)
        self._render_clock()
        self._render_battery()
        if self.window.get_realized():
            self._set_strut()

    def _on_realize(self, *_: object) -> None:
        self._set_strut()

    def _set_strut(self) -> None:
        """Reserve the top edge for maximized X11 windows (EWMH)."""
        try:
            # Only claim the global top edge; otherwise a monitor in a stacked
            # layout could incorrectly reserve space on a different monitor.
            rect = self.geometry
            if rect.y != 0:
                LOG.warning("Primary monitor is not on the root top edge; no EWMH strut set")
                return
            lib = ctypes.CDLL(ctypes.util.find_library("X11"))
            lib.XOpenDisplay.restype = ctypes.c_void_p
            lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
            lib.XInternAtom.restype = ctypes.c_ulong
            lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
            lib.XChangeProperty.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
                                            ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
            lib.XCloseDisplay.argtypes = [ctypes.c_void_p]
            display = lib.XOpenDisplay(None)
            if not display:
                return
            try:
                xid = GdkX11.X11Window.get_xid(self.window.get_window())
                cardinal = lib.XInternAtom(display, b"CARDINAL", 0)
                top = self.settings["height"]
                props = (
                    ("_NET_WM_STRUT", (0, 0, top, 0)),
                    ("_NET_WM_STRUT_PARTIAL", (0, 0, top, 0, 0, 0, 0, 0,
                                                rect.x, rect.x + rect.width - 1, 0, 0)),
                )
                for name, values in props:
                    data = (ctypes.c_ulong * len(values))(*values)
                    atom = lib.XInternAtom(display, name.encode(), 0)
                    lib.XChangeProperty(display, xid, atom, cardinal, 32, 0, data, len(values))
                lib.XFlush.argtypes = [ctypes.c_void_p]
                lib.XFlush(display)
            finally:
                lib.XCloseDisplay(display)
        except (AttributeError, OSError, TypeError) as exc:
            LOG.warning("Could not reserve top screen area: %s", exc)

    def _launch(self, key: str, trigger: Gtk.Widget) -> None:
        argv = self.settings[key]
        executable = os.path.expanduser(argv[0])
        resolved = shutil.which(executable)
        if not resolved and "/" not in executable:
            candidate = Path.home() / ".local/bin" / executable
            if candidate.is_file() and os.access(candidate, os.X_OK):
                resolved = str(candidate)
        if not resolved:
            self._launch_error(trigger, f"Command not found: {argv[0]}. Check ~/.config/macbar/config.json")
            return
        try:
            process = Gio.Subprocess.new([resolved, *argv[1:]], Gio.SubprocessFlags.NONE)
            process.wait_async(None, self._launch_finished, trigger)
        except GLib.Error as exc:
            self._launch_error(trigger, f"Failed to launch: {exc.message}")

    def _launch_finished(self, process: Gio.Subprocess, result: Gio.AsyncResult, trigger: Gtk.Widget) -> None:
        try:
            process.wait_finish(result)
            if not process.get_successful():
                self._launch_error(trigger, f"Launcher exited with code {process.get_exit_status()}")
            else:
                trigger.get_style_context().remove_class("launch-error")
                describe(trigger, "Open / close MacMenu" if trigger is self.menu_button else "Open / close Control Center")
        except GLib.Error as exc:
            LOG.warning("Launcher exited unexpectedly: %s", exc)

    def _launch_error(self, trigger: Gtk.Widget, message: str) -> None:
        LOG.warning("%s", message)
        describe(trigger, message)
        trigger.get_style_context().add_class("launch-error")

    def _clock_tick(self) -> bool:
        now = dt.datetime.now()
        self._render_clock(now)
        GLib.timeout_add_seconds(max(1, 60 - now.second), self._clock_tick)
        return GLib.SOURCE_REMOVE

    def _render_clock(self, now: dt.datetime | None = None) -> None:
        self.clock_label.set_text(clock_text(now or dt.datetime.now(), self.monitor_width))

    def _battery_tick(self) -> bool:
        self.last_battery = read_battery()
        self._render_battery()
        return GLib.SOURCE_CONTINUE

    def _render_battery(self) -> None:
        battery = self.last_battery
        self.battery_indicator.set_visible(battery is not None)
        if battery:
            state = "charging" if battery.state == "Charging" else ""
            level = "full" if battery.percent >= 95 else "good" if battery.percent >= 60 else "medium" if battery.percent >= 30 else "low" if battery.percent >= 15 else "caution"
            self.battery_image.set_from_icon_name(f"battery-{level}{('-' + state) if state else ''}-symbolic", Gtk.IconSize.MENU)
            self.battery_text.set_text(f"{battery.percent}%" if self.settings["show_battery_percent"] and self.monitor_width >= 480 else "")
            describe(self.battery_indicator, f"Battery {battery.percent}% · {battery.state}")

    def _init_network(self) -> None:
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
            "org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager",
            "org.freedesktop.NetworkManager", None, self._network_ready, None,
        )

    def _network_ready(self, _source: object, result: Gio.AsyncResult, _data: object) -> None:
        try:
            self.network_proxy = Gio.DBusProxy.new_for_bus_finish(result)
            self.network_proxy.connect("g-properties-changed", lambda *_: self._network_update())
            self._network_update()
        except GLib.Error as exc:
            LOG.warning("NetworkManager unavailable: %s", exc)
            describe(self.network_indicator, "Network status unavailable")

    def _network_update(self) -> None:
        proxy = self.network_proxy
        if not proxy:
            return
        state = proxy.get_cached_property("State")
        self.network_state = int(state.unpack()) if state is not None else 0
        primary = proxy.get_cached_property("PrimaryConnectionType")
        self.network_primary = str(primary.unpack()) if primary is not None else ""
        self.network_active_types = ()
        self.network_generation += 1
        self._render_network()
        if self.network_primary in ("802-11-wireless", "802-3-ethernet"):
            return
        # A VPN can be the primary connection while the actual link is Wi-Fi.
        active = proxy.get_cached_property("ActiveConnections")
        paths = tuple(active.unpack()) if active is not None else ()
        generation = self.network_generation
        for path in paths[:8]:
            Gio.DBusProxy.new_for_bus(
                Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
                "org.freedesktop.NetworkManager", path,
                "org.freedesktop.NetworkManager.Connection.Active", None,
                self._active_connection_ready, generation,
            )

    def _active_connection_ready(self, _source: object, result: Gio.AsyncResult, generation: int) -> None:
        if generation != self.network_generation:
            return
        try:
            proxy = Gio.DBusProxy.new_for_bus_finish(result)
            kind = proxy.get_cached_property("Type")
            if kind is not None:
                value = str(kind.unpack())
                if value not in self.network_active_types:
                    self.network_active_types += (value,)
                    self._render_network()
        except GLib.Error as exc:
            LOG.debug("Could not inspect active network connection: %s", exc)

    def _render_network(self) -> None:
        name, description = network_status(self.network_state, self.network_primary, self.network_active_types)
        self.network_image.set_from_icon_name(name, Gtk.IconSize.MENU)
        describe(self.network_indicator, description)

    def _volume_tick(self) -> bool:
        self._query_volume()
        return GLib.SOURCE_CONTINUE

    def _query_volume(self) -> None:
        if self.audio_busy:
            return
        wpctl = shutil.which("wpctl")
        pactl = shutil.which("pactl")
        if wpctl:
            argv = [wpctl, "get-volume", "@DEFAULT_AUDIO_SINK@"]
            parser = parse_wpctl
        elif pactl:
            argv = [pactl, "get-sink-volume", "@DEFAULT_SINK@"]
            parser = parse_pactl
        else:
            describe(self.audio_indicator, "Audio backend not found")
            return
        self._read_volume(argv, parser)

    def _read_volume(self, argv: list[str], parser) -> None:
        try:
            proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
            self.audio_busy = True
            self.audio_process = proc
            proc.communicate_utf8_async(None, None, self._volume_ready, parser)
            GLib.timeout_add_seconds(3, self._audio_timeout, proc)
        except GLib.Error as exc:
            self.audio_busy = False
            LOG.warning("Audio status unavailable: %s", exc)

    def _audio_timeout(self, process: Gio.Subprocess) -> bool:
        if self.audio_process is process and self.audio_busy:
            LOG.warning("Audio status request timed out")
            process.force_exit()
        return GLib.SOURCE_REMOVE

    def _volume_ready(self, process: Gio.Subprocess, result: Gio.AsyncResult, parser) -> None:
        self.audio_busy = False
        self.audio_process = None
        try:
            ok, out, _ = process.communicate_utf8_finish(result)
            if ok and process.get_successful():
                volume = parser(out)
                if volume:
                    if parser is parse_pactl:
                        self._query_pactl_mute(volume)
                    else:
                        self._display_volume(volume)
                    return
        except GLib.Error as exc:
            LOG.debug("Audio status read failed: %s", exc)
        # A machine may have wpctl installed while PulseAudio is the active server.
        pactl = shutil.which("pactl") if parser is parse_wpctl else None
        if pactl:
            self._read_volume([pactl, "get-sink-volume", "@DEFAULT_SINK@"], parse_pactl)
        else:
            describe(self.audio_indicator, "Audio status unavailable")

    def _query_pactl_mute(self, volume: Volume) -> None:
        try:
            proc = Gio.Subprocess.new([shutil.which("pactl"), "get-sink-mute", "@DEFAULT_SINK@"],
                                      Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
            proc.communicate_utf8_async(None, None, self._pactl_mute_ready, volume)
        except (GLib.Error, TypeError):
            self._display_volume(volume)

    def _pactl_mute_ready(self, process: Gio.Subprocess, result: Gio.AsyncResult, volume: Volume) -> None:
        try:
            ok, out, _ = process.communicate_utf8_finish(result)
            self._display_volume(Volume(volume.percent, "yes" in out.lower()) if ok and process.get_successful() else volume)
        except GLib.Error:
            self._display_volume(volume)

    def _display_volume(self, volume: Volume) -> None:
        if self.last_volume == volume:
            return
        self.last_volume = volume
        name = "audio-volume-muted" if volume.muted or volume.percent == 0 else "audio-volume-low" if volume.percent < 35 else "audio-volume-medium" if volume.percent < 70 else "audio-volume-high"
        self.audio_image.set_from_icon_name(f"{name}-symbolic", Gtk.IconSize.MENU)
        describe(self.audio_indicator, f"Volume {volume.percent}%" + (" · muted" if volume.muted else ""))

def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if "--version" in sys.argv[1:]:
        print(f"MacBar {VERSION}")
        return 0
    replace_xfce = "--replace-xfce" in sys.argv[1:]
    arguments = [arg for arg in sys.argv if arg != "--replace-xfce"]
    try:
        return MacBar(replace_xfce=replace_xfce).run(arguments)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
