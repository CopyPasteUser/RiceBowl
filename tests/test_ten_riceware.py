"""Hermetic Windows 10 Riceware renderer tests; no live device mutations."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from macrice.riceware import spice
from macrice.riceware.worker import Response
from macrice.riceware.pop import Notification
from macrice.ten_riceware import TenController, group_notifications, switch_state


class Runner:
    def __init__(self):
        self.queued = []
        self.closed = False

    def submit(self, key, operation, callback):
        self.queued.append((key, operation, callback))

    def deliver(self):
        key, operation, callback = self.queued.pop(0)
        try:
            response = Response(key, 1, value=operation())
        except Exception as exc:
            response = Response(key, 1, error=str(exc))
        callback(response)

    def close(self):
        self.closed = True


class Button:
    def __init__(self):
        self.active = False
        self.sensitive = None
        self.callback = None

    def set_active(self, value):
        self.active = value

    def set_sensitive(self, value):
        self.sensitive = value

    def set_tooltip_text(self, value):
        self.tooltip = value

    def connect(self, _signal, callback, *args):
        self.callback = lambda: callback(self, *args)


class Label:
    def set_text(self, value):
        self.text = value


class Box:
    def __init__(self):
        self.children = []

    def get_children(self):
        return list(self.children)

    def remove(self, child):
        self.children.remove(child)

    def show_all(self):
        pass


class Shell:
    def __init__(self):
        self.refreshed = 0

    def _refresh_status_async(self):
        self.refreshed += 1


class Win10RicewareTests(unittest.TestCase):
    def setUp(self):
        self.runner = Runner()
        self.shell = Shell()
        self.controller = TenController(self.shell, None, None, runner=self.runner)
        self.buttons = {name: Button() for name in ("wifi", "bluetooth", "quiet")}
        self.history = Box()
        self.message = Label()
        self.mark = Button()
        self.feedback = Label()
        self.clear = Button()
        self.confirmation = type("Confirmation", (), {"hide": lambda _: None})()
        self.controller.bind(switches=self.buttons, history_box=self.history,
                             history_message=self.message, mark_button=self.mark,
                             feedback=self.feedback, clear_button=self.clear,
                             confirmation=self.confirmation)

    def tearDown(self):
        self.controller.close()

    def test_unavailable_devices_remain_disabled_not_off(self):
        results = (spice.Result("wifi", "unavailable"),
                   spice.Result("bluetooth", "error"), None)
        self.assertEqual(switch_state(results), {
            "wifi": (None, False), "bluetooth": (None, False),
            "quiet": (None, False)})

    def test_readback_maps_actual_radio_and_focus_assist(self):
        class Bluetooth:
            powered = True

        values = switch_state((spice.Result("wifi", "ok", False),
                               spice.Result("bluetooth", "ok", Bluetooth()), True))
        self.assertEqual(values, {"wifi": (False, True),
                                  "bluetooth": (True, True),
                                  "quiet": (True, True)})

    def test_status_probe_uses_spice_and_returns_none_when_unavailable(self):
        received = []
        with patch("macrice.ten_riceware.spice.read", return_value=spice.Result(
                "desktop_status", "unavailable")) as read:
            self.controller.refresh_status(received.append)
            self.runner.deliver()
        read.assert_called_once_with("desktop_status")
        self.assertEqual(received, [None])

    def test_volume_error_never_claims_success(self):
        received = []
        with patch("macrice.ten_riceware.spice.change", return_value=spice.Result(
                "audio_volume", "error", reason="Readback mismatch")):
            self.controller.change_audio("audio_volume", 37,
                                         lambda state, error: received.append((state, error)))
            self.runner.deliver()
        self.assertEqual(received, [(None, "Readback mismatch")])

    def test_stale_history_does_not_repopulate_hidden_flyout(self):
        self.controller.opened = True
        with patch("macrice.ten_riceware.pop.history", return_value=()):
            self.controller.refresh_history()
            self.controller.discard()
            self.runner.deliver()
        self.assertEqual(self.history.children, [])
        self.assertFalse(self.mark.sensitive)

    def test_wifi_toggle_requires_verified_change_before_ui_update(self):
        self.controller.opened = True
        self.controller._states["wifi"] = (False, True)
        self.buttons["wifi"].set_sensitive(True)
        with patch("macrice.ten_riceware.spice.change", return_value=spice.Result(
                "wifi", "error", reason="Readback mismatch")) as write:
            self.buttons["wifi"].callback()
            self.assertFalse(self.buttons["wifi"].active)
            self.assertFalse(self.buttons["wifi"].sensitive)
            self.runner.deliver()
        write.assert_called_once_with("wifi", True)
        self.assertIn("Readback mismatch", self.feedback.text)
        self.assertEqual(self.shell.refreshed, 1)

    def test_focus_assist_failure_does_not_flip_toggled_state(self):
        self.controller.opened = True
        self.controller._states["quiet"] = (False, True)
        with patch("macrice.ten_riceware.pop.set_quiet_mode",
                   side_effect=RuntimeError("Permission denied")):
            self.buttons["quiet"].callback()
            self.runner.deliver()
        self.assertFalse(self.buttons["quiet"].active)
        self.assertIn("Permission denied", self.feedback.text)

    def test_periodic_read_does_not_reenable_pending_switch(self):
        class Bluetooth:
            powered = False

        self.controller.opened = True
        self.controller._states["wifi"] = (False, True)
        self.buttons["wifi"].callback()
        self.assertFalse(self.buttons["wifi"].sensitive)

        def probe(name):
            if name == "wifi":
                return spice.Result(name, "ok", False)
            return spice.Result(name, "ok", Bluetooth())

        with patch("macrice.ten_riceware.spice.read", side_effect=probe), \
             patch("macrice.ten_riceware.pop.quiet_mode", return_value=False):
            self.controller.refresh_switches()
            # Deliver the radio read before the queued hardware write.
            self.runner.queued[0], self.runner.queued[1] = (
                self.runner.queued[1], self.runner.queued[0])
            self.runner.deliver()
        self.assertFalse(self.buttons["wifi"].sensitive)

    def test_notification_watch_closes_with_shell(self):
        class Watch:
            closed = False

            def close(self):
                self.closed = True

        observer = Watch()
        with patch("macrice.ten_riceware.pop.watch", return_value=observer):
            self.controller.on_open()
        self.controller.close()
        self.assertTrue(observer.closed)
        self.assertTrue(self.runner.closed)

    def test_notification_actions_are_explicit_and_bounded(self):
        self.controller.opened = True
        self.controller._ids = ("valid-id",)
        with patch("macrice.ten_riceware.pop.mark_read") as mark:
            self.controller.mark_read()
            self.runner.deliver()
        mark.assert_called_once_with(("valid-id",))
        self.assertFalse(self.mark.sensitive)

    def test_notifications_group_by_actual_application_in_first_seen_order(self):
        def entry(identifier, application):
            return Notification(identifier, "12:30", application, "dialog-information",
                                "Notice", "Body", False)

        items = (entry("1", "Mail"), entry("2", "Files"), entry("3", "Mail"))
        self.assertEqual(tuple((app, tuple(item.identifier for item in entries))
                               for app, entries in group_notifications(items)),
                         (("Mail", ("1", "3")), ("Files", ("2",))))

    def test_clear_all_is_async_and_only_touches_xfce_history_on_confirmation(self):
        self.controller.opened = True
        with patch("macrice.ten_riceware.pop.clear_history") as clear, \
             patch("macrice.ten_riceware.pop.history", return_value=()):
            self.assertEqual(self.runner.queued, [])
            self.controller.clear_history()
            self.assertFalse(self.clear.sensitive)
            self.assertFalse(self.mark.sensitive)
            self.assertEqual(len(self.runner.queued), 1)
            self.runner.deliver()
            clear.assert_called_once_with()
            self.runner.deliver()
        self.assertFalse(self.clear.sensitive)
        self.assertIn("cleared", self.feedback.text)

    def test_failed_clear_preserves_history_and_reports_error(self):
        self.controller.opened = True
        with patch("macrice.ten_riceware.pop.clear_history",
                   side_effect=RuntimeError("XFCE permission denied")), \
             patch("macrice.ten_riceware.pop.history", return_value=()):
            self.controller.clear_history()
            self.runner.deliver()
            self.assertIn("XFCE permission denied", self.feedback.text)
            self.runner.deliver()

    def test_close_releases_runner_and_prevents_reopen(self):
        self.controller.close()
        self.assertTrue(self.runner.closed)
        with patch("macrice.ten_riceware.pop.watch") as watch:
            self.controller.on_open()
        watch.assert_not_called()
        self.assertFalse(self.controller.opened)


if __name__ == "__main__":
    unittest.main()
