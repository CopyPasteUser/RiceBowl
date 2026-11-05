"""Taskbar shortcuts must open actual, installed process managers."""

import unittest
from pathlib import Path

from macrice.aero_shell import LAUNCHABLE_TOOLS, preferred_task_manager


ROOT = Path(__file__).resolve().parents[1]


class TaskManagerIntegrationTests(unittest.TestCase):
    def test_prefer_lightweight_xfce_and_fallback_to_gnome(self):
        for available, expected in (
            ({"xfce4-taskmanager", "gnome-system-monitor"}, "xfce4-taskmanager"),
            ({"gnome-system-monitor"}, "gnome-system-monitor"),
            (set(), None),
        ):
            with self.subTest(available=available):
                resolved = preferred_task_manager(lambda binary: binary if binary in available else None)
                self.assertEqual(resolved, expected)
                if resolved:
                    self.assertIn(resolved, LAUNCHABLE_TOOLS)

    def test_existing_cross_rice_native_menus_share_one_live_resolver(self):
        shell = (ROOT / "macrice/aero_shell.py").read_text(encoding="utf-8")
        for owner in ("_classic98_taskbar_menu", "_luna_taskbar_menu",
                      "_ten_taskbar_menu", "_win7_taskbar_menu"):
            with self.subTest(owner=owner):
                self.assertIn(f"def {owner}(self):", shell)
        self.assertIn('"winclassic", "winxp", "aero", "windows10"', shell)
        self.assertIn('self._ten_taskbar_context if profile == "windows10"', shell)
        self.assertIn('menu.append(self._task_manager_item())', shell)
        self.assertIn('menu.append(self._task_manager_item(label="Start Task Manager"))', shell)
        self.assertIn('item.set_sensitive(name is not None)', shell)
        self.assertIn('self._open_tool(selected)', shell)
        self.assertIn('context_menu.destroy()', shell)


if __name__ == "__main__":
    unittest.main()
