"""Per-rice Windows 98 taskbar options and a native GTK properties dialog.

Only the RiceBowl-owned taskbar is affected; XFCE panel, xfconf and Plank
settings are deliberately untouched so changing rices remains reversible.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


DEFAULT_OPTIONS = {"show_clock": True, "show_quick_launch": True}
_MAX_CONFIG_SIZE = 8192


class TaskbarSettingsError(ValueError):
    """Invalid or unreadable user-owned classic taskbar preferences."""


def options_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "ricebowl" / "classic98-taskbar.json"


def validate_options(options: dict) -> dict[str, bool]:
    if not isinstance(options, dict):
        raise TaskbarSettingsError("Expected a JSON object")
    checked = {}
    for name, default in DEFAULT_OPTIONS.items():
        value = options.get(name, default)
        if not isinstance(value, bool):
            raise TaskbarSettingsError(f"{name} must be true or false")
        checked[name] = value
    return checked


def load_options(path: Path | None = None) -> dict[str, bool]:
    target = path or options_path()
    try:
        with target.open("rb") as source:
            data = source.read(_MAX_CONFIG_SIZE + 1)
    except FileNotFoundError:
        return dict(DEFAULT_OPTIONS)
    if len(data) > _MAX_CONFIG_SIZE:
        raise TaskbarSettingsError("Taskbar settings file is too large")
    try:
        return validate_options(json.loads(data))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TaskbarSettingsError("Invalid taskbar settings JSON") from exc


def save_options(options: dict, path: Path | None = None) -> dict[str, bool]:
    """Write with a private temporary file and an atomic same-directory rename."""
    checked = validate_options(options)
    target = path or options_path()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", dir=target.parent, prefix=".classic98-", suffix=".tmp",
            delete=False, encoding="utf-8",
        ) as stream:
            temporary = Path(stream.name)
            os.fchmod(stream.fileno(), 0o600)
            json.dump(checked, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return checked


def show(shell, Gtk):
    """Present one real Taskbar Properties dialog, with Apply/OK/Cancel."""
    existing = getattr(shell, "_classic98_taskbar_dialog", None)
    if existing is not None:
        existing.present()
        return existing

    dialog = Gtk.Dialog(title="Taskbar Properties", transient_for=shell.bar,
                        flags=Gtk.DialogFlags.DESTROY_WITH_PARENT)
    dialog.set_default_size(360, 300)
    dialog.set_resizable(False)
    dialog.set_modal(False)
    dialog.get_style_context().add_class("classic98-taskbar-properties")
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Apply", Gtk.ResponseType.APPLY)
    dialog.add_button("OK", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    content = dialog.get_content_area()
    content.set_spacing(10)
    content.set_border_width(14)

    heading = Gtk.Label(label="Taskbar Options", xalign=0)
    heading.get_style_context().add_class("classic98-properties-heading")
    content.pack_start(heading, False, False, 0)
    checks = {}
    labels = (("show_quick_launch", "Show Quick Launch"),
              ("show_clock", "Show clock"))
    for key, label in labels:
        widget = Gtk.CheckButton(label=label)
        widget.set_active(shell._classic98_taskbar_options[key])
        widget.get_accessible().set_name(label)
        content.pack_start(widget, False, False, 0)
        checks[key] = widget

    unavailable = Gtk.Frame(label="Not yet available")
    limitations = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    limitations.set_border_width(9)
    for label, reason in (
        ("Auto-hide the taskbar", "Requires X11 strut/monitor-safe auto-hide support"),
        ("Move the taskbar", "Requires orientation-aware taskbar layout and rollback"),
    ):
        widget = Gtk.CheckButton(label=label)
        widget.set_sensitive(False)
        widget.set_tooltip_text(reason)
        limitations.pack_start(widget, False, False, 0)
    unavailable.add(limitations)
    content.pack_start(unavailable, False, False, 0)
    note = Gtk.Label(label="These options affect only the RiceBowl Windows 98 taskbar.",
                     xalign=0)
    note.set_line_wrap(True)
    content.pack_start(note, False, False, 0)
    error = Gtk.Label(xalign=0)
    error.get_style_context().add_class("classic98-properties-error")
    error.set_no_show_all(True)
    content.pack_end(error, False, False, 0)

    def respond(_dialog, response):
        if response not in (Gtk.ResponseType.OK, Gtk.ResponseType.APPLY):
            _dialog.destroy()
            return
        desired = {key: widget.get_active() for key, widget in checks.items()}
        try:
            saved = save_options(desired)
        except (OSError, TaskbarSettingsError) as exc:
            error.set_text("Could not save taskbar settings: " + str(exc))
            error.show()
            return
        shell._classic98_taskbar_options = saved
        shell._classic98_apply_taskbar_options()
        error.hide()
        if response == Gtk.ResponseType.OK:
            _dialog.destroy()

    def closed(_dialog):
        shell._classic98_taskbar_dialog = None

    dialog.connect("response", respond)
    dialog.connect("destroy", closed)
    shell._classic98_taskbar_dialog = dialog
    dialog.show_all()
    error.hide()
    return dialog
