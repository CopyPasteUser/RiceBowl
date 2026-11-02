"""Headless tests for MacBar's no-popup status indicator contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import macbar  # noqa: E402
from gi.repository import GLib, Gtk  # noqa: E402
from status import parse_wpctl  # noqa: E402


class LayoutTests(unittest.TestCase):
    def test_status_indicators_are_read_only(self) -> None:
        fake = Mock()
        with patch.object(Gtk, "Box", return_value=fake):
            self.assertIs(macbar.indicator("Wi-Fi connected", Mock()), fake)
        fake.set_has_tooltip.assert_called_once_with(False)
        fake.get_accessible.return_value.set_name.assert_called_once_with("Wi-Fi connected")
        fake.connect.assert_not_called()
        self.assertFalse(hasattr(macbar, "popup"))
        self.assertFalse(hasattr(macbar.MacBar, "_open_network"))
        self.assertFalse(hasattr(macbar.MacBar, "_open_audio"))

    def test_window_title_widget_has_been_removed(self) -> None:
        self.assertNotIn("show_app_name", macbar.DEFAULT_CONFIG)
        self.assertFalse(hasattr(macbar.MacBar, "_init_window_title"))

    def test_networkmanager_primary_wifi_connection_selects_wifi_icon(self) -> None:
        with patch.object(macbar, "load_config", return_value=macbar.DEFAULT_CONFIG.copy()):
            bar = macbar.MacBar()
        bar.network_proxy = Mock()
        bar.network_proxy.get_cached_property.side_effect = lambda name: {
            "State": GLib.Variant("u", 70),
            "PrimaryConnectionType": GLib.Variant("s", "802-11-wireless"),
        }[name]
        bar.network_image = Mock()
        bar.network_indicator = Mock()
        bar._network_update()
        bar.network_image.set_from_icon_name.assert_called_once_with(
            "network-wireless-symbolic", Gtk.IconSize.MENU,
        )
        bar.network_indicator.get_accessible.return_value.set_name.assert_called_once_with("Wi-Fi connected")

    def test_config_rejects_invalid_types_instead_of_crashing_at_start(self) -> None:
        import json
        import os
        import tempfile

        for invalid in ({"menu_icon": None}, {"height": True}, {"show_battery_percent": "yes"}):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as temp:
                config_dir = Path(temp) / "macbar"
                config_dir.mkdir()
                (config_dir / "config.json").write_text(json.dumps(invalid))
                with patch.dict(os.environ, {"XDG_CONFIG_HOME": temp}):
                    self.assertEqual(macbar.load_config(), macbar.DEFAULT_CONFIG)

    def test_tooltips_disabled_at_screen_edge(self) -> None:
        with patch.object(Gtk, "Button") as fake:
            macbar.button("Open / close MacMenu", Mock())
        fake.return_value.set_has_tooltip.assert_called_once_with(False)

    def test_wpctl_failure_falls_back_to_pactl(self) -> None:
        with patch.object(macbar, "load_config", return_value=macbar.DEFAULT_CONFIG.copy()):
            bar = macbar.MacBar()
        bar._read_volume = Mock()
        process = Mock()
        process.communicate_utf8_finish.return_value = (True, "", "")
        process.get_successful.return_value = False
        with patch.object(macbar.shutil, "which", return_value="/usr/bin/pactl"):
            bar._volume_ready(process, Mock(), parse_wpctl)
        bar._read_volume.assert_called_once()
        self.assertEqual(bar._read_volume.call_args.args[0][1], "get-sink-volume")

    def test_xfce_is_not_stopped_before_dock_maps(self) -> None:
        with patch.object(macbar, "load_config", return_value=macbar.DEFAULT_CONFIG.copy()):
            bar = macbar.MacBar(replace_xfce=True)
        bar.window = Mock()
        bar.window.get_mapped.side_effect = [False, True]
        with patch.object(macbar.shutil, "which", return_value="/usr/bin/xfce4-panel"), \
             patch.object(macbar.Gio.Subprocess, "new") as spawned:
            self.assertTrue(bar._replace_panel())
            spawned.assert_not_called()
            self.assertFalse(bar._replace_panel())
            spawned.assert_called_once_with(["xfce4-panel", "--quit"], macbar.Gio.SubprocessFlags.NONE)

    def test_theme_reload_is_immediate_and_does_not_recreate_the_window(self) -> None:
        with patch.object(macbar, "load_config", return_value=macbar.DEFAULT_CONFIG.copy()):
            bar = macbar.MacBar()
        bar._style = Mock()
        bar._position = Mock()
        bar._render_battery = Mock()
        updated = {**bar.settings, "theme": "light"}
        with patch.object(macbar, "load_config", return_value=updated):
            self.assertFalse(bar._reload_config())
        self.assertEqual(bar.settings["theme"], "light")
        bar._style.assert_called_once()
        bar._position.assert_not_called()

    def test_unrelated_file_events_do_not_trigger_reload(self) -> None:
        with patch.object(macbar, "load_config", return_value=macbar.DEFAULT_CONFIG.copy()):
            bar = macbar.MacBar()
        with patch.object(macbar.GLib, "timeout_add") as schedule:
            bar._config_changed(None, Mock(get_basename=lambda: "other.json"), None, None)
            schedule.assert_not_called()
            bar._config_changed(None, Mock(get_basename=lambda: "config.json"), None, None)
            schedule.assert_called_once_with(90, bar._reload_config)

    def test_theme_provider_is_reused_across_many_switches(self) -> None:
        with patch.object(macbar, "load_config", return_value=macbar.DEFAULT_CONFIG.copy()):
            bar = macbar.MacBar()
        with patch.object(macbar.Gtk, "CssProvider") as factory, \
             patch.object(macbar.Gtk.StyleContext, "add_provider_for_screen") as add_provider:
            for theme in ("dark", "light", "dark", "light"):
                bar.settings["theme"] = theme
                bar._style()
            factory.assert_called_once()
            add_provider.assert_called_once()
            self.assertEqual(factory.return_value.load_from_data.call_count, 4)


if __name__ == "__main__":
    unittest.main()
