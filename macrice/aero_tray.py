"""Event-driven StatusNotifier host and fallback watcher for the optional Aero panel.

Supports SNI over the session bus; deliberately does not claim legacy XEmbed support.
Never modifies XFCE configuration or starts a compositor.
"""
from __future__ import annotations

import os
import re

WATCHER = "org.kde.StatusNotifierWatcher"
PATH = "/StatusNotifierWatcher"
IFACE = WATCHER
ITEM_IFACE = "org.kde.StatusNotifierItem"
MAX_ITEMS = 32

WATCHER_XML = """<node><interface name="org.kde.StatusNotifierWatcher">
<method name="RegisterStatusNotifierItem"><arg type="s" direction="in"/></method>
<method name="RegisterStatusNotifierHost"><arg type="s" direction="in"/></method>
<property name="RegisteredStatusNotifierItems" type="as" access="read"/>
<property name="IsStatusNotifierHostRegistered" type="b" access="read"/>
<property name="ProtocolVersion" type="i" access="read"/>
<signal name="StatusNotifierItemRegistered"><arg type="s"/></signal>
<signal name="StatusNotifierItemUnregistered"><arg type="s"/></signal>
<signal name="StatusNotifierHostRegistered"/>
</interface></node>"""


def parse_item_id(identifier: str) -> tuple[str, str] | None:
    """Accept a service name or service/path pair; reject arbitrary bus paths."""
    if not isinstance(identifier, str) or len(identifier) > 350:
        return None
    name, sep, rest = identifier.partition("/")
    if not re.fullmatch(r"(?::[0-9]+(?:\.[0-9]+)+|[A-Za-z_][A-Za-z_0-9-]*(?:\.[A-Za-z_0-9-]+)+)", name):
        return None
    path = "/" + rest if sep else "/StatusNotifierItem"
    if not re.fullmatch(r"/(?:[A-Za-z_0-9]+(?:/[A-Za-z_0-9]+)*)?", path):
        return None
    return name, path


def registration_id(service: str, sender: str) -> str | None:
    """An item registers either its object path or its service name."""
    if not service or len(service) > 350:
        return None
    if service.startswith("/"):
        candidate = sender + service
        return candidate if parse_item_id(candidate) else None
    return service if parse_item_id(service) else None


def unpack_variant(value):
    """PyGObject may return a plain Python value or a nested GLib.Variant."""
    return value.unpack() if callable(getattr(value, "unpack", None)) else value


def pixel_rgba(width: int, height: int, pixels: bytes) -> bytes | None:
    """Convert protocol ARGB32 byte arrays to GTK RGBA, with strict size limits."""
    if not (1 <= width <= 128 and 1 <= height <= 128) or len(pixels) != width * height * 4:
        return None
    result = bytearray(len(pixels))
    for index in range(0, len(pixels), 4):
        result[index:index + 4] = pixels[index + 1:index + 4] + pixels[index:index + 1]
    return bytes(result)


def select_tray_icons(items, visible_limit):
    """Select live SNI icons; prioritize attention without exposing Passive items."""
    active = [(identifier, status) for identifier, status in items
              if status in ("Active", "NeedsAttention")]
    if visible_limit is None:
        return tuple(identifier for identifier, _ in active), ()
    if not isinstance(visible_limit, int) or isinstance(visible_limit, bool) or visible_limit < 0:
        raise ValueError("visible_limit must be a non-negative integer or None")
    attention = [identifier for identifier, status in active if status == "NeedsAttention"]
    normal = [identifier for identifier, status in active if status == "Active"]
    visible = tuple((attention + normal)[:visible_limit])
    return visible, tuple(identifier for identifier, _ in active if identifier not in visible)


