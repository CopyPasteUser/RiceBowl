"""Protocol-level tests for Aero SNI logic without a D-Bus session."""
import unittest

from macrice.aero_tray import (StatusNotifierTray, parse_item_id, registration_id,
                              pixel_rgba, MAX_ITEMS, WATCHER_XML, unpack_variant)


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
