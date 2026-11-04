"""Windows 10 deeper-settings/network/workspace contracts without hardware writes."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from macrice.hardware_status import BluetoothState, SoundState, WifiNetwork
from macrice.riceware import spice
from macrice.riceware.worker import Response
from macrice.ten_network import TenNetworkFlyout, network_description
from macrice.ten_settings import CATEGORIES, SUBPAGES, TenSettings, page_parent
from macrice.ten_task_view import MAX_VISIBLE_WINDOWS, TenTaskView, manageable_workspace_count


class Toggle:
    def __init__(self, value=False):
        self.value = value
        self.enabled = False
        self.tooltip = ""

    def get_active(self):
        return self.value

    def set_active(self, value):
        self.value = value

    def set_sensitive(self, value):
        self.enabled = value

    def set_tooltip_text(self, value):
        self.tooltip = value


class Label:
    def set_text(self, value):
        self.value = value


class Slider(Toggle):
    def set_value(self, value):
        self.value = value


def settings_fixture():
    view = TenSettings.__new__(TenSettings)
    view._pending = set()
    view._switches = {
        "wifi": Toggle(), "bluetooth": Toggle(),
        "audio_mute": Toggle(), "quiet": Toggle(),
    }
    view._sliders = {"audio": Slider(), "brightness": Slider()}
    view._status_labels = {"bluetooth": Label(), "network": Label()}
    view.refresh = Mock()
    return view


class Win10DeepTests(unittest.TestCase):
    def test_settings_categories_and_real_navigation_hierarchy(self):
        self.assertEqual(len(CATEGORIES), 9)
        self.assertEqual(page_parent("home"), "home")
        self.assertEqual(page_parent("network"), "home")
        for page, (parent, title) in SUBPAGES.items():
            self.assertEqual(page_parent(page), parent)
            self.assertTrue(title)

    def test_capability_readback_updates_real_audio_and_mute(self):
        view = settings_fixture()
        view._render_capability("audio", Response(
            "audio", 1, value=spice.Result("audio", "ok", SoundState(43, True))))
        self.assertEqual(view._sliders["audio"].value, 43)
        self.assertTrue(view._sliders["audio"].enabled)
        self.assertTrue(view._switches["audio_mute"].value)
        self.assertTrue(view._switches["audio_mute"].enabled)

    def test_missing_radio_cannot_be_toggled(self):
        view = settings_fixture()
        view._render_capability("wifi", Response(
            "wifi", 1, value=spice.Result("wifi", "unavailable")))
        self.assertFalse(view._switches["wifi"].enabled)
        view._render_capability("bluetooth", Response(
            "bluetooth", 1, value=spice.Result("bluetooth", "ok",
                        BluetoothState(False, ()))))
        self.assertTrue(view._switches["bluetooth"].enabled)
        self.assertFalse(view._switches["bluetooth"].value)

    def test_unverifiable_focus_assist_is_not_reported_as_success(self):
        view = settings_fixture()
        view._pending.add("quiet")
        view._written("quiet", True, Response("quiet", 1, value=False))
        self.assertNotEqual(view._switches["quiet"].tooltip, "Verified")
        view.refresh.assert_called_once()

    def test_real_wifi_list_describes_signal_and_connection(self):
        self.assertEqual(network_description(WifiNetwork("Saved", 72, "WPA2", True)),
                         "72% signal · Secured · Connected")
        self.assertEqual(network_description(WifiNetwork("Guest", 19, "--", False)),
                         "19% signal · Open")

    def test_workspace_creation_is_bounded(self):
        self.assertFalse(manageable_workspace_count(0))
        self.assertTrue(manageable_workspace_count(1))
        self.assertTrue(manageable_workspace_count(11))
        self.assertFalse(manageable_workspace_count(12))
        self.assertEqual(MAX_VISIBLE_WINDOWS, 60)

    def test_workspace_count_requires_real_wm_confirmation(self):
        view = TenTaskView.__new__(TenTaskView)
        view.message = Label()
        view.refresh = Mock()
        view._screen = lambda: Mock(get_workspaces=lambda: (object(),))
        self.assertFalse(view._verify_count(2))
        self.assertIn("did not confirm", view.message.value)

    def test_disabled_wifi_is_reported_as_off_not_no_visible_networks(self):
        view = TenNetworkFlyout.__new__(TenNetworkFlyout)
        view.closed = False
        view.epoch = 1
        view.window = Mock()
        view.window.get_visible.return_value = True
        view.runner = Mock()
        view.status = Label()
        view.feedback = Label()
        view._render = Mock()
        view.refresh()
        key, operation, callback = view.runner.submit.call_args.args
        with patch("macrice.ten_network.spice.read", return_value=spice.Result(
                "wifi", "ok", False)), patch("macrice.ten_network.spice.scan_wifi",
                return_value=spice.Result("wifi_networks", "ok", ())):
            result = operation()
        callback(Response(key, 1, value=result))
        self.assertEqual(view.status.value, "Wi-Fi is turned off")
        self.assertIn("Action Center", view.feedback.value)

    def test_network_change_calls_verified_ricespice_api(self):
        view = TenNetworkFlyout.__new__(TenNetworkFlyout)
        view.busy = False
        view.closed = False
        view.epoch = 1
        view.feedback = Label()
        view.window = Mock()
        view.window.get_visible.return_value = True
        view.runner = Mock()
        view.refresh = Mock()
        view.shell = Mock()
        view._change("wifi_connect", "Test AP")
        key, operation, callback = view.runner.submit.call_args.args
        self.assertEqual(key, "ten-wifi-change")
        with patch("macrice.ten_network.spice.change", return_value=spice.Result(
                "wifi_connect", "error", reason="Credential unavailable")) as change:
            result = operation()
        change.assert_called_once_with("wifi_connect", "Test AP")
        callback(Response(key, 1, value=result))
        self.assertIn("Credential unavailable", view.feedback.value)
        self.assertIn("password", view.feedback.value)
        view.refresh.assert_called_once()


if __name__ == "__main__":
    unittest.main()
