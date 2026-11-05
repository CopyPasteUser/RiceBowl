"""Shared GTK3 window-management primitives for independent rice settings.

Settings are real window-manager clients, unlike quick settings and transient
flyouts.  A themed title strip can move/maximize its own toplevel without
grabbing buttons, managing X11 geometry by hand, or adding a resident daemon.
"""

from __future__ import annotations


def configure_settings_window(window, Gdk, *, role: str) -> None:
    """Make a rice-owned settings surface a normal desktop window."""
    window.set_type_hint(Gdk.WindowTypeHint.NORMAL)
    window.set_skip_taskbar_hint(False)
    window.set_skip_pager_hint(False)
    window.set_keep_above(False)
    window.set_resizable(True)
    window.set_role(role)


def draggable_caption(window, contents, Gtk, Gdk):
    """Wrap only non-interactive title content in a move/maximize handle."""
    handle = Gtk.EventBox()
    handle.set_visible_window(False)
    handle.set_can_focus(True)
    handle.set_tooltip_text("Drag to move · Double-click to maximize")
    handle.get_accessible().set_name("Move or maximize settings window")
    handle.add(contents)

    def toggle_maximize():
        if window.is_maximized():
            window.unmaximize()
        else:
            window.maximize()

    def pressed(_widget, event):
        if event.button != 1:
            return False
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            toggle_maximize()
            return True
        if event.type == Gdk.EventType.BUTTON_PRESS:
            window.begin_move_drag(1, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    def keyboard(_widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            toggle_maximize()
            return True
        return False

    handle.connect("button-press-event", pressed)
    handle.connect("key-press-event", keyboard)
    return handle
