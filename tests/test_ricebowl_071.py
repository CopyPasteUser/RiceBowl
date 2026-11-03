"""Regression coverage for 0.7.1 battery, network, audio and asset upgrades."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from macrice.asset_upgrade import (
    AssetConflict, git_blob_sha, inspect_bundle, install_bundle,
)
from macrice.hardware_status import read_battery, read_network, read_sound


class StatusReaderTests(unittest.TestCase):
    def test_battery_percentage_and_charging_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bat = root / "BAT0"
            bat.mkdir()
            for name, value in {"type": "Battery", "present": "1",
                                "capacity": "63", "status": "Discharging"}.items():
                (bat / name).write_text(value)
            state = read_battery(root)
            self.assertEqual((state.percent, state.charging, state.label),
                             (63, False, "Discharging"))
            (bat / "status").write_text("Charging")
            self.assertTrue(read_battery(root).charging)

    def test_multiple_batteries_are_energy_weighted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, now, full in [(0, 30, 60), (1, 10, 40)]:
                bat = root / ("BAT" + str(index))
                bat.mkdir()
                for name, value in {"type": "Battery", "energy_now": str(now),
                                    "energy_full": str(full), "status": "Discharging"}.items():
                    (bat / name).write_text(value)
            self.assertEqual(read_battery(root).percent, 40)

    def test_no_battery_and_missing_readings_do_not_fake_power(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = root / "AC0"
            adapter.mkdir()
            (adapter / "type").write_text("Mains")
            self.assertIsNone(read_battery(root))
            bat = root / "BAT0"
            bat.mkdir()
            (bat / "type").write_text("Battery")
            (bat / "capacity").write_text("invalid")
            self.assertIsNone(read_battery(root))

    def test_default_route_correctly_distinguishes_wifi_and_ethernet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            net = root / "net"
            net.mkdir()
            wifi = net / "wlp2s0"
            wifi.mkdir()
            (wifi / "wireless").mkdir()
            cable = net / "enp3s0"
            cable.mkdir()
            route = root / "route"
            header = "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"
            wifi_route = "wlp2s0 00000000 0100007F 0003 0 0 100 00000000 0 0 0\n"
            cable_route = "enp3s0 00000000 0100007F 0003 0 0 20 00000000 0 0 0\n"
            route.write_text(header + wifi_route)
            self.assertEqual(read_network(net, route), "wifi")
            route.write_text(header + wifi_route + cable_route)
            self.assertEqual(read_network(net, route), "ethernet")
            route.write_text(header)
            self.assertEqual(read_network(net, route), "offline")

    def test_audio_wires_up_wpctl_then_pactl_without_long_blocking(self):
        with mock.patch("macrice.hardware_status.shutil.which",
                        side_effect=lambda name: "/usr/bin/" + name), \
             mock.patch("macrice.hardware_status._run",
                        return_value="Volume: 0.63 [MUTED]"):
            state = read_sound()
            self.assertEqual((state.percent, state.muted), (63, True))
        with mock.patch("macrice.hardware_status.shutil.which",
                        side_effect=lambda name: None if name == "wpctl" else "/usr/bin/pactl"), \
             mock.patch("macrice.hardware_status._run",
                        side_effect=["Volume: front-left: 65536 / 100% / 0.00 dB",
                                     "Mute: no"]):
            state = read_sound()
            self.assertEqual((state.percent, state.muted), (100, False))
        with mock.patch("macrice.hardware_status.shutil.which", return_value=None):
            self.assertIsNone(read_sound().percent)


class AssetUpgradeTests(unittest.TestCase):
    def _bundle(self, root):
        src = root / "assets/themes/RiceHub-Test"
        dst = root / "data/themes/RiceHub-Test"
        src.mkdir(parents=True)
        dst.mkdir(parents=True)
        (src / "gtk.css").write_text("new CSS\n")
        (src / "index.theme").write_text("Name=RiceBowl\n")
        (dst / "gtk.css").write_text("old known CSS\n")
        (dst / "index.theme").write_text("Name=RiceHub\n")
        return src, dst

    def test_known_historical_assets_migrate_with_full_recovery_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = self._bundle(Path(tmp))
            trusted = {"assets/themes/RiceHub-Test/gtk.css":
                       frozenset({git_blob_sha(b"old known CSS\n")})}
            with mock.patch("macrice.asset_upgrade.trusted_assets", return_value=trusted):
                inspect_bundle(src, dst)
                backup = install_bundle(src, dst)
            self.assertIsNotNone(backup)
            self.assertEqual((dst / "gtk.css").read_text(), "new CSS\n")
            self.assertEqual((backup / "gtk.css").read_text(), "old known CSS\n")
            self.assertEqual((backup / "index.theme").read_text(), "Name=RiceHub\n")
            self.assertIsNone(install_bundle(src, dst))

    def test_unknown_user_edit_is_protected_and_repair_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = self._bundle(Path(tmp))
            (dst / "gtk.css").write_text("private custom theme")
            with mock.patch("macrice.asset_upgrade.trusted_assets", return_value={}):
                with self.assertRaisesRegex(AssetConflict, "customized"):
                    inspect_bundle(src, dst)
            self.assertEqual((dst / "gtk.css").read_text(), "private custom theme")
            backup = install_bundle(src, dst, repair=True)
            self.assertEqual((backup / "gtk.css").read_text(), "private custom theme")
            self.assertEqual((dst / "gtk.css").read_text(), "new CSS\n")

    def test_unmanaged_extra_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, dst = self._bundle(root)
            (dst / "unexpected.txt").write_text("user")
            with self.assertRaisesRegex(AssetConflict, "customized"):
                inspect_bundle(src, dst)
            with self.assertRaisesRegex(AssetConflict, "customized"):
                install_bundle(src, dst)
            self.assertTrue((dst / "unexpected.txt").exists())
            (dst / "unexpected.txt").unlink()
            (dst / "gtk.css").unlink()
            (dst / "gtk.css").symlink_to(root / "outside")
            with self.assertRaisesRegex(AssetConflict, "symlink"):
                install_bundle(src, dst, repair=True)


class ScopedRepairTests(unittest.TestCase):
    def test_repair_ten_dark_leaves_custom_ten_light_untouched(self):
        from macrice.rice import repair_assets

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            data = root / "data"
            dark = "RiceHub-Ten-Dark"
            light = "RiceHub-Ten-Light"
            icons = "RiceHub-Ten-Penguin"
            for name in (dark, light):
                path = source / "assets/themes" / name
                path.mkdir(parents=True)
                (path / "gtk.css").write_text("fresh:" + name)
                target = data / "themes" / name
                target.mkdir(parents=True)
                (target / "gtk.css").write_text("modified:" + name)
            icon_dir = source / "assets/icons" / icons
            icon_dir.mkdir(parents=True)
            (icon_dir / "index.theme").write_text("[Icon Theme]\\nName=RiceBowl\\n")
            with mock.patch("macrice.rice.os.geteuid", return_value=1000):
                archives = repair_assets("ten-dark", data_root=data, source_root=source)
            self.assertEqual(len(archives), 1)
            self.assertEqual((data / "themes" / dark / "gtk.css").read_text(), "fresh:" + dark)
            self.assertEqual((data / "themes" / light / "gtk.css").read_text(), "modified:" + light)
            self.assertEqual((archives[0] / "gtk.css").read_text(), "modified:" + dark)
            self.assertTrue((data / "icons" / icons / "index.theme").is_file())


if __name__ == "__main__":
    unittest.main()
