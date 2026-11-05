"""GTK drag source/target registration and explicit user denial (headless)."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from macrice.riceware import dnd_gtk


class FolderDropGtkTests(unittest.TestCase):
    def test_real_gtk3_folder_target_registers_when_xvfb_available(self):
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, GLib, Gtk

        initialized = Gtk.init_check()
        if not (initialized[0] if isinstance(initialized, tuple) else initialized):
            self.skipTest("GTK display unavailable; native Xvfb CI supplies one")
        with tempfile.TemporaryDirectory() as root:
            button = Gtk.Button(label="Desktop")
            self.assertTrue(dnd_gtk.attach_folder_drop(button, Path(root), Gtk, Gdk, GLib))
            self.assertIsNotNone(button.drag_dest_get_target_list())

    def test_valid_folder_registers_uri_copy_target_only(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "Desktop"
            folder.mkdir()
            widget = mock.Mock()
            Gtk = SimpleNamespace(TargetEntry=SimpleNamespace(new=lambda *args: args),
                                  DestDefaults=SimpleNamespace(ALL=7))
            Gdk = SimpleNamespace(DragAction=SimpleNamespace(COPY=9))
            self.assertTrue(dnd_gtk.attach_folder_drop(widget, folder, Gtk, Gdk, mock.Mock()))
            widget.drag_dest_set.assert_called_once_with(7, [("text/uri-list", 0, 0)], 9)
            self.assertEqual(widget.connect.call_args.args[0], "drag-data-received")
            self.assertFalse(dnd_gtk.attach_folder_drop(widget, Path("/"), Gtk, Gdk, mock.Mock()))

    def test_rejected_drop_does_not_start_file_copy(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "Desktop"
            folder.mkdir()
            source = Path(root) / "file.txt"
            source.write_text("protected", encoding="utf-8")
            widget = mock.Mock()
            selection = mock.Mock()
            selection.get_uris.return_value = [source.as_uri()]
            Gtk = mock.Mock()
            Gtk.TargetEntry.new.return_value = object()
            Gdk = SimpleNamespace(DragAction=SimpleNamespace(COPY=1))
            with mock.patch.object(dnd_gtk, "_message", return_value=False), \
                    mock.patch.object(dnd_gtk.file_drop, "copy_files") as copy:
                dnd_gtk.attach_folder_drop(widget, folder, Gtk, Gdk, mock.Mock())
                received = widget.connect.call_args.args[1]
                received(widget, object(), 0, 0, selection, 0, 123)
                Gtk.drag_finish.assert_called_once_with(mock.ANY, False, False, 123)
                copy.assert_not_called()
            self.assertEqual(source.read_text(), "protected")


if __name__ == "__main__":
    unittest.main()
