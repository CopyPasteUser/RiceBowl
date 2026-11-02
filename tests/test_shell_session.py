"""Switch the running RiceHub taskbar without overlapping two shells."""

import unittest
from unittest import mock

from macrice.shell_session import sync_theme


class ShellSessionTests(unittest.TestCase):
    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch("macrice.shell_session.subprocess.Popen")
    @mock.patch("macrice.shell_session.subprocess.run")
    def test_quits_other_shell_before_starting_new_one(self, run, popen):
        order = []
        run.side_effect = lambda argv, **kwargs: (order.append(("quit", argv[-2:])),
                                                   mock.Mock(returncode=0))[1]
        popen.side_effect = lambda argv, **kwargs: order.append(("start", argv[-1]))
        self.assertEqual(sync_theme("RiceHub-Aero"), ())
        self.assertEqual(order, [("quit", ["windows10-shell", "--quit"]),
                                 ("start", "aero-shell")])

    @mock.patch.dict("os.environ", {"DISPLAY": ":99"})
    @mock.patch("macrice.shell_session.subprocess.Popen")
    @mock.patch("macrice.shell_session.subprocess.run")
    def test_failed_quit_does_not_start_overlapping_taskbar(self, run, popen):
        run.return_value = mock.Mock(returncode=1, stderr="could not reach shell")
        self.assertTrue(sync_theme("RiceHub-Ten-Light"))
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
