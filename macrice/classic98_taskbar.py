"""Classic 98 taskbar window menus, backed by live libwnck X11 capabilities."""

from __future__ import annotations


def available_actions(window, Wnck) -> tuple[tuple[str, bool], ...]:
    """Return the Win98 menu's current capabilities without retaining a WnckWindow."""
    flags = window.get_actions()

    def allowed(name):
        flag = getattr(Wnck.WindowActions, name, 0)
        return bool(flags & flag)

    minimized = window.is_minimized()
    maximized = window.is_maximized()
    return (
        ("Restore", (minimized and allowed("UNMINIMIZE")) or
         (maximized and allowed("UNMAXIMIZE"))),
        ("Move", not maximized and allowed("MOVE")),
        ("Size", not maximized and allowed("RESIZE")),
        ("Minimize", not minimized and allowed("MINIMIZE")),
        ("Maximize", not maximized and allowed("MAXIMIZE")),
        ("Close", allowed("CLOSE")),
    )


def perform(window, name: str, timestamp: int) -> None:
    """Request the window-manager action; never manipulate X11 IDs directly."""
    if name == "Restore":
        if window.is_minimized():
            window.unminimize(timestamp)
        elif window.is_maximized():
            window.unmaximize()
    elif name == "Move":
        window.activate(timestamp)
        window.keyboard_move()
    elif name == "Size":
        window.activate(timestamp)
        window.keyboard_size()
    elif name == "Minimize":
        window.minimize()
    elif name == "Maximize":
        window.maximize()
    elif name == "Close":
        window.close(timestamp)
    else:
        raise ValueError("Unsupported taskbar action")


def show(shell, widget, event, xid: int, Gtk, Gdk, *, style_class="classic98-window-menu"):
    """Re-resolve the Wnck window both when opening and activating a menu item."""
    if event.button != 3 or shell._window_tracker is None:
        return False
    wnck = shell._window_tracker.wnck
    window = wnck.Window.get(xid)
    if window is None:
        return False
    menu = Gtk.Menu()
    menu.get_style_context().add_class(style_class)
    timestamp = int(event.time)
    for label, enabled in available_actions(window, wnck):
        if label == "Close":
            menu.append(Gtk.SeparatorMenuItem())
        item = Gtk.MenuItem(label=label)
        item.set_sensitive(enabled)

        def activate(_item, target=xid, action=label):
            live = wnck.Window.get(target)
            if live is None:
                return
            if dict(available_actions(live, wnck)).get(action):
                perform(live, action, Gtk.get_current_event_time())

        item.connect("activate", activate)
        menu.append(item)
    menu.show_all()
    menu.popup_at_pointer(event)
    return True
