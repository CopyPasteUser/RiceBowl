"""Protocol-level tests for Aero SNI logic without a D-Bus session."""
import unittest

from macrice.aero_tray import (StatusNotifierTray, parse_item_id, registration_id,
                              pixel_rgba, select_tray_icons, MAX_ITEMS, WATCHER_XML,
                              unpack_variant)


class AeroTrayTests(unittest.TestCase):
    def test_service_and_object_path(self):
        self.assertEqual(parse_item_id("org.example.Tray"), ("org.example.Tray", "/StatusNotifierItem"))
        self.assertEqual(parse_item_id(":1.25/StatusNotifierItem"), (":1.25", "/StatusNotifierItem"))
        for invalid in ("", "broken", "org.example.Tray/../../bad", ":bad/Item", "org.example.Tray//x"):
            self.assertIsNone(parse_item_id(invalid))

    def test_path_registration_scoped_to_sender(self):
        self.assertEqual(registration_id("/StatusNotifierItem", ":1.25"), ":1.25/StatusNotifierItem")
        self.assertEqual(registration_id("org.example.Tray", ":1.25"), "org.example.Tray")
        self.assertIsNone(registration_id("/../x", ":1.25"))

    def test_variant_unpack_accepts_nested_variant_and_plain_python_values(self):
        class FakeVariant:
            def unpack(self):
                return ["org.example.Tray"]
        self.assertEqual(unpack_variant(FakeVariant()), ["org.example.Tray"])
        self.assertEqual(unpack_variant(["org.example.Tray"]), ["org.example.Tray"])
        self.assertEqual(unpack_variant("Active"), "Active")

    def test_argb_conversion_and_bounds(self):
        self.assertEqual(pixel_rgba(1, 1, bytes([255, 12, 34, 56])), bytes([12, 34, 56, 255]))
        self.assertIsNone(pixel_rgba(129, 1, bytes(129 * 4)))
        self.assertIsNone(pixel_rgba(1, 1, bytes(3)))
        self.assertIsNone(pixel_rgba(0, 0, b""))
        self.assertLessEqual(MAX_ITEMS, 64)
        self.assertIn("RegisteredStatusNotifierItems", WATCHER_XML)

    def test_win7_notification_overflow_prioritizes_attention(self):
        registered = [
            ("chat", "Active"), ("sync", "Active"), ("updates", "NeedsAttention"),
            ("sleep", "Passive"), ("music", "Active"),
        ]
        self.assertEqual(select_tray_icons(registered, 2),
                         (("updates", "chat"), ("sync", "music")))
        self.assertEqual(select_tray_icons(registered, None),
                         (("chat", "sync", "updates", "music"), ()))
        self.assertEqual(select_tray_icons(registered, 0),
                         ((), ("chat", "sync", "updates", "music")))
        self.assertEqual(select_tray_icons([("passive", "Passive")], 3), ((), ()))
        for invalid in (-1, True, "3"):
            with self.assertRaises(ValueError):
                select_tray_icons(registered, invalid)

    def test_win7_overflow_reflow_hides_passive_and_excess_icons(self):
        class Button:
            def __init__(self):
                self.visible = self.no_show_all = None
                self.tooltip = ""

            def set_visible(self, value):
                self.visible = value

            def set_no_show_all(self, value):
                self.no_show_all = value

            def set_tooltip_text(self, value):
                self.tooltip = value

        tray = StatusNotifierTray.__new__(StatusNotifierTray)
        tray.visible_limit = 1
        tray.overflow_button = Button()
        tray.items = {name: (Button(), None) for name in ("app", "warning", "sleep")}
        tray.item_state = {
            "app": ("Active", "App"),
            "warning": ("NeedsAttention", "Warning"),
            "sleep": ("Passive", "Sleeping app"),
        }
        tray._reflow()
        self.assertEqual(tray.overflow_ids, ("app",))
        self.assertFalse(tray.items["app"][0].visible)
        self.assertTrue(tray.items["warning"][0].visible)
        self.assertFalse(tray.items["sleep"][0].visible)
        self.assertTrue(tray.overflow_button.visible)
        self.assertIn("1 hidden", tray.overflow_button.tooltip)
        tray.item_state["app"] = ("Passive", "App")
        tray._reflow()
        self.assertEqual(tray.overflow_ids, ())
        self.assertFalse(tray.overflow_button.visible)

    def test_watcher_callbacks_accept_six_arg_pygobject_dispatch(self):
        class FakeVariant:
            def unpack(self):
                return ("org.example.Tray",)

        received = []
        tray = StatusNotifierTray.__new__(StatusNotifierTray)
        tray._add = received.append
        tray._watcher_signal(None, None, None, None, "StatusNotifierItemRegistered", FakeVariant())
        self.assertEqual(received, ["org.example.Tray"])
        tray.items = {}
        tray.hosts = set()
        tray._name_changed(None, None, None, None, "NameOwnerChanged",
                           type("Value", (), {"unpack": lambda self: ("org.example.Tray", ":1.2", ":1.3")})())


if __name__ == "__main__":
    unittest.main()
