"""Native Xvfb smoke for the read-only Windows 98 System Properties applet."""
from __future__ import annotations

import os
import unittest


class Classic98SystemGuiTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("DISPLAY"), "Requires X11/Xvfb")
    def test_system_properties_tabs_and_real_linux_content(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk
        ready = Gtk.init_check()
        if isinstance(ready, tuple):
            ready = ready[0]
        if not ready:
            self.skipTest("No GTK display")
        from macrice.classic98_system import show_system

        parent = Gtk.Window()
        class Shell:
            actions = parent
            bar = parent

        problems, observed = [], []

        def descendants(widget):
            yield widget
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    yield from descendants(child)

        def inspect():
            windows = [w for w in Gtk.Window.list_toplevels()
                       if isinstance(w, Gtk.Dialog) and w.get_title() == "System Properties"]
            if not windows:
                problems.append("System Properties dialog did not open")
                return False
            dialog = windows[0]
            widgets = list(descendants(dialog))
            notebook = next((w for w in widgets if isinstance(w, Gtk.Notebook)), None)
            if notebook is None or notebook.get_n_pages() != 3:
                problems.append("Missing General / Device Manager / Performance tabs")
            elif notebook.get_tab_label_text(notebook.get_nth_page(0)) != "General":
                problems.append("General tab is missing")
            if not any(isinstance(w, Gtk.TextView)
                       and "Linux" in w.get_buffer().get_text(
                           w.get_buffer().get_start_iter(),
                           w.get_buffer().get_end_iter(), False) for w in widgets):
                problems.append("System facts did not render")
            observed.append(True)
            dialog.response(Gtk.ResponseType.CLOSE)
            return False

        def force_close():
            for widget in Gtk.Window.list_toplevels():
                if isinstance(widget, Gtk.Dialog) and widget.get_title() == "System Properties":
                    widget.response(Gtk.ResponseType.CLOSE)
            return False

        GLib.timeout_add(150, inspect)
        GLib.timeout_add(3000, force_close)
        try:
            show_system(Shell(), Gtk)
        finally:
            parent.destroy()
        self.assertTrue(observed)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
