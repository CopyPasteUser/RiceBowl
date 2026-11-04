"""Windows 98 System Properties verifies Linux facts from disposable /proc & /sys fixtures."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from macrice.classic98_system import (
    collect_system, cpu_name, meminfo_bytes, release_name, report_sections,
    size_label,
)
from macrice.classic98_control_panel import APPLETS


class ClassicSystemPropertiesTests(unittest.TestCase):
    def test_reads_realistic_linux_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("etc", "proc", "sys/class/net/enp1s0", "sys/block/nvme0n1"):
                (root / name).mkdir(parents=True)
            (root / "etc/os-release").write_text('NAME=Linux\nPRETTY_NAME="Linux Mint Test"\n')
            (root / "proc/cpuinfo").write_text(
                "processor : 0\nmodel name : Intel Core i7-7600U\nprocessor : 1\n")
            (root / "proc/meminfo").write_text(
                "MemTotal: 16384000 kB\nMemAvailable: 8192000 kB\n")
            (root / "proc/uptime").write_text("93784.72 843.00\n")
            (root / "sys/class/net/enp1s0/operstate").write_text("up\n")
            (root / "sys/block/nvme0n1/size").write_text("2097152\n")
            snapshot = collect_system(root)
            self.assertEqual(snapshot.distribution, "Linux Mint Test")
            self.assertEqual(snapshot.cpu_model, "Intel Core i7-7600U")
            self.assertEqual(snapshot.memory_total, 16384000 * 1024)
            self.assertEqual(snapshot.memory_available, 8192000 * 1024)
            self.assertEqual(snapshot.uptime_seconds, 93784)
            self.assertEqual(snapshot.interfaces, (("enp1s0", "up"),))
            self.assertEqual(snapshot.block_devices, (("nvme0n1", 1073741824),))
            sections = report_sections(snapshot)
            self.assertEqual(set(sections), {"General", "Device Manager", "Performance"})
            self.assertIn("Intel Core i7-7600U", sections["General"])
            self.assertIn("nvme0n1", sections["Device Manager"])
            self.assertIn("1.0 GiB", sections["Device Manager"])
            self.assertIn("1 days", sections["Performance"])

    def test_missing_data_is_truthfully_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_system(Path(directory))
        self.assertIn("unavailable", result.distribution.casefold())
        self.assertIsNone(result.memory_total)
        self.assertIsNone(result.uptime_seconds)
        self.assertEqual(result.interfaces, ())
        self.assertEqual(result.block_devices, ())
        text = report_sections(result)
        self.assertIn("Unavailable", text["Performance"])
        self.assertIn("None reported", text["Device Manager"])

    def test_cpu_model_precedes_numeric_processor_index(self):
        self.assertEqual(cpu_name("processor: 0\nmodel name: Ryzen 7\n"), "Ryzen 7")
        self.assertEqual(cpu_name("processor: 0\n"), "Processor model unavailable")

    def test_parsers_reject_false_or_broken_values(self):
        self.assertEqual(release_name('PRETTY_NAME="Ubuntu Server"\n'), "Ubuntu Server")
        self.assertEqual(meminfo_bytes("MemTotal: bad kB", "MemTotal"), None)
        self.assertEqual(size_label(-1), "Unavailable")
        self.assertEqual(size_label(1024 * 1024), "1.0 MiB")

    def test_control_panel_system_entry_is_native(self):
        applet = next(x for x in APPLETS if x.name == "System")
        self.assertEqual(applet.commands, ())
        self.assertIn("Linux", applet.description)


if __name__ == "__main__":
    unittest.main()
