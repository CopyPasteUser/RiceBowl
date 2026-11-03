"""Native Windows 7 task grouping and overflow invariants."""
import unittest

from macrice.aero_superbar import group_windows, select_groups
from macrice.aero_windows import WindowSnapshot


def win(xid, group="", title="Window"):
    return WindowSnapshot(xid, title, False, None, group)


class SuperbarModelTests(unittest.TestCase):
    def test_grouping_casefolded_wmclass_and_unknown_windows_separate(self):
        snapshots = (win(1, "Firefox", "One"), win(2, "terminal", "Shell"),
                     win(3, "firefox", "Two"), win(4), win(5))
        groups = group_windows(snapshots)
        self.assertEqual([g.key for g in groups],
                         ["app:firefox", "app:terminal", "window:4", "window:5"])
        self.assertEqual(groups[0].xids, (1, 3))
        self.assertEqual(groups[0].title, "One")

    def test_active_group_rescued_without_splitting_or_loss(self):
        groups = group_windows((win(1, "browser"), win(2, "terminal"),
                                win(3, "browser"), win(4, "editor")))
        visible, hidden = select_groups(groups, 4, 2)
        self.assertEqual([g.key for g in visible], ["app:browser", "app:editor"])
        self.assertEqual([g.key for g in hidden], ["app:terminal"])
        self.assertEqual(set(xid for group in visible + hidden for xid in group.xids),
                         {1, 2, 3, 4})
        self.assertEqual(select_groups(groups, 1, 0)[0], ())
        self.assertEqual(select_groups(groups, None, 99)[0], groups)

    def test_reordering_keeps_unique_groups_and_no_unsafe_title_grouping(self):
        snapshots = (win(10, "", "Untitled"), win(11, "", "Untitled"),
                     win(12, "FileManager", "Files"))
        self.assertEqual(len(group_windows(snapshots)), 3)
        self.assertEqual(group_windows(tuple(reversed(snapshots)))[0].xids, (12,))


if __name__ == "__main__":
    unittest.main()
