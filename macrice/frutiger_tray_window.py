"""Unclipped Aqua tray surfaces for the GTK3/X11 desktop dock.

Gtk.Popover is constrained to its ancestor toplevel, which here is a shallow
DOCK. Keep the visible flyout in a separate, owner-managed utility window.
"""

from __future__ import annotations

_TRAY_CLASS = None


def flyout_geometry(anchor_x: int, anchor_width: int, popup_width: int,
                   popup_height: int, screen_x: int, screen_y: int,
                   screen_width: int, screen_height: int) -> tuple[int, int]:
    x = max(screen_x + 5, min(anchor_x + anchor_width - popup_width,
                              screen_x + screen_width - popup_width - 5))
    y = max(screen_y + 5, screen_y + screen_height - popup_height - 48)
    return x, y


def create_tray_window(anchor, Gtk, *, title="Aqua World controls"):
    global _TRAY_CLASS
    from gi.repository import Gdk, GLib

    if _TRAY_CLASS is not None:
        return _TRAY_CLASS(anchor, title)

    class AquaTrayWindow(Gtk.Window):
        __gtype_name__ = "RiceBowlAquaTrayWindow"

        def __init__(self, anchor, title):
            super().__init__(type=Gtk.WindowType.TOPLEVEL)
            self._anchor = anchor
            self.set_title(title)
            self.set_decorated(False)
            self.set_resizable(False)
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
            self.set_keep_above(True)
            self.set_transient_for(anchor.get_toplevel())
            self.get_style_context().add_class("aqua-flyout")
            self.connect("focus-out-event", lambda window, _event: window.hide())
            self.connect("key-press-event", self._escape)
            self.connect("size-allocate", self._size_changed)

        def _escape(self, _window, event):
            if event.keyval == Gdk.KEY_Escape:
                self.popdown()
                return True
            return False

        def _size_changed(self, *_args):
            if self.get_visible():
                GLib.idle_add(self._place)

        def _place(self):
            anchor = self._anchor
            if not self.get_visible() or not anchor.get_realized():
                return False
            shell_window = anchor.get_toplevel()
            if not shell_window.get_window():
                return False
            offset = anchor.translate_coordinates(shell_window, 0, 0)
            if offset is None:
                return False
            origin_x, _origin_y = shell_window.get_window().get_root_origin()
            monitor = anchor.get_screen().get_monitor_geometry(
                anchor.get_screen().get_monitor_at_window(shell_window.get_window()))
            width, height = self.get_size()
            x, y = flyout_geometry(origin_x + offset[0], anchor.get_allocated_width(),
                                   width, height, monitor.x, monitor.y,
                                   monitor.width, monitor.height)
            if self.get_position() != (x, y):
                self.move(x, y)
            return False

        def popup(self):
            self.show_all()
            self.present()
            self._place()
            GLib.idle_add(self._place)

        def popdown(self):
            self.hide()

    _TRAY_CLASS = AquaTrayWindow
    return _TRAY_CLASS(anchor, title)
