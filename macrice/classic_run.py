"""Windows 98-inspired Run dialog backed by real Linux executables and URIs.

No shell invocation, privilege escalation or implicit environment modifications.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

MAX_INPUT = 2048
ALLOWED_SCHEMES = frozenset(("https", "http", "file", "mailto"))


def parse_target(raw: str) -> tuple[str, tuple[str, ...]]:
    """Return ('uri', (uri,)) or ('command', argv); raise ValueError otherwise."""
    import shlex

    value = raw.strip()
    if not value or len(value) > MAX_INPUT or "\x00" in value or "\n" in value:
        raise ValueError("Enter a valid program, file or website.")
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme.lower() in ALLOWED_SCHEMES:
        if parsed.scheme.lower() in ("http", "https") and not parsed.netloc:
            raise ValueError("The web address needs a host name.")
        return "uri", (value,)
    if parsed.scheme and "://" in value:
        raise ValueError("This URL scheme is not supported.")
    try:
        tokens = shlex.split(value, posix=True)
    except ValueError as exc:
        raise ValueError("Check quotation marks in the command.") from exc
    if not tokens:
        raise ValueError("Enter a program or file.")
    executable = os.path.expanduser(os.path.expandvars(tokens[0]))
    if executable.startswith("/") or executable.startswith("./") or executable.startswith("../"):
        path = Path(executable)
        if path.is_file() and os.access(path, os.X_OK):
            return "command", (str(path), *tokens[1:])
        if path.is_file() and not tokens[1:]:
            return "file", (path.resolve().as_uri(),)
        if path.is_dir() and not tokens[1:]:
            return "file", (path.resolve().as_uri(),)
        raise ValueError("The selected path is not an executable program.")
    if len(tokens) == 1 and Path(executable).expanduser().exists():
        return "file", (Path(executable).expanduser().resolve().as_uri(),)
    resolved = shutil.which(executable)
    if not resolved:
        raise ValueError(f"Program not found: {executable}")
    return "command", (resolved, *tokens[1:])


def execute_target(kind: str, args: tuple[str, ...], Gio) -> None:
    if kind == "command":
        subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
    else:
        Gio.AppInfo.launch_default_for_uri(args[0], None)


def show_run_dialog(Gtk, Gio, parent=None) -> None:
    """Modal GTK3 dialog with familiar Run workflow, not a false Windows API."""
    dialog = Gtk.Dialog(title="Run", transient_for=parent, flags=Gtk.DialogFlags.MODAL)
    dialog.set_default_size(430, -1)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    browse = dialog.add_button("Browse…", 100)
    ok = dialog.add_button("OK", Gtk.ResponseType.OK)
    ok.get_style_context().add_class("classic-run-ok")
    content = dialog.get_content_area()
    content.set_spacing(10)
    content.set_margin_start(14)
    content.set_margin_end(14)
    content.set_margin_top(12)
    content.set_margin_bottom(12)
    message = Gtk.Label(label="Type the name of a program, folder, document, or Internet resource, and it will be opened.")
    message.set_line_wrap(True)
    message.set_xalign(0)
    content.pack_start(message, False, False, 0)
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    row.pack_start(Gtk.Label(label="Open:"), False, False, 0)
    entry = Gtk.Entry()
    entry.set_activates_default(True)
    entry.set_placeholder_text("Program, path or URL")
    entry.get_accessible().set_name("Open")
    row.pack_start(entry, True, True, 0)
    content.pack_start(row, False, False, 0)
    feedback = Gtk.Label(xalign=0)
    feedback.set_line_wrap(True)
    feedback.set_no_show_all(True)
    content.pack_start(feedback, False, False, 0)
    dialog.set_default_response(Gtk.ResponseType.OK)
    dialog.show_all()
    feedback.hide()
    entry.grab_focus()
    try:
        while True:
            result = dialog.run()
            if result == 100:
                picker = Gtk.FileChooserDialog(
                    title="Browse", transient_for=dialog,
                    action=Gtk.FileChooserAction.OPEN)
                picker.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                                   "Open", Gtk.ResponseType.OK)
                try:
                    if picker.run() == Gtk.ResponseType.OK:
                        name = picker.get_filename()
                        if name:
                            entry.set_text(__import__("shlex").quote(name))
                            feedback.hide()
                finally:
                    picker.destroy()
                continue
            if result != Gtk.ResponseType.OK:
                break
            try:
                kind, args = parse_target(entry.get_text())
                execute_target(kind, args, Gio)
            except (ValueError, OSError, RuntimeError) as exc:
                feedback.set_text(str(exc))
                feedback.show()
                entry.grab_focus()
                continue
            except Exception as exc:
                # GLib.Error subclasses Exception, but must not terminate GTK.
                feedback.set_text(f"Cannot open target: {exc}")
                feedback.show()
                entry.grab_focus()
                continue
            break
    finally:
        dialog.destroy()