class StatusNotifierTray:
    """Register as host; own a watcher only if no existing one owns its bus name."""

    def __init__(self, box, Gtk, Gio, GLib, GdkPixbuf, *, visible_limit=None):
        self.box, self.Gtk, self.Gio, self.GLib, self.GdkPixbuf = box, Gtk, Gio, GLib, GdkPixbuf
        self.items = {}
        self.item_signals = {}
        self.item_state = {}
        self.visible_limit = visible_limit
        self.overflow_ids = ()
        self.overflow_button = None
        if visible_limit is not None:
            self.overflow_button = Gtk.Button(label="▴")
            self.overflow_button.get_style_context().add_class("win7-tray-chevron")
            self.overflow_button.set_relief(Gtk.ReliefStyle.NONE)
            self.overflow_button.get_accessible().set_name("Show hidden notification icons")
            self.overflow_button.set_tooltip_text("Show hidden notification icons")
            self.overflow_button.set_no_show_all(True)
            self.overflow_button.hide()
            self.overflow_button.connect("clicked", self._show_overflow)
            self.box.pack_start(self.overflow_button, False, False, 0)
        self.hosts = set()
        self.own_watcher = False
        self.registration = None
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.host_name = "org.kde.StatusNotifierHost-RiceBowl-" + str(os.getpid())
        self.host_owner = Gio.bus_own_name_on_connection(
            self.bus, self.host_name, Gio.BusNameOwnerFlags.NONE, self._host_acquired, None)
        self.watcher_owner = Gio.bus_own_name_on_connection(
            self.bus, WATCHER, Gio.BusNameOwnerFlags.NONE, self._acquired, self._lost)
        self.subscriptions = [
            self.bus.signal_subscribe(WATCHER, IFACE, None, PATH, None,
                                      Gio.DBusSignalFlags.NONE, self._watcher_signal),
            self.bus.signal_subscribe("org.freedesktop.DBus", "org.freedesktop.DBus",
                                      "NameOwnerChanged", "/org/freedesktop/DBus", None,
                                      Gio.DBusSignalFlags.NONE, self._name_changed),
        ]
        self._register_host()
        self._load_items()

    def _call(self, name, path, interface, method, parameters, signature=None, finished=None):
        def done(connection, result, _data=None):
            try:
                reply = connection.call_finish(result)
            except self.GLib.Error:
                return
            if finished:
                finished(reply)
        self.bus.call(name, path, interface, method, parameters,
                      self.GLib.VariantType.new(signature) if signature else None,
                      self.Gio.DBusCallFlags.NONE, 2000, None, done, None)

    def _host_acquired(self, _connection, _name):
        self._register_host()

    def _acquired(self, _connection, _name):
        self.own_watcher = True
        info = self.Gio.DBusNodeInfo.new_for_xml(WATCHER_XML)
        self.registration = self.bus.register_object(PATH, info.interfaces[0],
                                                       self._method, self._property, None)
        self._register_host()
        self._load_items()

    def _lost(self, _connection, _name):
        self.own_watcher = False
        if self.registration is not None:
            self.bus.unregister_object(self.registration)
            self.registration = None
        self.hosts.clear()
        self._reset_items()
        self._register_host()
        self._load_items()

    def _method(self, _conn, sender, _path, _iface, name, params, invocation):
        service = params.unpack()[0]
        if name == "RegisterStatusNotifierItem":
            identifier = registration_id(service, sender)
            if not identifier:
                invocation.return_dbus_error("org.freedesktop.DBus.Error.InvalidArgs", "Invalid item identifier")
                return
            if identifier not in self.items and len(self.items) >= MAX_ITEMS:
                invocation.return_dbus_error("org.freedesktop.DBus.Error.LimitsExceeded", "Tray is full")
                return
            self._add(identifier)
            self.bus.emit_signal(None, PATH, IFACE, "StatusNotifierItemRegistered",
                                 self.GLib.Variant("(s)", (identifier,)))
        elif name == "RegisterStatusNotifierHost" and service:
            self.hosts.add(service)
            self.bus.emit_signal(None, PATH, IFACE, "StatusNotifierHostRegistered", None)
        invocation.return_value(self.GLib.Variant("()", ()))

    def _property(self, _conn, _sender, _path, _iface, prop):
        if prop == "RegisteredStatusNotifierItems":
            return self.GLib.Variant("as", list(self.items))
        if prop == "IsStatusNotifierHostRegistered":
            return self.GLib.Variant("b", bool(self.hosts))
        if prop == "ProtocolVersion":
            return self.GLib.Variant("i", 0)
        return None

    def _register_host(self):
        self._call(WATCHER, PATH, IFACE, "RegisterStatusNotifierHost",
                   self.GLib.Variant("(s)", (self.host_name,)))

    def _load_items(self):
        def received(reply):
            try:
                identifiers = unpack_variant(reply.unpack()[0])
            except (IndexError, AttributeError, ValueError, TypeError):
                return
            for identifier in identifiers[:MAX_ITEMS]:
                self._add(identifier)
        self._call(WATCHER, PATH, "org.freedesktop.DBus.Properties", "Get",
                   self.GLib.Variant("(ss)", (IFACE, "RegisteredStatusNotifierItems")), "(v)", received)

    def _watcher_signal(self, _bus, _sender, _path, _iface, signal, params, _data=None):
        if signal == "StatusNotifierItemRegistered":
            self._add(params.unpack()[0])
        elif signal == "StatusNotifierItemUnregistered":
            self._remove(params.unpack()[0])

    def _name_changed(self, _bus, _sender, _path, _iface, _signal, params, _data=None):
        name, _old, new = params.unpack()
        if new:
            return
        for identifier in tuple(self.items):
            parsed = parse_item_id(identifier)
            if parsed and parsed[0] == name:
                self._remove(identifier)
                if self.own_watcher:
                    self.bus.emit_signal(None, PATH, IFACE, "StatusNotifierItemUnregistered",
                                         self.GLib.Variant("(s)", (identifier,)))
        self.hosts.discard(name)

    def _add(self, identifier):
        parsed = parse_item_id(identifier)
        if not parsed or identifier in self.items or len(self.items) >= MAX_ITEMS:
            return
        service, path = parsed
        button = self.Gtk.Button()
        button.get_style_context().add_class("aero-tray-icon")
        button.set_relief(self.Gtk.ReliefStyle.NONE)
        if self.visible_limit is not None:
            button.set_no_show_all(True)
            button.hide()
        img = self.Gtk.Image.new_from_icon_name("application-x-executable", self.Gtk.IconSize.MENU)
        button.add(img)
        button.connect("clicked", lambda _button: self._activate(service, path, "Activate",
                                                                self._button_position(_button)))
        button.connect("button-press-event",
                       lambda _button, event: self._context(service, path, event) if event.button == 3 else False)
        self.box.pack_start(button, False, False, 0)
        self.items[identifier] = (button, img)
        self.item_state[identifier] = ("Passive", service)
        self.item_signals[identifier] = self.bus.signal_subscribe(
            service, ITEM_IFACE, None, path, None, self.Gio.DBusSignalFlags.NONE,
            self._item_signal, identifier)
        self._refresh(identifier)
        self.box.show_all()

    def _remove(self, identifier):
        subscription = self.item_signals.pop(identifier, None)
        if subscription is not None:
            self.bus.signal_unsubscribe(subscription)
        item = self.items.pop(identifier, None)
        self.item_state.pop(identifier, None)
        if item:
            self.box.remove(item[0])
        self._reflow()

    def _reset_items(self):
        for identifier in tuple(self.items):
            self._remove(identifier)

    def _item_signal(self, _bus, _sender, _path, _iface, signal, _params, identifier):
        if signal in ("NewIcon", "NewAttentionIcon", "NewStatus", "NewTitle", "NewToolTip", "NewIconThemePath"):
            self._refresh(identifier)

    def _refresh(self, identifier):
        if identifier not in self.items:
            return
        service, path = parse_item_id(identifier)
        def received(reply):
            if identifier not in self.items:
                return
            try:
                props = {key: unpack_variant(value) for key, value in reply.unpack()[0].items()}
            except (IndexError, TypeError, ValueError, AttributeError):
                return
            button, img = self.items[identifier]
            status = props.get("Status")
            title = str(props.get("Title") or service)[:128]
            self.item_state[identifier] = (status, title)
            if status == "Passive":
                button.set_no_show_all(True)
                button.hide()
                self._reflow()
                return
            name = props.get("AttentionIconName") if props.get("Status") == "NeedsAttention" else None
            name = name or props.get("IconName")
            if isinstance(name, str) and name and not name.startswith("/"):
                img.set_from_icon_name(name, self.Gtk.IconSize.MENU)
            else:
                self._pixmap(img, props.get("IconPixmap") or ())
            button.set_tooltip_text(title)
            button.get_accessible().set_name(title)
            if self.visible_limit is None:
                button.set_no_show_all(False)
                button.show()
            else:
                self._reflow()
        self._call(service, path, "org.freedesktop.DBus.Properties", "GetAll",
                   self.GLib.Variant("(s)", (ITEM_IFACE,)), "(a{sv})", received)

    def _reflow(self):
        if self.visible_limit is None:
            return
        visible, self.overflow_ids = select_tray_icons(
            ((identifier, self.item_state.get(identifier, ("Passive", ""))[0])
             for identifier in self.items), self.visible_limit)
        visible_set = set(visible)
        for identifier, (button, _image) in self.items.items():
            should_show = identifier in visible_set
            button.set_no_show_all(not should_show)
            button.set_visible(should_show)
        has_overflow = bool(self.overflow_ids)
        self.overflow_button.set_no_show_all(not has_overflow)
        self.overflow_button.set_visible(has_overflow)
        self.overflow_button.set_tooltip_text(
            f"Show {len(self.overflow_ids)} hidden notification icons" if has_overflow
            else "Show hidden notification icons")

    def _show_overflow(self, button):
        """A bounded GTK menu escapes the narrow dock and stays keyboard-operable."""
        from gi.repository import Gdk, Pango

        if not self.overflow_ids:
            return
        menu = self.Gtk.Menu()
        menu.get_style_context().add_class("win7-tray-overflow-menu")
        for identifier in self.overflow_ids:
            if identifier not in self.items:
                continue
            service, path = parse_item_id(identifier)
            _button, icon = self.items[identifier]
            title = self.item_state.get(identifier, ("", service))[1]
            item = self.Gtk.MenuItem()
            content = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=9)
            image = self.Gtk.Image()
            if icon.get_storage_type() == self.Gtk.ImageType.PIXBUF:
                image.set_from_pixbuf(icon.get_pixbuf())
            elif icon.get_storage_type() == self.Gtk.ImageType.ICON_NAME:
                image.set_from_icon_name(icon.get_icon_name()[0], self.Gtk.IconSize.MENU)
            content.pack_start(image, False, False, 0)
            label = self.Gtk.Label(label=title, xalign=0)
            label.set_max_width_chars(30)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            content.pack_start(label, True, True, 0)
            item.add(content)
            item.connect("activate", lambda _item, s=service, p=path:
                         self._activate(s, p, "Activate", self._button_position(button)))
            item.connect("button-press-event", lambda _item, event, s=service, p=path:
                         self._context(s, p, event))
            menu.append(item)
        menu.connect("deactivate", lambda widget: widget.destroy())
        menu.show_all()
        menu.popup_at_widget(button, Gdk.Gravity.NORTH_WEST, Gdk.Gravity.SOUTH_WEST, None)

    def _pixmap(self, image, pixmaps):
        for width, height, raw in sorted(pixmaps, key=lambda p: p[0] * p[1]):
            if width < 16 or height < 16:
                continue
            rgba = pixel_rgba(width, height, bytes(raw))
            if rgba is not None:
                pixbuf = self.GdkPixbuf.Pixbuf.new_from_bytes(
                    self.GLib.Bytes.new(rgba), self.GdkPixbuf.Colorspace.RGB,
                    True, 8, width, height, width * 4)
                image.set_from_pixbuf(pixbuf.scale_simple(20, 20, self.GdkPixbuf.InterpType.BILINEAR))
                return
        image.set_from_icon_name("application-x-executable", self.Gtk.IconSize.MENU)

    @staticmethod
    def _button_position(button):
        window = button.get_window()
        if window is None:
            return (0, 0)
        x, y = window.get_origin()
        allocation = button.get_allocation()
        return (int(x + allocation.width // 2), int(y + allocation.height // 2))

    def _activate(self, service, path, method, position=(0, 0)):
        self._call(service, path, ITEM_IFACE, method, self.GLib.Variant("(ii)", position))

    def _context(self, service, path, event):
        if event.button == 3:
            self._activate(service, path, "ContextMenu",
                           (int(event.x_root), int(event.y_root)))
            return True
        return False

    def close(self):
        for subscription in self.subscriptions:
            self.bus.signal_unsubscribe(subscription)
        if self.registration is not None:
            self.bus.unregister_object(self.registration)
        self.Gio.bus_unown_name(self.watcher_owner)
        self.Gio.bus_unown_name(self.host_owner)
        self._reset_items()
