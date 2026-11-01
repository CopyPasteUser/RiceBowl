"""Session-local, release-aware D-Bus toggle for the resident GTK window.

The method callback executes on the same GLib main loop as the window, so
sequential key presses cannot race against a stale visibility-state file.
"""

import logging
import os

from gi.repository import Gio, GLib


BUS_NAME = "io.github.copypasteuser.MacOSControlCenter"
OBJECT_PATH = "/io/github/copypasteuser/MacOSControlCenter"
INTERFACE = BUS_NAME

_INTROSPECTION = """
<node>
  <interface name="io.github.copypasteuser.MacOSControlCenter">
    <method name="ToggleIfCurrent">
      <arg name="script" type="s" direction="in"/>
      <arg name="version" type="s" direction="in"/>
      <arg name="handled" type="b" direction="out"/>
    </method>
  </interface>
</node>
"""


class ToggleService:
    """Expose one toggle endpoint while this resident owns the GTK window."""

    def __init__(self, on_toggle, script, version):
        self._on_toggle = on_toggle
        self._script = os.path.realpath(script)
        self._version = version
        self._connection = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._node = Gio.DBusNodeInfo.new_for_xml(_INTROSPECTION)
        self._registration_id = self._connection.register_object(
            OBJECT_PATH, self._node.lookup_interface(INTERFACE),
            self._on_method, None, None,
        )
        self._owner_id = Gio.bus_own_name_on_connection(
            self._connection, BUS_NAME, Gio.BusNameOwnerFlags.NONE, None, None,
        )

    def _on_method(self, connection, sender, object_path, interface, method,
                   parameters, invocation):
        handled = False
        if interface == INTERFACE and method == "ToggleIfCurrent":
            script, version = parameters.unpack()
            if version == self._version and os.path.realpath(script) == self._script:
                try:
                    self._on_toggle()
                    handled = True
                except Exception:
                    logging.exception("Control Center fast toggle failed")
        invocation.return_value(GLib.Variant("(b)", (handled,)))

    def close(self):
        if self._owner_id:
            Gio.bus_unown_name(self._owner_id)
            self._owner_id = 0
        if self._registration_id:
            self._connection.unregister_object(self._registration_id)
            self._registration_id = 0
