"""Windows 98 Run history: in-memory privacy and ordering regressions."""
from __future__ import annotations

import unittest

from macrice.classic98_menu import remember_run


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


if __name__ == "__main__":
    unittest.main()
