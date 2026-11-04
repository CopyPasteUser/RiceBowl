"""Win7 Action Center uses XFCE history and never creates another notifyd."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from macrice.riceware import pop
from macrice.win7_notifications import Win7Balloon, event_messages
from macrice.win7_tray import Win7Tray, recent_alerts
from tests.test_luna_riceware import tray


class FakeStyle:
    def __init__(self):
        self.classes = set()

    def add_class(self, name):
        self.classes.add(name)

    def remove_class(self, name):
        self.classes.discard(name)


class NotificationTests(unittest.TestCase):
    def test_native_history_is_bounded_and_keeps_original_entry_identities(self):
        entries = tuple(SimpleNamespace(identifier=str(i), summary=f"Item {i}")
                        for i in range(20))
        self.assertEqual(recent_alerts(entries), entries[:6])
        self.assertEqual(recent_alerts(entries, 1), (entries[0],))
        self.assertEqual(len(entries), 20)

    def test_balloon_is_distinct_but_uses_verified_event_source(self):
        self.assertEqual(Win7Balloon.css_prefix, "win7-balloon")
        self.assertIn("Windows 7", Win7Balloon.heading_text)
        self.assertEqual(event_messages(None, Mock()), ())

    def test_action_center_device_balloons_respect_native_quiet_mode(self):
        aero = tray(Win7Tray)
        balloon = Mock()
        aero.shell = SimpleNamespace(luna_balloon=balloon)
        for quiet in (True, None):
            with self.subTest(quiet=quiet), patch.object(pop, "quiet_mode", return_value=quiet):
                aero.announce("USB drive mounted")
        balloon.show.assert_not_called()
        with patch.object(pop, "quiet_mode", return_value=False):
            aero.announce("USB drive mounted")
        balloon.show.assert_called_once_with("USB drive mounted")

    def test_unread_indicator_is_real_and_not_a_fake_badge(self):
        aero = tray(Win7Tray)
        style = FakeStyle()
        button = Mock()
        button.get_style_context.return_value = style
        aero._alerts_button = button
        with patch.object(pop, "status", return_value=pop.NotificationStatus(True, True, False)):
            aero.refresh_alert_indicator()
        self.assertIn("win7-alert-unread", style.classes)
        self.assertIn("Unread", button.set_tooltip_text.call_args.args[0])
        with patch.object(pop, "status", return_value=pop.NotificationStatus(True, False, True)):
            aero.refresh_alert_indicator()
        self.assertNotIn("win7-alert-unread", style.classes)
        self.assertIn("Quiet", button.set_tooltip_text.call_args.args[0])
        with patch.object(pop, "status", return_value=pop.NotificationStatus(False, None, None)):
            aero.refresh_alert_indicator()
        self.assertIn("unavailable", button.set_tooltip_text.call_args.args[0])

    def test_mark_as_read_calls_only_the_shared_native_api(self):
        aero = tray(Win7Tray)
        aero._alerts_writing = False
        aero._alerts_busy = False
        aero._alerts_error = None
        aero.alerts_mark = Mock()
        aero.alerts_status = Mock()
        aero.popovers = {"alerts": Mock(get_visible=lambda: False)}
        aero._alerts_button = Mock(get_style_context=lambda: FakeStyle())
        with patch.object(pop, "mark_read", return_value=None) as mark, \
             patch.object(pop, "status", return_value=pop.NotificationStatus(True, False, False)):
            aero._mark_alerts()
        mark.assert_called_once_with()
        self.assertFalse(aero._alerts_writing)
        self.assertIsNone(aero._alerts_error)
        aero.alerts_status.set_text.assert_called_with("Marking notifications as read…")


if __name__ == "__main__":
    unittest.main()
