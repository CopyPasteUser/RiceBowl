"""Shared settings-window WM contracts, independent of a running X server."""

from types import SimpleNamespace
from unittest import TestCase, mock

from macrice.rice_windows import configure_settings_window, draggable_caption


class FakeEventBox:
    def __init__(self):
        self.signals = {}
        self.accessible = mock.Mock()

    def set_visible_window(self, value):
        self.visible_window = value

    def set_can_focus(self, value):
        self.can_focus = value

    def set_tooltip_text(self, value):
        self.tooltip = value

    def get_accessible(self):
        return self.accessible

    def add(self, child):
        self.child = child

    def connect(self, name, callback):
        self.signals[name] = callback


class RiceWindowTests(TestCase):
    def test_settings_are_visible_wm_clients_not_always_above_popups(self):
        window = mock.Mock()
        Gdk = SimpleNamespace(WindowTypeHint=SimpleNamespace(NORMAL=42))
        configure_settings_window(window, Gdk, role="ricebowl-test-settings")
        window.set_type_hint.assert_called_once_with(42)
        window.set_skip_taskbar_hint.assert_called_once_with(False)
        window.set_skip_pager_hint.assert_called_once_with(False)
        window.set_keep_above.assert_called_once_with(False)
        window.set_resizable.assert_called_once_with(True)
        window.set_role.assert_called_once_with("ricebowl-test-settings")

    def test_title_is_draggable_maximizable_and_keyboard_accessible(self):
        window = mock.Mock()
        window.is_maximized.side_effect = [False, True, False]
        Gdk = SimpleNamespace(EventType=SimpleNamespace(BUTTON_PRESS=1, _2BUTTON_PRESS=2),
                              KEY_Return=13, KEY_KP_Enter=14, KEY_space=32)
        Gtk = SimpleNamespace(EventBox=FakeEventBox)
        contents = object()
        handle = draggable_caption(window, contents, Gtk, Gdk)
        self.assertIs(handle.child, contents)
        self.assertTrue(handle.can_focus)
        handle.accessible.set_name.assert_called_once()
        press = handle.signals["button-press-event"]
        self.assertFalse(press(None, SimpleNamespace(button=3, type=1)))
        self.assertTrue(press(None, SimpleNamespace(button=1, type=1,
                                                    x_root=135.5, y_root=90.4, time=1234)))
        window.begin_move_drag.assert_called_once_with(1, 135, 90, 1234)
        self.assertTrue(press(None, SimpleNamespace(button=1, type=2)))
        window.maximize.assert_called_once()
        keyboard = handle.signals["key-press-event"]
        self.assertTrue(keyboard(None, SimpleNamespace(keyval=13)))
        window.unmaximize.assert_called_once()
        self.assertFalse(keyboard(None, SimpleNamespace(keyval=70)))
