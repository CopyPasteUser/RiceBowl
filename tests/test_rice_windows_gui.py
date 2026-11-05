"""Actual GTK3 toplevel contract; exercised by Xvfb in the GitHub CI job."""

import unittest
from types import SimpleNamespace
from unittest import mock


class RiceWindowsGtkTests(unittest.TestCase):
    def test_real_eventbox_title_strip_and_wm_hints(self):
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, Gtk
        from macrice.rice_windows import configure_settings_window, draggable_caption

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("GTK display unavailable; native Xvfb CI supplies one")

        window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        window.set_decorated(False)
        window.set_default_size(450, 330)
        configure_settings_window(window, Gdk, role="ricebowl-test-settings")
        caption = draggable_caption(window, Gtk.Label(label="Settings"), Gtk, Gdk)
        window.add(caption)
        try:
            window.show_all()
            while Gtk.events_pending():
                Gtk.main_iteration_do(False)
            self.assertTrue(window.get_visible())
            self.assertTrue(caption.get_visible())
            self.assertTrue(caption.get_can_focus())
            self.assertEqual(window.get_type_hint(), Gdk.WindowTypeHint.NORMAL)
            self.assertFalse(window.get_skip_taskbar_hint())
            self.assertFalse(window.get_skip_pager_hint())
        finally:
            window.destroy()

    def test_aqua_settings_bluetooth_buttons_dispatch_verified_backend_actions(self):
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk
        from macrice.frutiger_native_controls import NativeAquaControls
        from macrice.hardware_status import BluetoothDevice, BluetoothState

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("GTK display unavailable; native Xvfb CI supplies one")

        device = BluetoothDevice("00:11:22:33:44:55", "Nearby headset", False, False)
        state = BluetoothState(True, (), (device,), "D-Bus")
        backend = mock.Mock()
        backend.read_bluetooth.return_value = state
        backend.scan_bluetooth_devices.return_value = state
        backend.pair_bluetooth_device.return_value = state

        class InlineRunner:
            def submit(self, _key, job, callback):
                callback(SimpleNamespace(error=None, value=job()))

        window = Gtk.Window()
        parent = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        window.add(parent)
        shell = SimpleNamespace(_class=lambda widget, _name: widget)
        panel = NativeAquaControls(shell, Gtk, GLib, parent, is_current=lambda: True,
                                   backend=backend, runner=InlineRunner())
        panel.bluetooth()
        window.show_all()

        def find(button_text, root):
            if isinstance(root, Gtk.Button) and root.get_label() == button_text:
                return root
            if isinstance(root, Gtk.Container):
                for child in root.get_children():
                    found = find(button_text, child)
                    if found is not None:
                        return found
            return None

        try:
            pair = find("Pair…", parent)
            self.assertIsNotNone(pair)
            pair.clicked()
            backend.pair_bluetooth_device.assert_called_once_with(device.address)
            scan = find("Scan for nearby devices (9 s)", parent)
            self.assertIsNotNone(scan)
            scan.clicked()
            self.assertEqual(backend.scan_bluetooth_devices.call_args.kwargs["duration"], 9)
            event = backend.scan_bluetooth_devices.call_args.kwargs["cancel"]
            self.assertFalse(event.is_set())
            panel.dispose()
            self.assertTrue(event.is_set())
        finally:
            panel.dispose()
            window.destroy()
