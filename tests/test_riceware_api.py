"""Renderer-facing contract and worker tests without a GTK main loop."""

import queue
import threading
import tempfile
import unittest
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from macrice import cli, riceware
from macrice.riceware import plate, pop, profiles, spice
from macrice.riceware.worker import MAX_PENDING, LatestRequestRunner


class RicewareApiTests(unittest.TestCase):
    def test_cli_manifest_requires_no_hardware(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["riceware", "manifest"]), 0)
        self.assertEqual(json.loads(output.getvalue())["api_version"], "1.0")

    def test_manifest_is_versioned_and_read_only(self):
        info = riceware.manifest()
        self.assertEqual(info["api_version"], "1.0")
        self.assertEqual(set(info["components"]),
                         {"riceSpice", "ricePop", "ricePlate", "riceWine"})
        self.assertEqual(set(spice.ACTION_SPECS), set(spice.WRITERS))
        from macrice.rice import STYLES

        self.assertEqual(set(profiles.PROFILE_FAMILIES), set(STYLES))
        self.assertEqual(profiles.family("aero-meadow"), "win7")
        with self.assertRaises(ValueError):
            profiles.family("unknown")

    def test_spice_action_metadata_rejects_bad_values_before_writes(self):
        invalid = (("audio_volume", 101), ("brightness", True),
                   ("bluetooth_connect", "not-mac"), ("wifi_connect", "ü" * 20),
                   ("wifi_disconnect", "oops"))
        for action, value in invalid:
            with self.subTest(action=action):
                self.assertEqual(spice.change(action, value).status, "error")
        self.assertEqual(spice.ACTION_SPECS["brightness"].minimum, 1)

    def test_wifi_scan_refresh_is_an_explicit_spice_operation(self):
        from unittest.mock import patch

        with patch.object(spice.hardware, "read_wifi_networks", return_value=("wifi",)) as read:
            result = spice.scan_wifi(rescan=True)
        self.assertEqual((result.status, result.value), ("ok", ("wifi",)))
        read.assert_called_once_with(rescan=True)
        with self.assertRaises(ValueError):
            spice.scan_wifi(rescan="yes")

    def test_aggregate_desktop_status_does_not_duplicate_snapshot_probes(self):
        from unittest.mock import patch

        with patch.object(spice, "read", return_value=spice.Result("test", "ok")) as read:
            spice.snapshot()
        self.assertNotIn("desktop_status", [call.args[0] for call in read.call_args_list])
        self.assertIn("desktop_status", spice.READERS)

    def test_runner_dispatches_to_ui_and_drops_stale_results(self):
        scheduled = queue.Queue()
        delivered = []
        entered, release = threading.Event(), threading.Event()

        def slow():
            entered.set()
            self.assertTrue(release.wait(2))
            return "old"

        with LatestRequestRunner(scheduled.put, workers=2) as runner:
            runner.submit("wifi", slow, delivered.append)
            self.assertTrue(entered.wait(1))
            runner.submit("wifi", lambda: "new", delivered.append)
            scheduled.get(timeout=2)()
            release.set()
            scheduled.get(timeout=2)()
            self.assertEqual([item.value for item in delivered], ["new"])

    def test_runner_exposes_errors_and_honors_close(self):
        scheduled = queue.Queue()
        delivered = []
        with LatestRequestRunner(scheduled.put, workers=1) as runner:
            def bad():
                raise RuntimeError("device unavailable")

            with self.assertLogs("macrice.riceware.worker", level="ERROR"):
                runner.submit("power", bad, delivered.append)
                scheduled.get(timeout=2)()
            self.assertEqual(delivered[0].error, "device unavailable")

        runner = LatestRequestRunner(scheduled.put, workers=1)
        runner.submit("status", lambda: 123, delivered.append)
        runner.close()
        scheduled.get(timeout=2)()
        self.assertEqual(len(delivered), 1)
        with self.assertRaises(RuntimeError):
            runner.submit("status", lambda: 0, delivered.append)

    def test_invalid_request_keys_do_not_start_work(self):
        runner = LatestRequestRunner(lambda callback: callback())
        try:
            with self.assertRaises(ValueError):
                runner.submit("", lambda: None, lambda _value: None)
        finally:
            runner.close()

    def test_runner_bounds_outstanding_keys_without_losing_later_work(self):
        scheduled = queue.Queue()
        entered, release = threading.Event(), threading.Event()

        def blocking():
            entered.set()
            release.wait(2)
            return 1

        runner = LatestRequestRunner(scheduled.put, workers=1)
        try:
            runner.submit("first", blocking, lambda _response: None)
            self.assertTrue(entered.wait(1))
            for index in range(MAX_PENDING - 1):
                runner.submit(f"item-{index}", lambda: None, lambda _response: None)
            with self.assertRaisesRegex(RuntimeError, "outstanding"):
                runner.submit("overflow", lambda: None, lambda _response: None)
        finally:
            runner.close()
            release.set()

    def test_notification_watch_unsubscribes_without_becoming_host(self):
        changes = []

        class FakeConnection:
            def __init__(self):
                self.callback = None
                self.unsubscribed = []

            def signal_subscribe(self, *args):
                self.callback = args[-1]
                return 19

            def signal_unsubscribe(self, subscription):
                self.unsubscribed.append(subscription)

        connection = FakeConnection()

        class FakeGio:
            class BusType:
                SESSION = 1

            class DBusSignalFlags:
                NONE = 0

            @staticmethod
            def bus_get(_kind, _cancel, ready):
                ready(None, "connection")

            @staticmethod
            def bus_get_finish(_result):
                return connection

        observer = pop.watch(lambda: changes.append("refresh"), Gio=FakeGio)
        connection.callback()
        observer.close()
        connection.callback()
        observer.close()
        self.assertEqual(changes, ["refresh"])
        self.assertEqual(connection.unsubscribed, [19])

    def test_desktop_launcher_metadata_is_bounded_and_never_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            victim = folder / "must-not-be-created"
            (folder / "good.desktop").write_text(
                "[Desktop Entry]\nName=Notes\nIcon=accessories-text-editor\n"
                f"Hidden=true\nExec=touch {victim}\n", encoding="utf-8")
            (folder / "huge.desktop").write_bytes(b"[Desktop Entry]\nName=" + b"x" * 200000)
            items = {item.filename: item for item in plate.snapshot(folder).items}
            self.assertEqual(items["good.desktop"].display_name, "Notes")
            self.assertEqual(items["good.desktop"].icon_name, "accessories-text-editor")
            self.assertTrue(items["good.desktop"].hidden)
            self.assertIsNone(items["huge.desktop"].display_name)
            self.assertFalse(victim.exists())


if __name__ == "__main__":
    unittest.main()
