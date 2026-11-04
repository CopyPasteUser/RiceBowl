"""Windows 98 Run history: in-memory privacy and ordering regressions."""
from __future__ import annotations

import unittest

from macrice.classic98_menu import remember_run, quick_launch_menu_action


class Classic98RunHistoryTests(unittest.TestCase):
    def test_recent_first_and_deduplicated(self):
        self.assertEqual(remember_run(("a", "b", "c"), "b"), ("b", "a", "c"))

    def test_blank_input_preserves_history(self):
        self.assertEqual(remember_run(("a", "b"), " "), ("a", "b"))

    def test_history_is_bounded(self):
        history = tuple(str(i) for i in range(20))
        result = remember_run(history, "new")
        self.assertEqual(result[0], "new")
        self.assertEqual(len(result), 12)

    def test_preserves_arguments_not_shell_exec(self):
        self.assertEqual(remember_run((), 'gedit "hello world.txt"'),
                         ('gedit "hello world.txt"',))

class Classic98ProgramContextTests(unittest.TestCase):
    def test_add_and_remove_quick_launch(self):
        self.assertEqual(quick_launch_menu_action("app.desktop", (), 3),
                         ("Add to Quick Launch", True, True))
        self.assertEqual(quick_launch_menu_action(
            "app.desktop", ("app.desktop",), 3),
            ("Remove from Quick Launch", True, False))

    def test_full_toolbar_disables_new_pin_but_not_remove(self):
        self.assertEqual(quick_launch_menu_action("new.desktop", ("a", "b"), 2),
                         ("Add to Quick Launch", False, True))
        self.assertEqual(quick_launch_menu_action("a", ("a", "b"), 2),
                         ("Remove from Quick Launch", True, False))

    def test_missing_desktop_id_has_no_pin_action(self):
        self.assertIsNone(quick_launch_menu_action(None, (), 3))




if __name__ == "__main__":
    unittest.main()
