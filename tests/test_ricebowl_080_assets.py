"""Release 0.8.0 identity and native X11 asset acceptance checks."""
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from macrice.installer import project_root
from macrice.hardware_status import read_network


ICON_FAMILIES = (
    "RiceHub-Aero", "RiceHub-Ten-Penguin", "RiceHub-Luna-Icons",
    "RiceHub-Classic-Icons", "RiceHub-Chrome-Icons", "RiceHub-Frutiger-Icons",
)
STATUS_PROFILES = ("aero", "windows10", "winxp", "winclassic", "chromeos", "frutiger")


class VisualIdentityTests(unittest.TestCase):
    def test_each_rice_has_unique_real_app_and_places_icons(self):
        assets = project_root() / "assets/icons"
        for group, name in (
            ("apps", "system-file-manager"),
            ("apps", "preferences-system"),
            ("apps", "web-browser"),
            ("apps", "utilities-terminal"),
            ("places", "folder"),
            ("places", "user-home"),
            ("places", "user-trash"),
        ):
            contents = []
            for family in ICON_FAMILIES:
                path = assets / family / "scalable" / group / (name + ".svg")
                with self.subTest(family=family, kind=name):
                    self.assertTrue(path.is_file(), str(path))
                    ET.parse(path)
                    contents.append(hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(len(contents), len(set(contents)),
                             f"{name}: identical placeholder icons across rices")

    def test_each_status_icon_exists_as_valid_vector_for_every_rice(self):
        root = project_root() / "assets/status"
        for profile in STATUS_PROFILES:
            for key in ("battery-0", "battery-25", "battery-50", "battery-75",
                        "battery-100", "battery-charging", "wifi", "ethernet",
                        "offline", "sound", "muted"):
                path = root / profile / (key + ".svg")
                with self.subTest(profile=profile, status=key):
                    self.assertTrue(path.is_file())
                    svg = ET.parse(path).getroot()
                    self.assertTrue(svg.tag.endswith("svg"))

    def test_unique_start_buttons_for_four_heritage_skins(self):
        from macrice.heritage import PROFILES
        names = [PROFILES[key].logo for key in
                 ("winxp", "winclassic", "chromeos", "frutiger")]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            ET.parse(project_root() / "assets" / name)

    def test_vpn_default_route_reports_wireless_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            net = root / "net"
            (net / "wlp1s0" / "wireless").mkdir(parents=True)
            (net / "wlp1s0" / "operstate").write_text("up")
            (net / "tun0").mkdir()
            route = root / "route"
            route.write_text(
                "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"
                "tun0 00000000 0100007F 0003 0 0 50 00000000 0 0 0\n")
            self.assertEqual(read_network(net, route), "wifi")

    def test_chromeos_and_frutiger_have_separate_launcher_implementations(self):
        from macrice import aero_shell
        source = Path(aero_shell.__file__).read_text()
        self.assertIn("def _create_chrome_launcher", source)
        self.assertIn("def _create_frutiger_menu", source)
        self.assertIn("self._install_status_widgets(right_area)", source)
        self.assertIn("chrome-app-shelf", source)
        self.assertIn("chrome-status-pill", source)


if __name__ == "__main__":
    unittest.main()
