"""Event balloons use only actual observed transitions, never startup guesses."""

import unittest

from macrice.hardware_status import BatteryState, DesktopStatus, SoundState
from macrice.luna_notifications import event_messages, removable_mount_message


def status(network="wifi", battery=None):
    return DesktopStatus(battery, network, SoundState(None, None))


class LunaNotificationTests(unittest.TestCase):
    def test_removable_mount_notifications_are_truthful_and_bounded(self):
        class Drive:
            def __init__(self, removable):
                self.removable = removable

            def is_removable(self):
                return self.removable

            def is_media_removable(self):
                return False

        class Volume:
            def __init__(self, drive):
                self.drive = drive

            def get_drive(self):
                return self.drive

        class Mount:
            def __init__(self, drive):
                self.volume = Volume(drive) if drive else None

            def get_volume(self):
                return self.volume

            def get_name(self):
                return "USB\nPhotos"

        removable = Mount(Drive(True))
        self.assertEqual(removable_mount_message(removable, added=True),
                         "USB Photos is ready to use")
        self.assertEqual(removable_mount_message(removable, added=False),
                         "USB Photos was unmounted")
        self.assertIsNone(removable_mount_message(Mount(Drive(False)), added=True))
        self.assertIsNone(removable_mount_message(Mount(None), added=False))
        self.assertIsNone(removable_mount_message(object(), added=True))

    def test_startup_and_steady_state_have_no_balloon(self):
        current = status("wifi", BatteryState(18, False, "Discharging"))
        self.assertEqual(event_messages(None, current), ())
        self.assertEqual(event_messages(current, current), ())

    def test_network_transitions_are_real(self):
        self.assertEqual(event_messages(status("offline"), status("wifi")),
                         ("Connected using Wi-Fi",))
        self.assertEqual(event_messages(status("ethernet"), status("offline")),
                         ("Network connection lost",))
        self.assertEqual(event_messages(status("wifi"), status("ethernet")), ())

    def test_battery_crossing_does_not_repeat(self):
        self.assertEqual(event_messages(
            status(battery=BatteryState(16, False, "Discharging")),
            status(battery=BatteryState(14, False, "Discharging"))),
            ("Battery low — 14% remaining",))
        self.assertEqual(event_messages(
            status(battery=BatteryState(14, False, "Discharging")),
            status(battery=BatteryState(13, False, "Discharging"))), ())
        self.assertEqual(event_messages(
            status(battery=BatteryState(20, True, "Charging")),
            status(battery=BatteryState(15, False, "Discharging"))),
            ("Battery low — 15% remaining",))


if __name__ == "__main__":
    unittest.main()
