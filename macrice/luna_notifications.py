"""XP-style event balloons derived only from observed hardware transitions."""

from __future__ import annotations

from .hardware_status import DesktopStatus


def event_messages(previous: DesktopStatus | None,
                   current: DesktopStatus) -> tuple[str, ...]:
    """Never announce states on first sample, or while backend state is unknown."""
    if previous is None:
        return ()
    events = []
    if previous.network != current.network:
        if current.network == "offline":
            events.append("Network connection lost")
        elif previous.network == "offline":
            events.append("Connected using " + (
                "Wi-Fi" if current.network == "wifi" else "Ethernet"))
    old, new = previous.battery, current.battery
    if old is not None and new is not None and not new.charging:
        if old.percent > 15 >= new.percent:
            events.append("Battery low — " + str(new.percent) + "% remaining")
        elif old.charging and new.percent <= 15:
            events.append("Power disconnected — " + str(new.percent) + "% remaining")
    return tuple(events)


def removable_mount_message(mount, *, added: bool) -> str | None:
    """Notify only verified removable-volume mounts, never arbitrary GVfs shares.

    A mount signal means mounted/unmounted, *not* that a device was safely
    ejected or a file transfer completed. Both claims would be misleading.
    """
    try:
        volume = mount.get_volume()
        drive = volume.get_drive() if volume is not None else None
        if drive is None or not (drive.is_removable() or drive.is_media_removable()):
            return None
        name = " ".join((mount.get_name() or "Removable device").split())[:72]
    except (AttributeError, RuntimeError, ValueError):
        return None
    return (name + " is ready to use" if added else name + " was unmounted")


class LunaBalloon:
    """Dismissible, auto-expiring lightweight notification above the taskbar."""

    css_prefix = "luna-balloon"
    heading_text = "RiceBowl · Windows XP"

    def __init__(self, shell, Gtk, Gdk, GLib):
        self.shell, self.Gtk, self.GLib = shell, Gtk, GLib
        self.window = None
        self.timeout = 0

    def show(self, message: str):
        self.close()
        Gtk, Gdk = self.Gtk, self.Gdk
        window = self.shell._class(Gtk.Window(type=Gtk.WindowType.TOPLEVEL),
                                   self.css_prefix)
        window.set_decorated(False)
        window.set_resizable(False)
        window.set_skip_taskbar_hint(True)
        window.set_skip_pager_hint(True)
        window.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
        window.set_keep_above(True)
        window.set_accept_focus(False)
        window.set_default_size(240, -1)
        body = self.shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6),
                                 self.css_prefix + "-body")
        heading = self.shell._class(Gtk.Label(label=self.heading_text, xalign=0),
                                    self.css_prefix + "-title")
        body.pack_start(heading, False, False, 0)
        detail = Gtk.Label(label=message, xalign=0)
        detail.set_line_wrap(True)
        body.pack_start(detail, False, False, 0)
        dismiss = self.shell._class(Gtk.Button(label="Dismiss"),
                                    self.css_prefix + "-dismiss")
        dismiss.connect("clicked", lambda _button: self.close())
        body.pack_end(dismiss, False, False, 0)
        window.add(body)
        window.connect("key-press-event", lambda _win, event:
                       self.close() or event.keyval == Gdk.KEY_Escape)
        window.show_all()
        rect = self.shell._desktop_rect()
        width, height = window.get_size()
        window.move(rect.x + max(8, rect.width - width - 10),
                    rect.y + max(8, rect.height - height - 40 - 9))
        self.window = window
        self.timeout = self.GLib.timeout_add_seconds(7, self._expire)

    def _expire(self):
        self.timeout = 0
        self.close()
        return False

    def close(self):
        if self.timeout:
            self.GLib.source_remove(self.timeout)
            self.timeout = 0
        if self.window is not None:
            self.window.destroy()
            self.window = None
