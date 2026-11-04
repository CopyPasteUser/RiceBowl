"""Contract tests for the real Xfce notification-log adapter; no live bus."""

import subprocess
import unittest
from unittest.mock import patch

from macrice import chrome_notification_backend as notifications


def row(identifier="abc", *, read=False, app="Browser", summary="New message",
        body="<b>Hi</b> &amp; welcome", icon="web-browser", timestamp=1730760000000000):
    return (identifier, timestamp, "UTC", "browser.desktop", app, icon,
            summary, body, (("reply", "Reply"),), 5000, read)


class NotificationBackendTests(unittest.TestCase):
    def test_notification_log_schema_and_sanitization(self):
        items = notifications.parse_entries((row(),))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].application, "Browser")
        self.assertEqual(items[0].body, "Hi & welcome")
        self.assertFalse(items[0].is_read)
        self.assertNotIn("reply", repr(items[0]))

    def test_rejects_malformed_ids_and_rows(self):
        items = notifications.parse_entries((row(""), ("bad",), "bad", row("valid")))
        self.assertEqual([item.identifier for item in items], ["valid"])

    def test_escaped_and_bounded_untrusted_text(self):
        malicious = row(icon="../../etc/passwd", summary="<script>" + "A" * 500,
                        body="&lt;safe&gt;" + "b" * 900)
        item = notifications.parse_entries((malicious,))[0]
        self.assertEqual(item.icon, "dialog-information")
        self.assertLessEqual(len(item.summary), 160)
        self.assertLessEqual(len(item.body), 480)
        self.assertNotIn("<script>", item.summary)

    def test_unexpected_timestamp_never_crashes(self):
        item = notifications.parse_entries((row(timestamp=None),))[0]
        self.assertEqual(item.timestamp, "Time unavailable")

    def test_hard_limit_for_big_logs(self):
        items = notifications.parse_entries(row(str(index)) for index in range(600))
        self.assertEqual(len(items), notifications.MAX_ITEMS)

    def test_unread_requires_real_boolean_result(self):
        with patch.object(notifications, "_call", return_value=(True,)):
            self.assertTrue(notifications.has_unread())
        with patch.object(notifications, "_call", return_value=(1,)):
            with self.assertRaises(notifications.NotificationUnavailable):
                notifications.has_unread()

    def test_mark_all_does_not_fabricate_notification_actions(self):
        with patch.object(notifications, "_call") as call:
            notifications.mark_read()
            notifications.clear_notifications()
        self.assertEqual(call.call_args_list[0].args, ("MarkAllRead",))
        self.assertEqual(call.call_args_list[1].args, ("Clear",))

    @patch.object(notifications.shutil, "which", return_value="/usr/bin/xfconf-query")
    def test_dnd_needs_exact_linux_state(self, _which):
        with patch.object(notifications.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, "false\n", "")):
            self.assertIs(notifications.read_dnd(), False)
        with patch.object(notifications.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 1, "", "not found")):
            self.assertIsNone(notifications.read_dnd())

    def test_dnd_write_requires_supported_provider(self):
        with patch.object(notifications, "read_dnd", return_value=None):
            with self.assertRaises(notifications.NotificationUnavailable):
                notifications.set_dnd(True)

    @patch.object(notifications, "read_dnd", side_effect=[False, True])
    def test_dnd_write_is_read_back_verified(self, _dnd):
        with patch.object(notifications.subprocess, "run",
                          return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            self.assertTrue(notifications.set_dnd(True))
        self.assertEqual(run.call_args.args[0][-1], "true")


if __name__ == "__main__":
    unittest.main()
