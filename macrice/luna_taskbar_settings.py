"""Persistent, user-local XP Luna taskbar and Start menu preferences.

The controls affect only RiceBowl windows: no XFCE panels, session settings,
desktop shortcuts or other rice profiles are modified.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


DEFAULT_OPTIONS = {
    "show_clock": True,
    "show_quick_launch": True,
    "group_similar_windows": True,
    "recent_program_count": 6,
}
_MAX_BYTES = 8192


class LunaSettingsError(ValueError):
    """A persisted XP preference is invalid or unsafe to access."""


def options_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "ricehub" / "winxp-taskbar.json"


def validate_options(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise LunaSettingsError("Expected a JSON object")
    valid = {}
    for name, default in DEFAULT_OPTIONS.items():
        value = raw.get(name, default)
        if isinstance(default, bool):
            if type(value) is not bool:
                raise LunaSettingsError(f"{name} must be true or false")
        elif type(value) is not int or not 3 <= value <= 12:
            raise LunaSettingsError("Recent program count must be between 3 and 12")
        valid[name] = value
    return valid


def _check_path(target: Path):
    if target.is_symlink() or target.parent.is_symlink():
        raise LunaSettingsError("Refusing symlinked XP preferences")
    if target.exists() and not target.is_file():
        raise LunaSettingsError("XP preferences must be a regular file")


def load_options(path: Path | None = None) -> dict:
    target = path if path is not None else options_path()
    _check_path(target)
    try:
        with target.open("rb") as stream:
            data = stream.read(_MAX_BYTES + 1)
    except FileNotFoundError:
        return dict(DEFAULT_OPTIONS)
    if len(data) > _MAX_BYTES:
        raise LunaSettingsError("XP preferences file is too large")
    try:
        return validate_options(json.loads(data))
    except (ValueError, UnicodeError) as exc:
        raise LunaSettingsError("Invalid XP preferences") from exc


def save_options(options: dict, path: Path | None = None) -> dict:
    valid = validate_options(options)
    target = path if path is not None else options_path()
    _check_path(target)
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    _check_path(target)
    fd, temporary = tempfile.mkstemp(prefix=".winxp-taskbar-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o600)
            json.dump(valid, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        _check_path(target)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return valid


def center_on_workarea(rect, width: int, height: int, panel_height: int = 40):
    """Center an XP-owned dialog above its DOCK on the current monitor."""
    return (rect.x + max(0, (rect.width - width) // 2),
            rect.y + max(0, (rect.height - panel_height - height) // 2))


def show(shell, Gtk):
    """Single-instance, real Luna-styled properties window with Apply/Cancel."""
    existing = getattr(shell, "_luna_taskbar_dialog", None)
    if existing is not None:
        existing.present()
        return existing

    dialog = Gtk.Dialog(title="Taskbar and Start Menu Properties",
                        transient_for=shell.bar,
                        flags=Gtk.DialogFlags.DESTROY_WITH_PARENT)
    dialog.get_style_context().add_class("luna-taskbar-properties")
    dialog.set_default_size(408, 366)
    dialog.set_resizable(False)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Apply", Gtk.ResponseType.APPLY)
    dialog.add_button("OK", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    area = dialog.get_content_area()
    area.set_border_width(13)
    area.set_spacing(10)
    tabs = Gtk.Notebook()
    area.pack_start(tabs, True, True, 0)

    task = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    task.set_border_width(13)
    tabs.append_page(task, Gtk.Label(label="Taskbar"))
    intro = Gtk.Label(label="Taskbar appearance", xalign=0)
    intro.get_style_context().add_class("luna-properties-heading")
    task.pack_start(intro, False, False, 0)
    fields = {}
    for key, label, hint in (
        ("show_quick_launch", "Show Quick Launch", "Show pinned shortcuts and Show Desktop"),
        ("group_similar_windows", "Group similar taskbar buttons", "Combine windows from the same application when the taskbar is crowded"),
        ("show_clock", "Show the clock", "Keep date and calendar available from the notification area"),
    ):
        check = Gtk.CheckButton(label=label)
        check.set_active(shell._luna_taskbar_options[key])
        check.set_tooltip_text(hint)
        check.get_accessible().set_name(label)
        task.pack_start(check, False, False, 0)
        fields[key] = check
    unavailable = Gtk.Label(
        label="Auto-hide and locking require monitor-safe X11 edge handling; "
              "they are not enabled in this release.", xalign=0)
    unavailable.set_line_wrap(True)
    unavailable.set_max_width_chars(38)
    unavailable.get_style_context().add_class("luna-properties-note")
    task.pack_end(unavailable, False, False, 0)

    start = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=11)
    start.set_border_width(13)
    tabs.append_page(start, Gtk.Label(label="Start Menu"))
    heading = Gtk.Label(label="Start menu appearance", xalign=0)
    heading.get_style_context().add_class("luna-properties-heading")
    start.pack_start(heading, False, False, 0)
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    label = Gtk.Label(label="Number of recent programs:", xalign=0)
    row.pack_start(label, True, True, 0)
    count = Gtk.SpinButton.new_with_range(3, 12, 1)
    count.set_value(shell._luna_taskbar_options["recent_program_count"])
    count.get_accessible().set_name("Number of recent programs")
    row.pack_end(count, False, False, 0)
    start.pack_start(row, False, False, 0)
    explanation = Gtk.Label(
        label="Recently used applications appear below your pinned favorites. "
              "Right-click a program in Start to manage favorites and their order.",
        xalign=0)
    explanation.set_line_wrap(True)
    explanation.set_max_width_chars(38)
    start.pack_start(explanation, False, False, 0)

    error = Gtk.Label(xalign=0)
    error.get_style_context().add_class("luna-properties-error")
    error.set_line_wrap(True)
    area.pack_end(error, False, False, 0)

    def respond(_dialog, response):
        if response not in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
            _dialog.destroy()
            return
        desired = {key: check.get_active() for key, check in fields.items()}
        desired["recent_program_count"] = count.get_value_as_int()
        try:
            saved = save_options(desired)
        except (OSError, LunaSettingsError) as exc:
            error.set_text("Could not save XP preferences: " + str(exc))
            error.show()
            return
        shell._luna_taskbar_options = saved
        shell._luna_apply_taskbar_options()
        error.hide()
        if response == Gtk.ResponseType.OK:
            _dialog.destroy()

    dialog.connect("response", respond)
    dialog.connect("destroy", lambda _dialog: setattr(shell, "_luna_taskbar_dialog", None))
    from gi.repository import GLib

    def center_dialog():
        dialog.move(*center_on_workarea(shell._desktop_rect(), *dialog.get_size()))
        return False

    dialog.connect("map-event", lambda *_args: GLib.idle_add(center_dialog))
    shell._luna_taskbar_dialog = dialog
    dialog.show_all()
    error.hide()
    return dialog
