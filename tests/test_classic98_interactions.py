"""Fast, side-effect-free checks for Win98's actual menu backends."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from enum import IntFlag

from macrice.classic98_control_panel import APPLETS, executable, visible_applets
from macrice.classic98_menu import (
    Favorite, all_favorites, gtk_bookmarks, parse_run_target, save_favorites,
    user_favorites, valid_favorite,
)
from macrice.classic98_taskbar import available_actions, perform


class FakeActions(IntFlag):
    MOVE = 1
    RESIZE = 2
    MINIMIZE = 4
    UNMINIMIZE = 8
    MAXIMIZE = 16
    UNMAXIMIZE = 32
    CLOSE = 64


class FakeWnck:
    WindowActions = FakeActions


class FakeWindow:
    def __init__(self, minimized=False, maximized=False):
        self.minimized = minimized
        self.maximized = maximized
        self.calls = []

    def get_actions(self):
        return FakeActions(127)

    def is_minimized(self):
        return self.minimized

    def is_maximized(self):
        return self.maximized

    def __getattr__(self, name):
        def method(*args):
            self.calls.append((name, args))
        return method


class Classic98BackendTests(unittest.TestCase):
    def test_favorites_are_atomic_and_user_scoped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ricebowl" / "classic98-favorites.json"
            entries = (Favorite("Home", Path(folder).as_uri()),
                       Favorite("Docs", "https://example.org/docs"))
            save_favorites(entries, path)
            self.assertEqual(user_favorites(path), entries)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError):
                save_favorites((Favorite("bad", "javascript:alert(1)"),), path)
            self.assertEqual(user_favorites(path), entries)

    def test_import_gtk_bookmarks_without_modifying_them(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "gtk-3.0").mkdir()
            file = base / "gtk-3.0" / "bookmarks"
            file.write_text("file:///tmp/Project Project files\nhttps://example.org Docs\n"
                            "javascript:alert(1) Unsafe\n", encoding="utf-8")
            with patch.dict("os.environ", {"XDG_CONFIG_HOME": folder}):
                self.assertEqual(gtk_bookmarks(), (
                    Favorite("Project files", "file:///tmp/Project"),
                    Favorite("Docs", "https://example.org"),
                ))
                self.assertEqual(all_favorites(), gtk_bookmarks())
                self.assertFalse((base / "ricebowl" / "classic98-favorites.json").exists())
            self.assertEqual(file.read_text(encoding="utf-8").count("\n"), 3)

    def test_supported_uri_schemes_are_explicit(self):
        self.assertTrue(valid_favorite("smb://nas/Photos"))
        self.assertFalse(valid_favorite("javascript:alert(1)"))
        self.assertFalse(valid_favorite("file:"))

    def test_run_parser_does_not_invoke_shell_expansion(self):
        with patch("shutil.which", side_effect=lambda cmd: "/usr/bin/printf" if cmd == "printf" else None):
            kind, argv = parse_run_target("printf 'hello; touch /tmp/never' ")
            self.assertEqual((kind, argv), ("command", ("printf", "hello; touch /tmp/never")))
            with self.assertRaisesRegex(ValueError, "not installed"):
                parse_run_target("not-a-real-binary")
        self.assertEqual(parse_run_target("https://example.org"), ("uri", "https://example.org"))
        with self.assertRaises(ValueError):
            parse_run_target("printf 'unterminated")

    def test_run_parser_handles_real_folders(self):
        with tempfile.TemporaryDirectory(prefix="ricebowl98-contains space-") as folder:
            self.assertEqual(parse_run_target(repr(folder)), ("uri", Path(folder).as_uri()))

    def test_control_panel_shows_real_applet_catalog(self):
        self.assertEqual(len(APPLETS), len({a.name for a in APPLETS}))
        self.assertGreaterEqual(len(APPLETS), 15)
        self.assertTrue(visible_applets("mouse"))
        self.assertEqual(visible_applets("nonexistent applet"), ())
        self.assertEqual(executable(APPLETS[0], which=lambda name: None), None)
        self.assertEqual(executable(APPLETS[0], which=lambda name: "/usr/bin/" + name),
                         APPLETS[0].commands[0])

    def test_classic_taskbar_menu_matches_window_manager_state(self):
        normal = dict(available_actions(FakeWindow(), FakeWnck))
        self.assertEqual(normal, {"Restore": False, "Move": True, "Size": True,
                                  "Minimize": True, "Maximize": True, "Close": True})
        maximized = dict(available_actions(FakeWindow(maximized=True), FakeWnck))
        self.assertTrue(maximized["Restore"])
        self.assertFalse(maximized["Move"])
        self.assertFalse(maximized["Size"])
        minimized = dict(available_actions(FakeWindow(minimized=True), FakeWnck))
        self.assertTrue(minimized["Restore"])
        self.assertFalse(minimized["Minimize"])

    def test_window_actions_call_the_real_wm_interface(self):
        win = FakeWindow()
        perform(win, "Close", 1234)
        perform(win, "Move", 1234)
        self.assertEqual(win.calls, [("close", (1234,)), ("activate", (1234,)),
                                     ("keyboard_move", ())])
        with self.assertRaises(ValueError):
            perform(win, "Delete all files", 1)


if __name__ == "__main__":
    unittest.main()
