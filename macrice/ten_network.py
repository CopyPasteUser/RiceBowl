"""Windows 10 network flyout backed by NetworkManager through riceSpice."""

from __future__ import annotations

from .riceware import spice


def network_description(network):
    """Bounded display text; connection success is never inferred from signal."""
    security = "Secured" if network.security and network.security != "--" else "Open"
    return f"{network.signal}% signal · {security}" + (" · Connected" if network.connected else "")


class TenNetworkFlyout:
    def __init__(self, shell, Gtk, Gdk, runner):
        self.shell, self.Gtk, self.runner = shell, Gtk, runner
        self.epoch = 0
        self.busy = False
        self.closed = False
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Windows 10 · Network")
        self.window.set_decorated(False)
        self.window.set_resizable(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.window.set_transient_for(shell.bar)
        self.window.set_keep_above(True)
        self.window.set_default_size(340, 440)

        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10),
                            "ten-network-root")
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        header.pack_start(shell._class(Gtk.Label(label="Network & Internet", xalign=0),
                                      "ten-action-title"), True, True, 0)
        close = shell._class(Gtk.Button(label="×"), "ten-rail-button")
        close.get_accessible().set_name("Close network panel")
        close.connect("clicked", lambda _button: self.hide())
        header.pack_end(close, False, False, 0)
        root.pack_start(header, False, False, 0)
        self.status = shell._class(Gtk.Label(label="Checking Wi-Fi…", xalign=0), "ten-muted")
        root.pack_start(self.status, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.networks = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        scroll.add(self.networks)
        root.pack_start(scroll, True, True, 0)
        self.feedback = shell._class(Gtk.Label(label="", xalign=0), "ten-action-feedback")
        self.feedback.set_line_wrap(True)
        root.pack_start(self.feedback, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        refresh = shell._class(Gtk.Button(label="Refresh networks"), "ten-settings-action")
        refresh.get_accessible().set_name("Rescan available Wi-Fi networks")
        refresh.connect("clicked", lambda _button: self.refresh(rescan=True))
        actions.pack_start(refresh, True, True, 0)
        settings = shell._class(Gtk.Button(label="Network settings"), "ten-settings-action")
        settings.get_accessible().set_name("Open Windows 10 network settings")
        settings.connect("clicked", lambda _button: shell._open_ten_settings("network"))
        actions.pack_start(settings, True, True, 0)
        root.pack_end(actions, False, False, 0)

        self.window.add(root)
        self.window.connect("delete-event", lambda *_args: self._on_delete())
        self.window.connect("key-press-event", self._key)
        self.window.connect("focus-out-event", lambda *_args: self.hide())

    def _key(self, _window, event):
        if event.keyval == self.Gtk.accelerator_parse("Escape")[0]:
            self.hide()
            return True
        return False

    def _on_delete(self):
        self.hide()
        return True

    def show(self):
        if self.closed:
            return
        self.epoch += 1
        rect = self.shell._desktop_rect()
        width = min(340, max(0, rect.width - 16))
        height = min(440, max(0, rect.height - 64))
        if width < 250 or height < 230:
            self.shell._error("The screen is too small for network settings.")
            return
        self.window.show_all()
        self.window.resize(width, height)
        self.window.move(rect.x + rect.width - width - 8, rect.y + rect.height - height - 48)
        self.window.present()
        self.refresh()

    def hide(self):
        self.epoch += 1
        self.window.hide()
        # No SSIDs persist in hidden GTK child widgets.
        for child in self.networks.get_children():
            self.networks.remove(child)

    def refresh(self, *, rescan=False):
        if self.closed or not self.window.get_visible():
            return
        epoch = self.epoch
        self.status.set_text("Scanning available Wi-Fi networks…" if rescan else
                             "Reading network state…")

        def done(response):
            if epoch != self.epoch or not self.window.get_visible():
                return
            radio, networks = response.value if response.error is None else (None, None)
            if response.error or networks.status != "ok":
                self.status.set_text("Wi-Fi networks unavailable")
                self.feedback.set_text(response.error or networks.reason or
                                       "NetworkManager is not available")
                self._render(())
                return
            if radio.status == "ok" and radio.value is False:
                self.status.set_text("Wi-Fi is turned off")
                self.feedback.set_text("Enable Wi-Fi in Action Center to scan networks")
                self._render(())
            else:
                self.status.set_text("Available Wi-Fi networks")
                self._render(networks.value)

        self.runner.submit("ten-wifi-list", lambda: (
            spice.read("wifi"), spice.scan_wifi(rescan=rescan)), done)

    def _render(self, items):
        Gtk = self.Gtk
        for child in self.networks.get_children():
            self.networks.remove(child)
        if not items:
            self.networks.pack_start(self.shell._class(
                Gtk.Label(label="No visible Wi-Fi networks", xalign=0), "ten-muted"),
                False, False, 0)
        for network in items[:12]:
            row = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6),
                                    "ten-network-item")
            detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            ssid = self.shell._class(Gtk.Label(label=network.ssid, xalign=0),
                                     "ten-network-name")
            ssid.set_ellipsize(3)
            ssid.set_max_width_chars(21)
            detail.pack_start(ssid, False, False, 0)
            detail.pack_start(self.shell._class(
                Gtk.Label(label=network_description(network), xalign=0), "ten-muted"),
                False, False, 0)
            row.pack_start(detail, True, True, 0)
            action = "wifi_disconnect" if network.connected else "wifi_connect"
            label = "Disconnect" if network.connected else "Connect"
            button = self.shell._class(Gtk.Button(label=label), "ten-settings-action")
            button.set_sensitive(not self.busy)
            button.get_accessible().set_name(label + " " + network.ssid)
            button.connect("clicked", lambda _button, act=action, ssid=network.ssid:
                           self._change(act, ssid))
            row.pack_end(button, False, False, 0)
            self.networks.pack_start(row, False, False, 0)
        self.networks.show_all()

    def _change(self, action, ssid):
        if self.busy or self.closed:
            return
        self.busy = True
        self.feedback.set_text("Connecting…" if action == "wifi_connect" else "Disconnecting…")
        epoch = self.epoch

        def done(response):
            self.busy = False
            if epoch != self.epoch or not self.window.get_visible():
                return
            result = response.value
            if response.error or result.status != "ok":
                reason = response.error or result.reason or "Connection change not verified"
                self.feedback.set_text(reason + (" · Use NetworkManager settings for a password."
                                                 if action == "wifi_connect" else ""))
            else:
                self.feedback.set_text("Connection verified")
            self.refresh()
            self.shell._refresh_status_async()

        self.runner.submit("ten-wifi-change", lambda: spice.change(
            action, ssid if action == "wifi_connect" else None), done)

    def close(self):
        if self.closed:
            return
        self.hide()
        self.closed = True
        self.window.destroy()
