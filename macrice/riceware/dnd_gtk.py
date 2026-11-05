"""GTK3 URI drag-and-drop for explicit ricePlate folder surfaces.

Only supported local regular-file drops are accepted. There is no automatic
move, overwrite, installation, executable handling or setting mutation.
"""

from __future__ import annotations

import threading
from pathlib import Path

from . import file_drop


def _message(Gtk, parent, title, detail, *, confirm=False):
    dialog = Gtk.MessageDialog(
        transient_for=parent if parent is not None and parent.get_visible() else None,
        modal=True, message_type=Gtk.MessageType.QUESTION if confirm else Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.YES_NO if confirm else Gtk.ButtonsType.CLOSE,
        text=title)
    dialog.format_secondary_text(detail[:600])
    try:
        response = dialog.run()
        return response == Gtk.ResponseType.YES if confirm else False
    finally:
        dialog.destroy()


def attach_folder_drop(widget, destination: Path, Gtk, Gdk, GLib):
    """Turn a real folder button into a confirmed *copy* target."""
    folder = Path(destination)
    if folder == Path("/") or not folder.is_dir() or folder.is_symlink():
        return False
    targets = [Gtk.TargetEntry.new("text/uri-list", 0, 0)]
    widget.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
    widget.set_tooltip_text(f"Open {folder} · Drop local files here to copy (confirmation required)")

    def received(button, context, _x, _y, selection, _info, timestamp):
        parent = button.get_toplevel()
        try:
            plan = file_drop.plan_copy(selection.get_uris(), folder)
        except (OSError, UnicodeError, ValueError) as exc:
            Gtk.drag_finish(context, False, False, timestamp)
            _message(Gtk, parent, "File drop not accepted", str(exc))
            return
        if not _message(Gtk, parent, f"Copy {len(plan.sources)} file(s) to {folder.name}?",
                        "Only local files are copied; existing files are never overwritten. "
                        "Cancel to keep everything unchanged.", confirm=True):
            Gtk.drag_finish(context, False, False, timestamp)
            return
        Gtk.drag_finish(context, True, False, timestamp)

        def finish(receipt=None, error=None):
            if error:
                _message(Gtk, parent, "File copy not completed", error)
                return False
            dialog = Gtk.MessageDialog(
                transient_for=parent if parent is not None and parent.get_visible() else None,
                modal=True, message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.NONE,
                text=f"Copied {len(receipt.created)} file(s) to {folder.name}")
            dialog.format_secondary_text(
                "The copies use private permissions. Undo is available while "
                "the newly copied files remain unchanged.")
            dialog.add_button("Undo copy", Gtk.ResponseType.REJECT)
            dialog.add_button("Keep files", Gtk.ResponseType.CLOSE)
            try:
                undo = dialog.run() == Gtk.ResponseType.REJECT
            finally:
                dialog.destroy()
            if undo:
                def remove():
                    try:
                        removed, skipped = file_drop.undo_copy(receipt)
                        GLib.idle_add(_message, Gtk, parent, "Undo finished",
                                      f"Removed {removed}; kept {skipped} modified/replaced file(s).")
                    except (OSError, ValueError) as exc:
                        GLib.idle_add(_message, Gtk, parent, "Could not undo file copy", str(exc))

                threading.Thread(target=remove, daemon=True,
                                 name="ricebowl-file-drop-undo").start()
            return False

        def work():
            try:
                receipt = file_drop.copy_files(plan)
                GLib.idle_add(finish, receipt, None)
            except (OSError, ValueError, RuntimeError) as exc:
                GLib.idle_add(finish, None, str(exc)[:220])

        threading.Thread(target=work, daemon=True, name="ricebowl-file-drop-copy").start()

    widget.connect("drag-data-received", received)
    return True


def attach_file_drag_source(tree, Gtk, Gdk, uri_from_selected_row):
    """Export an existing file URI from a GTK list to Thunar/XFDesktop."""
    tree.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                         [Gtk.TargetEntry.new("text/uri-list", 0, 0)], Gdk.DragAction.COPY)

    def drag_data_get(_tree, _context, selection, _info, _timestamp):
        try:
            uri = uri_from_selected_row()
            if uri:
                file_drop.parse_local_uris([uri])
                selection.set_uris([uri])
        except (OSError, ValueError):
            return

    tree.connect("drag-data-get", drag_data_get)
