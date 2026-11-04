"""Native GTK/X11 construction smoke for Windows 98 Find and its advanced controls."""
from __future__ import annotations

import os
import unittest


class ClassicFindGuiTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("DISPLAY"), "Requires a real X11/Xvfb display")
    def test_open_expand_and_close_find(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib
        ready = Gtk.init_check()
        if isinstance(ready, tuple):
            ready = ready[0]
        if not ready:
            self.skipTest("GTK display could not initialize")
        from macrice.classic98_menu import show_file_search

        parent = Gtk.Window()
        class Shell:
            bar = parent
            def _open_uri(self, _uri):
                pass

        observed, problems = [], []

        def descendants(widget):
            yield widget
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    yield from descendants(child)

        def inspect():
            dialogs = [w for w in Gtk.Window.list_toplevels()
                       if isinstance(w, Gtk.Dialog) and w.get_title() == "Find: All Files"]
            if not dialogs:
                problems.append("Find dialog failed to open")
                return False
            dialog = dialogs[0]
            widgets = list(descendants(dialog))
            expanders = [w for w in widgets if isinstance(w, Gtk.Expander)]
            if len(expanders) != 1:
                problems.append("Expected one Advanced options expander")
            else:
                expanders[0].set_expanded(True)
                if not expanders[0].get_expanded():
                    problems.append("Advanced options could not expand")
            for name in ("File extension", "Text within files",
                         "Minimum file size in MiB", "Maximum file size in MiB"):
                if not any(isinstance(w, Gtk.Entry)
                           and w.get_accessible().get_name() == name for w in widgets):
                    problems.append("Missing accessible field: " + name)
            observed.append(True)
            dialog.response(Gtk.ResponseType.CLOSE)
            return False

        def force_close():
            for widget in Gtk.Window.list_toplevels():
                if isinstance(widget, Gtk.Dialog) and widget.get_title() == "Find: All Files":
                    widget.response(Gtk.ResponseType.CLOSE)
            return False

        GLib.timeout_add(150, inspect)
        GLib.timeout_add(3000, force_close)
        try:
            show_file_search(Shell(), Gtk, GLib)
        finally:
            parent.destroy()
        self.assertTrue(observed, "Find dialog did not render")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
