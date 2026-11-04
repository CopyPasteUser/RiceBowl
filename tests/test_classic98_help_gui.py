"""Smoke-test actual classic Help navigation and Search under X11/Xvfb."""
from __future__ import annotations

import os
import unittest


class ClassicHelpGuiTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("DISPLAY"), "Requires X11/Xvfb")
    def test_contents_history_index_and_search(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib
        ready = Gtk.init_check()
        if isinstance(ready, tuple):
            ready = ready[0]
        if not ready:
            self.skipTest("GTK could not connect to a display")
        from macrice.classic98_help import show_help

        parent = Gtk.Window()

        class Shell:
            bar = parent
            was_hidden = False
            def _hide_menu(self):
                self.was_hidden = True

        shell = Shell()
        problems, visited = [], []

        def descendants(widget):
            yield widget
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    yield from descendants(child)

        def inspect():
            dialogs = [w for w in Gtk.Window.list_toplevels()
                       if isinstance(w, Gtk.Dialog) and w.get_title() == "RiceBowl Help"]
            if not dialogs:
                problems.append("Help dialog did not open")
                return False
            dialog = dialogs[0]
            widgets = list(descendants(dialog))
            notebook = next((w for w in widgets if isinstance(w, Gtk.Notebook)), None)
            listings = [w for w in widgets if isinstance(w, Gtk.ListBox)]
            search = next((w for w in widgets if isinstance(w, Gtk.SearchEntry)), None)
            back = next((w for w in widgets if isinstance(w, Gtk.Button)
                         and w.get_label() == "◀ Back"), None)
            if notebook is None or notebook.get_n_pages() != 3 or len(listings) != 3:
                problems.append("Missing Contents / Index / Search tabs")
            if search is None or back is None:
                problems.append("Missing search or navigation controls")
            if not problems:
                names = [row._help_topic for row in listings[0].get_children()]
                if "Finding Files" not in names:
                    problems.append("Contents topic missing")
                else:
                    idx = names.index("Finding Files")
                    listings[0].emit("row-activated", listings[0].get_row_at_index(idx))
                    if not back.get_sensitive():
                        problems.append("Back history did not activate after visiting a topic")
                    back.clicked()
                    if back.get_sensitive():
                        problems.append("Back did not return to the initial topic")
                search.set_text("Quick Launch")
                search.emit("search-changed")
                if not listings[2].get_children():
                    problems.append("Help Search found no matching topics")
                visited.append(True)
            dialog.response(Gtk.ResponseType.CLOSE)
            return False

        def force_close():
            for widget in Gtk.Window.list_toplevels():
                if isinstance(widget, Gtk.Dialog) and widget.get_title() == "RiceBowl Help":
                    widget.response(Gtk.ResponseType.CLOSE)
            return False

        GLib.timeout_add(150, inspect)
        GLib.timeout_add(3000, force_close)
        try:
            show_help(shell, Gtk)
        finally:
            parent.destroy()
        self.assertTrue(shell.was_hidden)
        self.assertTrue(visited)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
