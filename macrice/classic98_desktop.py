"""Read-only Windows 98 desktop icon inspector using ricePlate/XFDesktop.

XFDesktop retains file, icon position, wallpaper and drag/drop ownership.
"""

from __future__ import annotations

from pathlib import Path
import shutil

from .riceware import plate


MAX_DESKTOP_ITEMS = 256


def display_items(snapshot):
    """Stable, bounded rows; never interpret a .desktop Exec command here."""
    return tuple((item.display_name or item.filename, item.kind,
                  "Hidden entry" if item.hidden else
                  "Dotfile" if item.filename.startswith(".") else "Present", item.path)
                 for item in snapshot.items[:MAX_DESKTOP_ITEMS])


class Classic98Desktop:
    def __init__(self, shell, Gtk):
        from gi.repository import Gdk, GLib
        from .riceware.dnd_gtk import attach_file_drag_source, attach_folder_drop

        self.shell, self.Gtk = shell, Gtk
        self.epoch = 0
        self.closed = False
        self.folder = None
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Desktop Icons")
        self.window.set_default_size(545, 375)
        self.window.set_resizable(True)
        self.window.set_transient_for(shell.actions)
        self.window.connect("delete-event", self._on_delete)
        root = shell._class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8),
                            "classic98-desktop-window")
        heading = Gtk.Label(label="Desktop icons are owned by XFDesktop.", xalign=0)
        root.pack_start(heading, False, False, 0)
        guidance = Gtk.Label(
            label="Double-click a real file or shortcut to open it. Changes are made in the desktop folder.",
            xalign=0)
        guidance.set_line_wrap(True)
        root.pack_start(guidance, False, False, 0)
        self.status = Gtk.Label(label="Loading desktop items…", xalign=0)
        root.pack_start(self.status, False, False, 0)
        self.store = Gtk.ListStore(str, str, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_headers_visible(True)
        for index, title in enumerate(("Name", "Type", "Status")):
            cell = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, cell, text=index)
            column.set_resizable(True)
            self.tree.append_column(column)
        self.tree.get_accessible().set_name("Real XFDesktop desktop items")
        self.tree.connect("row-activated", self._activate)

        def selected_uri():
            model, selected = self.tree.get_selection().get_selected()
            if selected is None:
                return None
            path = Path(model[selected][3])
            return path.as_uri() if path.is_file() and not path.is_symlink() else None

        attach_file_drag_source(self.tree, Gtk, Gdk, selected_uri)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.tree)
        root.pack_start(scroll, True, True, 0)
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        refresh = Gtk.Button(label="Refresh")
        refresh.connect("clicked", lambda _button: self.refresh())
        buttons.pack_start(refresh, False, False, 0)
        self.open_folder = Gtk.Button(label="Open Desktop Folder")
        self.open_folder.set_sensitive(False)
        self.open_folder.connect("clicked", lambda _button: self._open_folder())
        from .luna_desktop import desktop_path

        desktop = desktop_path()
        if desktop.is_dir():
            attach_folder_drop(self.open_folder, desktop, Gtk, Gdk, GLib)
        buttons.pack_start(self.open_folder, False, False, 0)
        xfdesktop = Gtk.Button(label="Desktop Settings…")
        xfdesktop.set_sensitive(shutil.which("xfdesktop-settings") is not None)
        xfdesktop.connect("clicked", lambda _button: shell._open_tool("xfdesktop-settings"))
        buttons.pack_start(xfdesktop, False, False, 0)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda _button: self.hide())
        buttons.pack_end(close, False, False, 0)
        root.pack_end(buttons, False, False, 0)
        self.window.add(root)

    def _on_delete(self, *_args):
        self.hide()
        return True

    def show(self):
        if self.closed:
            return
        self.window.show_all()
        self.window.present()
        self.refresh()

    def refresh(self):
        if self.closed or not self.window.get_visible():
            return
        self.epoch += 1
        epoch = self.epoch
        self.status.set_text("Reading desktop folder…")

        def ready(result):
            if self.closed or epoch != self.epoch or not self.window.get_visible():
                return
            if not isinstance(result, plate.DesktopSnapshot):
                self.folder = None
                self.open_folder.set_sensitive(False)
                self.store.clear()
                self.status.set_text(getattr(result, "reason", None) or
                                     "Could not read XFDesktop items")
                return
            self.folder = result.folder if result.exists else None
            self.open_folder.set_sensitive(result.exists)
            self.store.clear()
            for row in display_items(result):
                self.store.append(row)
            suffix = " (first 256 shown)" if result.truncated else ""
            self.status.set_text(f"{len(result.items)} desktop items{suffix}")

        self.shell.classic98_controller.submit(
            "desktop-inventory", lambda: plate.snapshot(limit=MAX_DESKTOP_ITEMS), ready)

    def _open_folder(self):
        if self.folder:
            self.shell._open_uri(Path(self.folder).as_uri())

    def _activate(self, _tree, path, _column):
        row = self.store[path]
        if row and Path(row[3]).exists():
            self.shell._open_uri(Path(row[3]).as_uri())

    def hide(self):
        self.epoch += 1
        self.store.clear()
        self.window.hide()

    def close(self):
        if not self.closed:
            self.hide()
            self.closed = True
            self.window.destroy()
