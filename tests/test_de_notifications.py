"""The Wayland RicePop read bridge cannot own, replay or mutate notifications."""

import json
import subprocess
import unittest
from unittest import mock

from macrice.cli import main
from macrice.de import notifications


class WaylandRicePopReadTests(unittest.TestCase):
    def test_reads_mako_live_and_history_without_replaying_actions(self):
        active = [{"id": 12, "summary": "Download", "body": "Finished",
                   "app_name": "Files", "urgency": "normal",
                   "actions": {"dangerous": "Delete file"}}]
        finished = [{"id": 13, "summary": "Mail", "body": "Private message",
                     "app_name": "Mail", "urgency": "low"}]
        def fake_run(args, **options):
            self.assertEqual(args[0], "/usr/bin/makoctl")
            self.assertEqual(args[-1], "-j")
            self.assertTrue(options["capture_output"])
            return subprocess.CompletedProcess(args, 0,
                   json.dumps(active if args[1] == "list" else finished).encode(), b"")
        with mock.patch("macrice.de.notifications.shutil.which", return_value="/usr/bin/makoctl"), \
             mock.patch("macrice.de.notifications.subprocess.run", side_effect=fake_run):
            result = notifications.inspect()
        self.assertTrue(result["read_only"])
        self.assertFalse(result["mutates_active_desktop"])
        self.assertFalse(result["actions_replayed"])
        self.assertEqual(result["active"][0]["summary"], "Download")
        self.assertNotIn("actions", result["active"][0])
        self.assertEqual(result["history"][0]["id"], 13)

    def test_missing_backend_invalid_reply_and_overlong_history_fail_closed(self):
        with mock.patch("macrice.de.notifications.shutil.which", return_value=None):
            with self.assertRaises(notifications.NotificationBridgeError):
                notifications.inspect()
        for payload in (b"[]junk", b'{}', b'[{"id": true}]', b'x' * (128 * 1024 + 1)):
            with self.subTest(payload=payload[:20]):
                with self.assertRaises(notifications.NotificationBridgeError):
                    notifications._records(payload)
        limited, truncated = notifications._records(json.dumps([
            {"id": x + 1, "summary": "abc"} for x in range(80)]).encode())
        self.assertEqual(len(limited), 64)
        self.assertTrue(truncated)

    def test_machine_cli_returns_error_without_printing_private_paths(self):
        with mock.patch("macrice.de.notifications.shutil.which", return_value=None), \
             mock.patch("builtins.print") as printed:
            self.assertEqual(main(["de", "notifications", "--json"]), 2)
            output = json.loads(printed.call_args.args[0])
        self.assertEqual(output["error"]["code"], "notifications_unavailable")
        self.assertFalse(output["ok"])


if __name__ == "__main__":
    unittest.main()
