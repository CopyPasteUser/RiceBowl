"""BlueZ system D-Bus transport, independent of the bluetoothctl executable.

BlueZ is the Linux Bluetooth stack; bluetoothctl and this module are separate
control interfaces to that stack. All calls are bounded and run off the UI thread.
"""

from __future__ import annotations


def _connection():
    from gi.repository import Gio

    return Gio, Gio.bus_get_sync(Gio.BusType.SYSTEM, None)


def _objects():
    from gi.repository import GLib

    Gio, bus = _connection()
    answer = bus.call_sync(
        "org.bluez", "/", "org.freedesktop.DBus.ObjectManager",
        "GetManagedObjects", None, GLib.VariantType.new("(a{oa{sa{sv}}})"),
        Gio.DBusCallFlags.NONE, 2500, None,
    )
    return answer.unpack()[0]


def _value(value):
    return value.unpack() if hasattr(value, "unpack") else value


def snapshot():
    """Return (powered, adapter path, [(address, name, paired, connected)]).

    An empty list is a valid adapter with no cached devices; no adapter is an
    error, distinct from an adapter that is switched off.
    """
    objects = _objects()
    adapters = sorted((path, props["org.bluez.Adapter1"])
                      for path, props in objects.items()
                      if "org.bluez.Adapter1" in props)
    if not adapters:
        raise RuntimeError("No BlueZ adapter is available on system D-Bus")
    path, adapter = adapters[0]
    powered = _value(adapter.get("Powered"))
    if not isinstance(powered, bool):
        raise RuntimeError("Adapter power state is missing")
    devices = []
    for device_path, interfaces in objects.items():
        props = interfaces.get("org.bluez.Device1")
        if not props or not device_path.startswith(path + "/"):
            continue
        address = _value(props.get("Address"))
        if not isinstance(address, str) or not address:
            continue
        alias = _value(props.get("Alias")) or _value(props.get("Name"))
        devices.append((address, str(alias or address),
                        bool(_value(props.get("Paired"))),
                        bool(_value(props.get("Connected")))))
    return powered, path, tuple(sorted(devices, key=lambda item: item[1].casefold()))[:32]


def set_power(adapter_path: str, enabled: bool) -> None:
    from gi.repository import GLib

    Gio, bus = _connection()
    bus.call_sync(
        "org.bluez", adapter_path, "org.freedesktop.DBus.Properties",
        "Set", GLib.Variant("(ssv)",
                            ("org.bluez.Adapter1", "Powered", GLib.Variant("b", enabled))),
        None, Gio.DBusCallFlags.NONE, 4000, None,
    )


def set_connection(address: str, connected: bool) -> None:
    """Act only on a device path resolved from live BlueZ objects."""
    objects = _objects()
    for path, interfaces in objects.items():
        props = interfaces.get("org.bluez.Device1", {})
        if _value(props.get("Address")) != address:
            continue
        if connected and not bool(_value(props.get("Paired"))):
            raise ValueError("Pair the device in Bluetooth settings first")
        Gio, bus = _connection()
        bus.call_sync(
            "org.bluez", path, "org.bluez.Device1",
            "Connect" if connected else "Disconnect", None, None,
            Gio.DBusCallFlags.NONE, 8000, None,
        )
        return
    raise ValueError("Bluetooth device is no longer available")
