"""MPRIS media integration uses allowlisted session bus calls, never a daemon."""

import unittest
from types import SimpleNamespace
from unittest import mock

from macrice.riceware import media


class Variant:
    def __init__(self, payload):
        self.payload = payload

    def unpack(self):
        return self.payload


class FakeBus:
    def __init__(self, *, can_next=True):
        self.status = "Paused"
        self.can_next = can_next
        self.calls = []

    def call_sync(self, bus_name, path, interface, method, params, *args):
        self.calls.append((bus_name, path, interface, method))
        if method == "ListNames":
            return Variant((["org.mpris.MediaPlayer2.music", "org.other.Unrelated"],))
        if method == "GetAll":
            return Variant(({"PlaybackStatus": self.status,
                             "Metadata": {"xesam:title": "Track", "xesam:artist": ["Artist"]},
                             "CanControl": True, "CanPlay": True, "CanPause": True,
                             "CanGoNext": self.can_next, "CanGoPrevious": False},))
        if method == "PlayPause":
            self.status = "Playing" if self.status != "Playing" else "Paused"
            return Variant(())
        return Variant(())


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        gio = SimpleNamespace(
            BusType=SimpleNamespace(SESSION=0),
            DBusCallFlags=SimpleNamespace(NONE=0),
            bus_get_sync=lambda *_args: self.bus,
        )
        glib = SimpleNamespace(Variant=lambda _sig, value: Variant(value),
                               VariantType=lambda signature: signature)
        patch = mock.patch.object(media, "_gio", return_value=(gio, glib))
        patch.start()
        self.addCleanup(patch.stop)

    def test_read_is_bounded_to_real_mpris_names_and_displays_metadata(self):
        players = media.read_media_players()
        self.assertEqual(len(players), 1)
        self.assertEqual(players[0].title, "Track")
        self.assertEqual(players[0].artist, "Artist")
        self.assertEqual(players[0].status, "Paused")
        self.assertTrue(players[0].can_play_pause)
        self.assertFalse(players[0].can_previous)
        self.assertEqual(len(self.bus.calls), 2)

    def test_play_pause_requires_capability_and_rechecks_actual_state(self):
        after = media.media_action("org.mpris.MediaPlayer2.music", "PlayPause")
        self.assertEqual(after[0].status, "Playing")
        self.assertEqual([call[3] for call in self.bus.calls],
                         ["GetAll", "PlayPause", "GetAll"])

    def test_invalid_command_and_bus_name_never_touch_session_bus(self):
        with self.assertRaises(ValueError):
            media.media_action("org.freedesktop.DBus", "PlayPause")
        with self.assertRaises(ValueError):
            media.media_action("org.mpris.MediaPlayer2.music", "Eval")
        self.assertEqual(self.bus.calls, [])

    def test_unsupported_player_action_never_dispatches_command(self):
        self.bus.can_next = False
        with self.assertRaisesRegex(RuntimeError, "does not permit"):
            media.media_action("org.mpris.MediaPlayer2.music", "Next")
        self.assertEqual([call[3] for call in self.bus.calls], ["GetAll"])

    def test_unresponsive_playback_never_claims_success(self):
        original = self.bus.call_sync

        def unresponsive(*args):
            if args[3] == "PlayPause":
                self.bus.calls.append((args[0], args[1], args[2], args[3]))
                return Variant(())
            return original(*args)

        self.bus.call_sync = unresponsive
        with mock.patch.object(media.time, "sleep") as sleep:
            with self.assertRaisesRegex(RuntimeError, "did not confirm"):
                media.media_action("org.mpris.MediaPlayer2.music", "PlayPause")
        self.assertEqual(sleep.call_count, 3)

    def test_missing_session_bus_reports_error_without_faking_a_player(self):
        with mock.patch.object(media, "_gio", side_effect=RuntimeError("absent")):
            with self.assertRaisesRegex(RuntimeError, "not available"):
                media.read_media_players()


if __name__ == "__main__":
    unittest.main()
