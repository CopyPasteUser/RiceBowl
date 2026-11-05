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
    from gi.repository import Gdk
    from .luna_dialog import attach_luna_dialog_chrome

    dialog.get_style_context().add_class("luna-taskbar-properties")
    dialog.set_default_size(438, 488)
    dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
    dialog.add_button("Apply", Gtk.ResponseType.APPLY)
    dialog.add_button("OK", Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.OK)
    area = attach_luna_dialog_chrome(
        dialog, Gtk, Gdk, role="ricebowl-xp-taskbar-properties",
        title="Taskbar and Start Menu Properties",
        close_response=Gtk.ResponseType.CANCEL)

    tabs = Gtk.Notebook()
    tabs.set_margin_start(9)
    tabs.set_margin_end(9)
    tabs.set_margin_top(9)
    tabs.set_margin_bottom(6)
    area.pack_start(tabs, True, True, 0)

    task = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    task.set_border_width(11)
    tabs.append_page(task, Gtk.Label(label="Taskbar"))
    sample = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    sample.get_style_context().add_class("luna-properties-preview")
    sample.get_accessible().set_name("Live visual preview of the XP taskbar settings")
    sample.pack_start(Gtk.Label(label="RiceBowl XP Luna · Desktop preview", xalign=.5),
                      True, True, 7)
    sample_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    sample_bar.get_style_context().add_class("luna-properties-preview-bar")
    sample_start = Gtk.Label(label="◉ start")
    sample_start.get_style_context().add_class("luna-properties-preview-start")
    sample_bar.pack_start(sample_start, False, False, 0)
    sample_quick = Gtk.Label(label="◫  ◈")
    sample_quick.set_no_show_all(True)
    sample_quick.get_style_context().add_class("luna-properties-preview-quick")
    sample_bar.pack_start(sample_quick, False, False, 0)
    sample_tasks = Gtk.Label(label="▣  Files")
    sample_tasks.get_style_context().add_class("luna-properties-preview-task")
    sample_bar.pack_start(sample_tasks, True, True, 0)
    sample_clock = Gtk.Label(label="09:41")
    sample_clock.set_no_show_all(True)
    sample_clock.get_style_context().add_class("luna-properties-preview-clock")
    sample_bar.pack_end(sample_clock, False, False, 0)
    sample.pack_end(sample_bar, False, False, 0)
    task.pack_start(sample, False, False, 0)

    appearance = Gtk.Frame(label="Taskbar appearance")
    appearance_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    appearance_box.set_border_width(9)
    appearance.add(appearance_box)
    task.pack_start(appearance, False, False, 0)
    fields = {}
    for key, label, hint in (
        ("show_quick_launch", "Show Quick Launch", "Show pinned shortcuts and Show Desktop"),
        ("group_similar_windows", "Group similar taskbar buttons", "Combine windows from the same application when the taskbar is crowded"),
    ):
        check = Gtk.CheckButton(label=label)
        check.set_active(shell._luna_taskbar_options[key])
        check.set_tooltip_text(hint)
        check.get_accessible().set_name(label)
        appearance_box.pack_start(check, False, False, 0)
        fields[key] = check

    notification = Gtk.Frame(label="Notification area")
    notification_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
    notification_box.set_border_width(9)
    notification.add(notification_box)
    clock = Gtk.CheckButton(label="Show the clock")
    clock.set_active(shell._luna_taskbar_options["show_clock"])
    clock.set_tooltip_text("Open the calendar from the actual notification area")
    clock.get_accessible().set_name("Show the clock")
    fields["show_clock"] = clock
    notification_box.pack_start(clock, True, True, 0)
    customize = Gtk.Button(label="Customize…")
    customize.set_sensitive(getattr(shell, "_tray", None) is not None)
    customize.set_tooltip_text("Choose the real StatusNotifier icons shown in the tray")
    customize.connect("clicked", lambda _button: shell._tray.open_preferences())
    notification_box.pack_end(customize, False, False, 0)
    task.pack_start(notification, False, False, 0)

    def refresh_sample(_widget=None):
        sample_quick.set_visible(fields["show_quick_launch"].get_active())
        sample_clock.set_visible(fields["show_clock"].get_active())
        sample_tasks.set_text("▣  Files × 2" if fields["group_similar_windows"].get_active()
                              else "▣ Files   ▣ Files")

    for check in fields.values():
        check.connect("toggled", refresh_sample)
    refresh_sample()
    unavailable = Gtk.Label(
        label="The XFWM window manager remains active. Taskbar auto-hide "
              "is unavailable until edge handling is safe on multiple monitors.", xalign=0)
    unavailable.set_line_wrap(True)
    unavailable.set_max_width_chars(46)
    unavailable.get_style_context().add_class("luna-properties-note")
    task.pack_end(unavailable, False, False, 0)

    start = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
    start.set_border_width(11)
    tabs.append_page(start, Gtk.Label(label="Start Menu"))
    heading = Gtk.Label(label="Customize the Start menu", xalign=0)
    heading.get_style_context().add_class("luna-properties-heading")
    start.pack_start(heading, False, False, 0)
    illustration = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    illustration.get_style_context().add_class("luna-properties-start-preview")
    illustration.pack_start(Gtk.Label(label="◉  Linux desktop", xalign=0), False, False, 0)
    columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    programs = Gtk.Label(label="Programs\nDocuments\nAll Programs  ▸", xalign=0)
    programs.get_style_context().add_class("luna-properties-start-apps")
    places = Gtk.Label(label="My Computer\nControl Panel\nHelp and Support", xalign=0)
    places.get_style_context().add_class("luna-properties-start-places")
    columns.pack_start(programs, True, True, 0)
    columns.pack_start(places, True, True, 0)
    illustration.pack_start(columns, True, True, 0)
    start.pack_start(illustration, False, False, 0)
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
    history_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    history_text = Gtk.Label(label="Recently opened programs", xalign=0)
    history_row.pack_start(history_text, True, True, 0)
    clear = Gtk.Button(label="Clear List")
    clear.get_accessible().set_name("Clear recent XP Start menu programs")
    history_row.pack_end(clear, False, False, 0)
    start.pack_start(history_row, False, False, 0)

    error = Gtk.Label(xalign=0)
    error.get_style_context().add_class("luna-properties-error")
    error.set_line_wrap(True)
    area.pack_end(error, False, False, 0)

    def clear_history(_button):
        """Clear only XP usage history after confirmation; preserve favorites."""
        from .luna_start_state import clear_recent_programs, save_start_state

        state = shell._luna_start_state
        if state is None or not state.launches:
            clear.set_sensitive(False)
            return
        confirm = Gtk.MessageDialog(
            transient_for=dialog, modal=True, message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text="Clear recently used programs?")
        confirm.format_secondary_text(
            "Only the XP Start menu history will be cleared. Pinned favorites stay in place.")
        try:
            if confirm.run() != Gtk.ResponseType.YES:
                return
        finally:
            confirm.destroy()
        previous = dict(state.launches)
        clear_recent_programs(state)
        try:
            save_start_state(state)
        except (OSError, ValueError) as exc:
            state.launches = previous
            error.set_text("Could not clear recent programs: " + str(exc))
            error.show()
            return
        clear.set_sensitive(False)
        error.hide()
        if shell.menu is not None and shell.menu.get_visible():
            shell._populate(shell.search.get_text())

    clear.set_sensitive(bool(shell._luna_start_state and shell._luna_start_state.launches))
    clear.connect("clicked", clear_history)

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
    refresh_sample()
    error.hide()
    return dialog
