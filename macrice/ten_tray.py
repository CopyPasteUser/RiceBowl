"""Windows 10 tray surfaces backed by existing, verified Linux device actions.

Windows 10 owns the renderer; LunaTray supplies only the established asynchronous
network/audio/BlueZ/UPower adapters. No XP artwork or XFCE theme is changed.
"""

from __future__ import annotations

from .luna_tray import LunaTray


TEN_TRAY_ICONS = {
    "Volume": "audio-volume-high",
    "Power": "battery",
    "Bluetooth devices": "bluetooth-active",
    "Date and time": "x-office-calendar",
}

TEN_SETTINGS_LINKS = {
    "Sound settings…": "sound",
    "Power options…": "system",
    "Date and time settings…": "time",
}


class TenTray(LunaTray):
    """Compact, independently anchored rectangular Win10-style flyouts."""

    def install(self, name, anchor):
        if name not in ("audio", "battery", "bluetooth", "clock"):
            raise ValueError("Windows 10 has a separate NetworkManager flyout")
        popup = super().install(name, anchor)
        popup.get_style_context().add_class("ten-tray-popup")
        popup.set_title("Windows 10 · " + name.title())
        return popup

    def _label(self, value, kind="luna-tray-caption"):
        css = {
            "luna-tray-title": "ten-tray-title",
            "luna-tray-section": "ten-tray-section",
        }.get(kind, "ten-tray-caption")
        return super()._label(value, css)

    def _heading(self, body, name, _xp_icon):
        Gtk = self.Gtk
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
        row.pack_start(self.shell._icon(TEN_TRAY_ICONS[name], Gtk.IconSize.LARGE_TOOLBAR),
                       False, False, 0)
        row.pack_start(self._label(name, "luna-tray-title"), True, True, 0)
        body.pack_start(row, False, False, 0)

    def _button(self, label, command, *, css="ten-tray-link"):
        native_page = TEN_SETTINGS_LINKS.get(label)
        if native_page:
            button = self.shell._class(self.Gtk.Button(label=label), css)
            button.get_accessible().set_name(label)
            button.connect("clicked", lambda _button, page=native_page:
                           self.shell._open_ten_settings(page))
            return button
        return super()._button(label, command, css=css)

    def toggle(self, name):
        if name not in self.popovers:
            return
        opening = not self.popovers[name].get_visible()
        if opening:
            # One desktop flyout at a time; device backends never own UI focus.
            if getattr(self.shell, "ten_network", None) is not None:
                self.shell.ten_network.hide()
            task_view = getattr(self.shell, "ten_task_view", None)
            if task_view is not None:
                task_view.hide()
        super().toggle(name)
